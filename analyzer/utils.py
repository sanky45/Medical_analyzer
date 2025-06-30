import os
import firebase_admin
from firebase_admin import credentials, firestore, auth as fb_auth
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_chroma import Chroma
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, SystemMessagePromptTemplate
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
import markdown
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import re
import json
import uuid

from django.conf import settings
from .models import HealthData, UploadedReport
from datetime import date
import pinecone
from pinecone import Pinecone, ServerlessSpec
from langchain_pinecone import Pinecone as PineconeStore
from deep_translator import GoogleTranslator
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

# Load API keys from environment
HF_TOKEN = os.getenv('HF_TOKEN')
FIREBASE_CREDENTIALS_PATH = os.getenv('FIREBASE_CREDENTIALS_PATH')

# Initialize Firebase
firebase_app = None
def get_firebase_db():
    global firebase_app
    if not firebase_admin._apps:
        cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
        firebase_app = firebase_admin.initialize_app(cred)
    return firestore.client()


def get_embeddings():
    return HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")


def process_pdf(file_path, namespace=None, mode="create"):
    pinecone_api_key = os.getenv('PINECONE_API_KEY')
    pinecone_region = os.getenv('PINECONE_REGION', 'us-east-1')
    pc = Pinecone(api_key=pinecone_api_key)
    index_name = 'medical-analyzer-index'
    dimension = 384  # for MiniLM-L6-v2

    # Create index if it doesn't exist
    if index_name not in pc.list_indexes().names():
        pc.create_index(
            name=index_name,
            dimension=dimension,
            metric='cosine',
            spec=ServerlessSpec(
                cloud='aws',
                region=pinecone_region
            )
        )
    embeddings = get_embeddings()
    if mode == "create":
        loader = PyPDFLoader(file_path)
        docs = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=5000, chunk_overlap=500)
        splits = text_splitter.split_documents(docs)
        vectorstore = PineconeStore.from_documents(
            documents=splits,
            embedding=embeddings,
            index_name=index_name,
            namespace=namespace
        )
    else:
        vectorstore = PineconeStore.from_existing_index(
            index_name=index_name,
            embedding=embeddings,
            namespace=namespace
        )
    retriever = vectorstore.as_retriever(namespace=namespace)
    return retriever


def reconstruct_chat_history(messages):
    fixed = []
    for m in messages:
        if isinstance(m, (HumanMessage, AIMessage, SystemMessage)):
            fixed.append(m)
        elif isinstance(m, dict):
            # Only accept dicts with 'content' and valid _type, and ignore any extra fields
            data = m.get('data', {})
            if (
                m.get('_type') in {'human', 'ai', 'system'}
                and isinstance(data, dict)
                and set(data.keys()) == {'content'}
                and isinstance(data['content'], str)
            ):
                if m.get('_type') == 'human':
                    fixed.append(HumanMessage(content=data['content']))
                elif m.get('_type') == 'ai':
                    fixed.append(AIMessage(content=data['content']))
                elif m.get('_type') == 'system':
                    fixed.append(SystemMessage(content=data['content']))
            # Ignore any dict with unknown or extra fields (e.g., 'thought')
        elif isinstance(m, str):
            fixed.append(HumanMessage(content=m))
        # Ignore any other types or dicts with unsupported fields
    return fixed


def extract_health_data_from_llm_output(llm_output):
    """
    Extracts the JSON array from the 'Extracted Health Data (JSON)' section of the LLM output,
    or from any code block containing a JSON array. Returns a Python list of dicts, or an empty list if not found/invalid.
    """
    # Try to find JSON array after the heading first
    match = re.search(r'## Extracted Health Data \(JSON\)[^\[]*(\[.*?\])', llm_output, re.DOTALL)
    if match:
        json_str = match.group(1)
        try:
            return json.loads(json_str)
        except Exception as e:
            print(f"[ERROR] Failed to parse health data JSON after heading: {e}")
    # Fallback: find the first JSON array in any code block or anywhere in the text
    match = re.search(r'\[\s*{.*?}\s*\]', llm_output, re.DOTALL)
    if match:
        json_str = match.group(0)
        try:
            return json.loads(json_str)
        except Exception as e:
            print(f"[ERROR] Failed to parse fallback health data JSON: {e}")
    return []


def analyze_with_llm(user_input, retriever, chat_history=None, context=""):
    contextualize_q_prompt = ChatPromptTemplate.from_messages([
        ("system", "Reformulate the user's question to make it self-contained and clear."),
        MessagesPlaceholder("messages"),
        ("human", "{input}")
    ])
    system_prompt = """
    You are a highly knowledgeable and detailed medical AI assistant. Analyze the user's medical report thoroughly and extract all possible key health attributes, findings, and insights.

    For any question or summary request, provide your answer in a clear, structured, and easy-to-read format using:
    - Markdown headings for each section (e.g., ## Summary, ## Key Health Parameters, etc.)
    - Bullet points for lists
    - Numbered lists for steps or sequences
    - Tables for comparisons or grouped data
    - Short, concise sentences (avoid long paragraphs)

    Use these sections:
    ## Summary
    ## Key Health Parameters (with values and explanations)
    ## Historical Trends (if available)
    ## Advantages & Disadvantages
    ## Detected Diseases
    List all diseases or abnormalities detected in the report.
    ## Remedies & Recommendations
    For each detected disease or abnormality, provide:
    - Dietary modifications and natural remedies
    - Allopathic (modern medicine) solutions
    - Ayurvedic solutions
    - Homeopathic solutions
    - For each solution, explain the rationale and any precautions.
    ## Research Papers & Global Guidelines
    For each detected disease or abnormality:
    - List 2-3 recent or important research papers (with title, a short summary, and a link if possible).
    - Summarize global clinical guidelines (e.g., WHO, CDC, NICE) for this disease.
    ## Risks & Next Steps

    If you don't have enough information, say you don't know instead of making assumptions.
    
    ---
    
    Here is the full text of the user's medical report:
    {context}
    """
    qa_prompt = ChatPromptTemplate(
        messages=[
            SystemMessagePromptTemplate.from_template(system_prompt),
            MessagesPlaceholder("messages"),
            ("human", "{input}")
        ]
    )
    model = ChatGoogleGenerativeAI(model="gemini-1.5-flash")
    question_answer_chain = create_stuff_documents_chain(model, qa_prompt)
    rag_chain = create_retrieval_chain(retriever, question_answer_chain)
    # Ensure chat_history is a list of valid LangChain message objects only
    valid_types = (HumanMessage, AIMessage, SystemMessage)
    # Accept both list and ChatMessageHistory for chat_history
    if chat_history is None:
        chat_history = []
    if hasattr(chat_history, 'messages'):
        chat_history = chat_history.messages
    chat_history = [m for m in chat_history if isinstance(m, valid_types)]
    # Append the user's question as a HumanMessage
    chat_history.append(HumanMessage(content=user_input))
    # Ensure messages is a list of valid message objects
    messages = getattr(chat_history, 'messages', [])
    if not isinstance(messages, list):
        messages = []
    # Convert dicts to message objects if needed (should be redundant now)
    fixed_messages = reconstruct_chat_history(messages)
    print("[DEBUG] chat_history type:", type(chat_history))
    print("[DEBUG] fixed_messages:", fixed_messages)
    print("[DEBUG] fixed_messages types:", [type(m) for m in fixed_messages])
    print("[DEBUG] retriever type:", type(retriever))
    response = rag_chain.invoke({
        "input": user_input,
        "messages": chat_history,
        "context": context
    })
    answer = response.get("answer", "No response generated.")
    # Only append to chat_history if it is a ChatMessageHistory object
    if hasattr(chat_history, 'messages'):
        chat_history.messages.append(AIMessage(content=answer))
    # Extract health data JSON for further use
    health_data = extract_health_data_from_llm_output(answer)
    print("[DEBUG] Extracted health data:", health_data)
    # Render markdown to HTML for better readability
    answer_html = markdown.markdown(answer, extensions=["tables", "fenced_code"])
    return answer_html, health_data


def save_health_data_to_db(health_data, patient_id, report_date=None, pdf_text=None):
    if report_date is None:
        report_date = date.today()
    for entry in health_data:
        param = entry.get('parameter', '')
        value = str(entry.get('value', ''))
        unit = entry.get('unit', '')
        if unit is None:
            unit = ''
        # If pdf_text is given, filter by presence of both parameter and value together
        if pdf_text:
            # Build a regex to match the parameter and value near each other (allowing for whitespace and punctuation)
            pattern = re.compile(rf'{re.escape(param)}[\s:,-]*{re.escape(value)}', re.IGNORECASE)
            if not (param and value and pattern.search(pdf_text)):
                continue
        HealthData.objects.create(
            patient_id=patient_id,
            report_date=report_date,
            parameter=param,
            value=value,
            unit=unit
        )


def translate_text(text, dest_lang='hi'):
    return GoogleTranslator(source='auto', target=dest_lang).translate(text)


@csrf_exempt
def chatbot_ask(request):
    if request.method == 'POST':
        data = json.loads(request.body.decode('utf-8'))
        question = data.get('question', '')
        report_id = data.get('report_id')
        chat_history = data.get('chat_history', [])
        # Load report context
        retriever = None
        if report_id:
            try:
                report = UploadedReport.objects.get(id=report_id)
                namespace = f"report_{report.id}"
                retriever = process_pdf(report.file.path, namespace=namespace, mode="retrieve")
            except Exception as e:
                return JsonResponse({'error': f'Could not load report: {e}'}, status=400)
        else:
            return JsonResponse({'error': 'No report_id provided.'}, status=400)
        # Build chat history for LLM
        llm_chat_history = []
        for msg in chat_history:
            if msg.get('role') == 'user':
                llm_chat_history.append(HumanMessage(content=msg.get('content', '')))
            elif msg.get('role') == 'ai':
                llm_chat_history.append(AIMessage(content=msg.get('content', '')))
        # Use a strict system prompt for chatbot
        answer_html, _ = analyze_with_llm(question, retriever, llm_chat_history)
        return JsonResponse({'answer': answer_html})
    return JsonResponse({'error': 'Invalid request method.'}, status=405)
