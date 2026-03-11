from analyzer.forms import MedicalImageUploadForm
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import os
import os
import json
import base64
import pandas as pd
from io import BytesIO
import logging
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from analyzer.forms import ReportUploadForm, SymptomCheckerForm
from analyzer.models import UploadedReport, ChatHistory, HealthData
from analyzer.utils import process_pdf, analyze_with_llm, get_firebase_db, save_health_data_to_db
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.tools import Tool
import pandas as pd
from io import BytesIO
import base64
import os
import json
import pinecone




def medical_image_annotation(request):
    from analyzer.utils import analyze_medical_image_with_gemini, export_annotation_pdf
    image_url = None
    explanation = None
    explanation_text = None
    export_pdf = False
    
    if request.method == 'POST':
        form = MedicalImageUploadForm(request.POST, request.FILES)
        action = request.POST.get('action', 'submit')
        
        if form.is_valid():
            image = form.cleaned_data['image']
            user_prompt = form.cleaned_data.get('prompt', '')
            
            # Save uploaded image
            file_path = default_storage.save('medical_images/' + image.name, ContentFile(image.read()))
            image_url = default_storage.url(file_path)
            abs_image_path = default_storage.path(file_path)
            
            # Analyze image with Gemini Vision
            try:
                explanation, explanation_text = analyze_medical_image_with_gemini(
                    abs_image_path,
                    user_prompt=user_prompt
                )
                messages.success(request, 'Image analyzed successfully!')
            except Exception as e:
                explanation = f"<p style='color: red;'>Error analyzing image: {str(e)}</p>"
                explanation_text = f"Error analyzing image: {str(e)}"
                messages.error(request, f'Image analysis error: {str(e)}')
            
            # Export as PDF if requested
            if action == 'export_pdf' and explanation_text:
                return export_annotation_pdf(image_url, explanation_text)
    else:
        form = MedicalImageUploadForm()
    
    return render(request, 'analyzer/medical_image_annotation.html', {
        'form': form,
        'image_url': image_url,
        'explanation': explanation,
        'export_pdf': export_pdf
    })



# Symptom Checker View
def symptom_checker(request):
    from analyzer.utils import medical_agent
    result = None
    result_html = None
    if request.method == 'POST':
        form = SymptomCheckerForm(request.POST)
        if form.is_valid():
            symptoms_raw = form.cleaned_data['symptoms']
            # Pass user input as a structured prompt to the agent
            prompt = f"""Analyze the following symptoms and provide a comprehensive medical overview:

1. Possible Medical Conditions - List conditions that could cause these symptoms
2. Severity Assessment - Rate as mild, moderate, or severe
3. Recommended Next Steps - Suggest self-care, doctor visit, or emergency care
4. Warning Signs - Highlight symptoms requiring immediate medical attention
5. General Health Recommendations - Offer preventive care suggestions

Symptom List: {symptoms_raw}

IMPORTANT DISCLAIMER: This is for informational purposes only and cannot replace a medical diagnosis. Always consult a licensed healthcare professional for proper medical evaluation and treatment."""
            try:
                result = medical_agent.run(prompt)
            except Exception as e:
                result = f"Error analyzing symptoms: {e}"
            import markdown
            result_html = markdown.markdown(result, extensions=["tables", "fenced_code"])
    else:
        form = SymptomCheckerForm()
    return render(request, 'analyzer/symptom_checker.html', {
        'form': form,
        'result': result,
        'result_html': result_html
    })

@login_required
def dashboard(request):
    # Get last 3 reports for the logged-in user
    recent_reports = UploadedReport.objects.filter(user=request.user).order_by('-uploaded_at')[:3]
    return render(request, 'analyzer/dashboard.html', {
        'recent_reports': recent_reports
    })

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
            report.save()  # Ensure file is saved before reading
            # Read the raw PDF text for filtering
            from langchain_community.document_loaders import PyPDFLoader
            loader = PyPDFLoader(report.file.path)
            docs = loader.load()
            pdf_text = "\n".join([doc.page_content for doc in docs])
            print('[DEBUG] PDF text length:', len(pdf_text))
            # Use report.id as namespace for Pinecone
            namespace = f"report_{report.id}"
            retriever = process_pdf(report.file.path, namespace=namespace, mode="create")
            from langchain_community.chat_message_histories import ChatMessageHistory
            chat_hist = ChatMessageHistory()
            user_input = "Extract all health parameters and their values from this report. Output only the JSON array as described."
            from .utils import analyze_with_llm, save_health_data_to_db
            answer_html, health_data = analyze_with_llm(user_input, retriever, chat_hist, context=pdf_text)
            print('[DEBUG] AUTO-EXTRACT LLM RAW ANSWER:', answer_html)
            print('[DEBUG] AUTO-EXTRACT LLM health_data:', health_data)
            if not health_data:
                print('[DEBUG] No health_data extracted! LLM output was:', answer_html)
            if health_data:
                save_health_data_to_db(
                    health_data,
                    patient_id=str(request.user.id),
                    report_date=report.uploaded_at.date() if hasattr(report, 'uploaded_at') else None,
                    pdf_text=pdf_text,
                    report=report
                )
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
                save_health_data_to_db(
                    health_data,
                    patient_id=str(request.user.id),
                    report_date=report.uploaded_at.date() if hasattr(report, 'uploaded_at') else None,
                    report=report
                )
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




@login_required
def health_data_trends(request):
    from .models import HealthData, UploadedReport
    user_id = str(request.user.id)
    reports = UploadedReport.objects.filter(user=request.user).order_by('uploaded_at')
    # Get all health data for this user, ordered by date
    data = HealthData.objects.filter(patient_id=user_id).order_by('report_date')
    # Group by parameter
    chart_data = {}
    for row in data:
        if row.parameter not in chart_data:
            chart_data[row.parameter] = []
        chart_data[row.parameter].append({
            'date': row.report_date.strftime('%Y-%m-%d'),
            'value': float(row.value) if row.value.replace('.', '', 1).isdigit() else row.value,
            'unit': row.unit,
            'report_id': row.report.id if row.report else None
        })
    parameters = list(chart_data.keys())
    import json
    chart_data_json = json.dumps(chart_data)
    # Prepare report list for dropdowns
    report_options = [
        {'id': r.id, 'date': r.uploaded_at.strftime('%Y-%m-%d'), 'name': os.path.basename(r.file.name)} for r in reports
    ]
    return render(request, 'analyzer/health_data_trends.html', {
        'parameters': parameters,
        'chart_data_json': chart_data_json,
        'report_options': report_options
    })




@login_required
def extracted_key_parameters(request):
    from analyzer.models import HealthData, UploadedReport
    user_id = str(request.user.id)
    reports = UploadedReport.objects.filter(user=request.user).order_by('-uploaded_at')
    report_data = []
    for report in reports:
        data = HealthData.objects.filter(patient_id=user_id, report=report)
        param_list = []
        for row in data:
            param_list.append({
                'parameter': row.parameter,
                'value': row.value,
                'unit': row.unit,
                'date': row.report_date
            })
        if param_list:
            report_data.append({
                'report': report,
                'parameters': param_list
            })
    return render(request, 'analyzer/extracted_key_parameters.html', {
        'report_data': report_data
    })



@login_required
def analyze_profile(request):
    reports = UploadedReport.objects.filter(user=request.user).order_by('-uploaded_at')
    all_text = ""
    for report in reports:
        if hasattr(report, 'file') and report.file:
            try:
                with open(report.file.path, 'r', encoding='utf-8', errors='ignore') as f:
                    all_text += f.read() + "\n\n"
            except Exception:
                continue
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate
    system_prompt = """
    You are a highly knowledgeable and detailed medical AI assistant. Analyze the user's entire health profile and extracted medical data. Provide a summary, key findings, trends, and recommendations in a clear, structured format.
    {context}
    """
    qa_prompt = ChatPromptTemplate(
        messages=[
            SystemMessagePromptTemplate.from_template(system_prompt),
            ("human", "Give me a summary and insights for my entire health profile.")
        ]
    )
    model = ChatGoogleGenerativeAI(model="gemini-1.5-flash")
    import markdown
    answer_html = None
    error_message = None
    try:
        response = model.invoke(all_text)
        answer_html = markdown.markdown(response.content, extensions=["tables", "fenced_code"])
    except Exception as e:
        error_message = str(e)
    return render(request, 'analyzer/analyze_profile.html', {'answer_html': answer_html, 'reports': reports, 'error_message': error_message})

@login_required
def chatbot_widget(request):
    return render(request, 'analyzer/chatbot_widget.html')