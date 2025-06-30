from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import ReportUploadForm
from .models import UploadedReport, ChatHistory
from .utils import process_pdf, analyze_with_llm, get_firebase_db, save_health_data_to_db, translate_text
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
import base64
import os
import json
from django.http import JsonResponse
from langchain_core.messages import HumanMessage, AIMessage
import pinecone

# Dashboard view
@login_required
def dashboard(request):
    return render(request, 'analyzer/dashboard.html')

# User signup

def user_signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Account created! Please log in.')
            return redirect('analyzer:login')
        else:
            messages.error(request, 'Sign up failed. Please check the form.')
    else:
        form = UserCreationForm()
    return render(request, 'analyzer/signup.html', {'form': form})

# User login

def user_login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('analyzer:dashboard')
        else:
            messages.error(request, 'Login failed. Please check your username and password.')
    else:
        form = AuthenticationForm()
    return render(request, 'analyzer/login.html', {'form': form})

# User logout

def user_logout(request):
    logout(request)
    return redirect('analyzer:login')

# PDF upload
@login_required
def upload_report(request):
    if request.method == 'POST':
        form = ReportUploadForm(request.POST, request.FILES)
        if form.is_valid():
            report = form.save(commit=False)
            report.user = request.user
            report.save()
            # Use report.id as namespace for Pinecone
            namespace = f"report_{report.id}"
            retriever = process_pdf(report.file.path, namespace=namespace, mode="create")
            from langchain_community.chat_message_histories import ChatMessageHistory
            chat_hist = ChatMessageHistory()
            # Use a direct prompt to force extraction
            user_input = "Extract all health parameters and their values from this report. Output only the JSON array as described."
            from .utils import analyze_with_llm, save_health_data_to_db
            answer_html, health_data = analyze_with_llm(user_input, retriever, chat_hist)
            print('[DEBUG] AUTO-EXTRACT LLM RAW ANSWER:', answer_html)
            print('[DEBUG] AUTO-EXTRACT LLM health_data:', health_data)
            # Read the raw PDF text for filtering
            from langchain_community.document_loaders import PyPDFLoader
            loader = PyPDFLoader(report.file.path)
            docs = loader.load()
            pdf_text = "\n".join([doc.page_content for doc in docs])
            if health_data:
                save_health_data_to_db(health_data, patient_id=str(request.user.id), report_date=report.uploaded_at.date() if hasattr(report, 'uploaded_at') else None, pdf_text=pdf_text)
            messages.success(request, 'Report uploaded and health data extracted!')
            return redirect('analyzer:dashboard')
    else:
        form = ReportUploadForm()
    return render(request, 'analyzer/upload.html', {'form': form})

# Analyze report (with chat history)
@login_required
def analyze_report(request):
    answer = None
    reports = UploadedReport.objects.filter(user=request.user)
    selected_report_id = request.POST.get('report_id') if request.method == 'POST' else None
    chat_history = []
    if selected_report_id:
        chat_history = ChatHistory.objects.filter(user=request.user, report_id=selected_report_id).order_by('timestamp')
    if request.method == 'POST':
        report_id = request.POST.get('report_id')
        user_input = request.POST.get('user_input')
        try:
            report = UploadedReport.objects.get(id=report_id, user=request.user)
            namespace = f"report_{report.id}"
            retriever = process_pdf(report.file.path, namespace=namespace, mode="retrieve")
            # Build chat history for LLM (only question/answer, no extra fields)
            llm_chat_history = []
            for chat in chat_history:
                llm_chat_history.append(HumanMessage(content=chat.question))
                llm_chat_history.append(AIMessage(content=chat.answer))
            answer_html, health_data = analyze_with_llm(user_input, retriever, llm_chat_history)
            print('[DEBUG] LLM RAW ANSWER:', answer_html)
            print('[DEBUG] LLM health_data:', health_data)
            # Save Q&A to ChatHistory
            ChatHistory.objects.create(user=request.user, report=report, question=user_input, answer=answer_html)
            # Save extracted health data to DB (if any)
            if health_data:
                print('[DEBUG] Saving health_data to DB for user:', request.user.id)
                save_health_data_to_db(health_data, patient_id=str(request.user.id), report_date=report.uploaded_at.date() if hasattr(report, 'uploaded_at') else None)
            else:
                print('[DEBUG] No health_data extracted from LLM output.')
            # Refresh chat history
            chat_history = ChatHistory.objects.filter(user=request.user, report=report).order_by('timestamp')
            answer = answer_html
        except Exception as e:
            answer = f"Error: {e}"
    return render(request, 'analyzer/analyze.html', {
        'reports': reports,
        'answer': answer,
        'chat_history': chat_history,
        'selected_report_id': selected_report_id
    })

# User profile
@login_required
def user_profile(request):
    user = request.user
    reports = UploadedReport.objects.filter(user=user)
    return render(request, 'analyzer/profile.html', {
        'user': user,
        'reports': reports
    })

# Extracted health data
@login_required
def extracted_health_data(request):
    from .models import HealthData, UploadedReport
    user_id = str(request.user.id)
    # Get all reports for this user
    reports = UploadedReport.objects.filter(user=request.user).order_by('-uploaded_at')
    # For each report, get its health data (all dates for that report)
    report_data = []
    for report in reports:
        data = HealthData.objects.filter(patient_id=user_id, report_date=report.uploaded_at.date())
        # Group by parameter for this report and date
        param_dict = {}
        for row in data:
            if row.parameter not in param_dict:
                param_dict[row.parameter] = []
            param_dict[row.parameter].append({
                'value': row.value,
                'unit': row.unit,
                'date': row.report_date
            })
        if data.exists():
            report_data.append({
                'report': report,
                'health_data': data,
                'param_dict': param_dict
            })
    return render(request, 'analyzer/extracted_health_data.html', {
        'report_data': report_data
    })

@login_required
def uploaded_reports(request):
    reports = UploadedReport.objects.filter(user=request.user).order_by('-uploaded_at')
    return render(request, 'analyzer/uploaded_reports.html', {'reports': reports})

@login_required
def delete_report(request, report_id):
    from .models import UploadedReport
    report = UploadedReport.objects.get(id=report_id, user=request.user)
    if request.method == 'POST':
        # Clean up Pinecone namespace for this report
        pinecone_api_key = os.getenv('PINECONE_API_KEY')
        pinecone_region = os.getenv('PINECONE_REGION', 'us-east-1')
        pc = pinecone.Pinecone(api_key=pinecone_api_key)
        index_name = 'medical-analyzer-index'
        namespace = f"report_{report.id}"
        if index_name in pc.list_indexes().names():
            index = pc.Index(index_name)
            # Delete all vectors in this namespace
            index.delete(delete_all=True, namespace=namespace)
        report.file.delete(save=False)  # delete the file from storage
        report.delete()
        messages.success(request, 'Report and its vectors deleted successfully!')
        return redirect('analyzer:uploaded_reports')
    return redirect('analyzer:uploaded_reports')

def translate_summary(request):
    if request.method == 'POST':
        text = request.POST.get('text')
        lang = request.POST.get('lang', 'hi')
        translated = translate_text(text, dest_lang=lang)
        return JsonResponse({'translated': translated})
