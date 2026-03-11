
# =====================
# Imports
# =====================
import os
import langchain
import io
import re
import json
import requests
import markdown
from datetime import date
from django.core.mail import send_mail
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.csrf import csrf_exempt
from reportlab.pdfgen import canvas
from analyzer.models import HealthData, UploadedReport
import firebase_admin
from firebase_admin import credentials, firestore
from pinecone import Pinecone, ServerlessSpec
from langchain_core.tools import Tool
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, SystemMessagePromptTemplate
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_pinecone import Pinecone as PineconeStore
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough





# --- Django View: Chatbot Ask ---
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse


# =====================
# Utility Functions
# =====================

# Default prompt template for image analysis. You can override this by
# setting the IMAGE_PROMPT_TEMPLATE environment variable or by passing a
# custom `user_prompt` to `analyze_medical_image_with_gemini`.
DEFAULT_IMAGE_PROMPT = (
    "You are an expert medical image analyst. Analyze this medical image "
    "and provide a comprehensive structured assessment."
)


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

# Initialize Firebase
firebase_app = None
def get_firebase_db():
    global firebase_app
    if not firebase_admin._apps:
        cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
        firebase_app = firebase_admin.initialize_app(cred)
    return firestore.client()


def get_embeddings():
    """Return Google Generative AI embeddings."""
    from langchain_google_genai import GoogleGenerativeAIEmbeddings
    return GoogleGenerativeAIEmbeddings(model="gemini-embedding-001",output_dimensionality=768)


def extract_text_from_pdf(file_path):
    """Extract text from a PDF file."""
    try:
        from pypdf import PdfReader
        pdf_text = ""
        with open(file_path, 'rb') as f:
            reader = PdfReader(f)
            for page in reader.pages:
                pdf_text += page.extract_text() + "\n"
        return pdf_text
    except ImportError:
        # Fallback: use PyPDFLoader
        try:
            loader = PyPDFLoader(file_path)
            docs = loader.load()
            return "\n".join([doc.page_content for doc in docs])
        except Exception as e:
            print(f"[ERROR] PDF extraction failed: {e}")
            return ""


def analyze_medical_image_with_gemini(image_path, user_prompt=""):
    """Analyze a medical image using Gemini Vision and return HTML/text.

    This helper handles:
    1. API key validation
    2. Image encoding
    3. Model initialization
    4. Sending prompt+image to Gemini
    5. Returning markdown-rendered HTML and raw text

    Prompting:
    - Defaults to :data:`DEFAULT_IMAGE_PROMPT` defined earlier
    - You may override with the ``IMAGE_PROMPT_TEMPLATE`` environment
      variable or by providing ``user_prompt`` when calling the function.

    The prompt encourages Gemini to include:
      - Condition type/severity
      - Physiological explanation
      - Natural remedies (5+ items)
      - Medical treatments and medications
      - Prevention, aftercare, red flags, and timelines
    """
    import base64
    
    # Ensure API key exists
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        return (
            "<p style='color: red;'><strong>Configuration Error:</strong> "
            "Google API key missing. Set GOOGLE_API_KEY in .env.</p>",
            "API key not configured"
        )

    # encode image
    try:
        with open(image_path, 'rb') as f:
            image_data = base64.standard_b64encode(f.read()).decode('utf-8')
    except FileNotFoundError:
        msg = f"Image file not found: {image_path}"
        return f"<p style='color: red;'>{msg}</p>", msg

    ext = image_path.lower().split('.')[-1]
    media_type_map = {'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'png': 'image/png',
                      'gif': 'image/gif', 'webp': 'image/webp'}
    media_type = media_type_map.get(ext, 'image/jpeg')

    # init model
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_core.messages import HumanMessage
    try:
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
    except Exception as init_error:
        return (
            f"<p style='color: red;'>API init error: {init_error}</p>",
            f"API init error: {init_error}"
        )

    # build comprehensive analysis prompt with structured output
    base_prompt = user_prompt or os.getenv("IMAGE_PROMPT_TEMPLATE", DEFAULT_IMAGE_PROMPT)
    analysis_prompt = f"""{base_prompt}

Please provide a comprehensive analysis in the following structured format:

## 1. Condition Identification & Properties
- **Condition Name**: What condition is visible? (e.g., laceration, rash, wound, skin condition, burn, etc.)
- **Severity Level**: mild, moderate, or severe
- **Characteristics**: Color, texture, size, location on body, appearance details
- **Type/Classification**: The medical category of this condition
- **Duration Estimate**: Approximate age or timeline of the condition

## 2. Pathophysiology & Causes
- Explain the physiological/biological mechanism causing this condition
- List the most common causes (3-5 primary causes)
- Explain why it manifests this way on the skin/body

## 3. Natural Remedies & Home Treatments
Provide AT LEAST 5-7 natural, home-based treatment options:
For each remedy, include:
- **Remedy Name** – What it is and how it works
- **Ingredients/Application** – Complete preparation and application instructions
- **Dosage & Duration** – How long to use for visible results
- **Efficacy & Evidence** – Why it works and any scientific basis
- **Precautions & Side Effects** – Warnings and contraindications
- **Cost & Availability** – Estimated cost and where to find

Include remedies such as:
- Herbal treatments (turmeric, aloe vera, calendula, etc.)
- Essential oils and aromatherapy
- Dietary modifications and supplements
- Topical natural preparations
- Lifestyle and behavioral modifications
- Traditional/Ayurvedic/homeopathic solutions

## 4. Medical Treatments & Medications
- **Over-the-Counter Options** (with specific product names, dosages, instructions)
- **Prescription Medications** (types available; note that doctor consultation is needed)
- **Professional Procedures** (laser therapy, microdermabrasion, steroid injections, etc.)
- **Expected Results Timeline** – How long each treatment typically takes for visible improvement
- **Cost Estimates** – Approximate costs for each option

## 5. Prevention & Aftercare Strategies
- How to prevent this condition or prevent recurrence
- Daily care routine
- Lifestyle modifications
- Environmental controls
- Protective measures
- When to seek professional help to prevent worsening

## 6. Red Flags & When to Seek Medical Attention
List specific warning signs that require immediate professional evaluation:
- Signs of infection (pus, increased redness, warmth, fever, red streaks)
- Spreading or rapid changes
- Severe pain or numbness
- Loss of function or mobility
- Non-healing after expected timeline
- Complications or unexpected symptoms
- Mental health concerns (if applicable to self-harm)
- Any situation requiring professional diagnosis or treatment

## 7. Timeline & Expected Outcomes
- **Natural Remedy Timeline**: How long before natural treatments show results
- **Medical Treatment Timeline**: How quickly each medical option works
- **Recovery Milestones**: Expected progression of healing
- **Realistic Expectations**: What improvements can be expected vs. what cannot

## 8. Important Medical Disclaimer
⚠️ Always include that this analysis is for informational purposes only and a licensed healthcare professional must be consulted for diagnosis and treatment decisions.

Format your response using:
- Clear markdown headings
- Bullet points and numbered lists
- Tables for comparisons where appropriate
- Bold text for emphasis on important details"""

    message = HumanMessage(content=[
        {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{image_data}"}},
        {"type": "text", "text": analysis_prompt}
    ])

    try:
        response = llm.invoke([message])
        text = response.content if hasattr(response, 'content') else str(response)
    except Exception as e:
        print(f"[ERROR] Image analysis failed: {e}")
        return (f"<p style='color:red;'>Error: {e}</p>", str(e))

    html = markdown.markdown(text, extensions=["tables", "fenced_code"])
    return html, text



def process_pdf(file_path, namespace=None, mode="create"):
    pinecone_api_key = os.getenv('PINECONE_API_KEY')
    pinecone_region = os.getenv('PINECONE_REGION', 'us-east-1')
    pc = Pinecone(api_key=pinecone_api_key)
    index_name = 'medical-analyzer-index'
    dimension = 768  # Google embedding-001 produces 768-dimensional vectors

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
    """Analyze medical information using LLM with explicit health data extraction."""
    from google.api_core.exceptions import ResourceExhausted, TooManyRequests
    
    try:
        import pinecone.core.client.exceptions as pinecone_exceptions
    except ImportError:
        class pinecone_exceptions:
            class RateLimitException(Exception):
                pass

    # System prompt with explicit instructions for health data extraction
    system_prompt ="""
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

    model = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite")
    
    # Build chat history
    valid_types = (HumanMessage, AIMessage, SystemMessage)
    if chat_history is None:
        chat_history = []
    if hasattr(chat_history, 'messages'):
        chat_history = chat_history.messages
    chat_history = [m for m in chat_history if isinstance(m, valid_types)]
    
    # Prepare full input with context
    full_input = user_input
    if context:
        full_input = f"{user_input}\n\n--- Medical Report Context ---\n{context}"
    
    try:
        messages = [SystemMessage(content=system_prompt)] + chat_history + [HumanMessage(content=full_input)]
        response = model.invoke(full_input)
        answer = response.content if hasattr(response, 'content') else str(response)
        
    except (ResourceExhausted, TooManyRequests) as e:
        answer = "Sorry, the Gemini API is currently rate-limited. Please try again in a few minutes."
    except pinecone_exceptions.RateLimitException as e:
        answer = "Sorry, the service is currently rate-limited. Please try again later."
    except Exception as e:
        print(f"[ERROR] LLM error: {e}")
        answer = f"Error during analysis: {str(e)}"
    
    # Extract health data JSON from response
    health_data = extract_health_data_from_llm_output(answer)
    print(f"[DEBUG] Extracted health data: {health_data}")
    
    # Render markdown to HTML
    answer_html = markdown.markdown(answer, extensions=["tables", "fenced_code"])
    return answer_html, health_data


def save_health_data_to_db(health_data, patient_id, report_date=None, pdf_text=None, report=None):
    if report_date is None:
        report_date = date.today()
    for entry in health_data:
        # Normalize parameter key
        param = entry.get('parameter') or entry.get('test') or entry.get('name') or ''
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
            unit=unit,
            report=report
        )

# --- LangChain Tool Objects (define after all get_* functions) ---

# MedGamma-only image explanation tool

# utils/medimage_explainer.py
import os
import json
import requests

def explain_medical_image(image_path: str) -> str:
    """
    Explain a medical image using a Hugging Face vision-language model.
    Requires: HF_API_KEY environment variable.
    """
    api_key = os.getenv("HF_TOKEN")
    if not api_key:
        return "⚠️ Missing Hugging Face API key. Please set HF_API_KEY."

    endpoint = "https://api-inference.huggingface.co/models/microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224"

    try:
        with open(image_path, "rb") as f:
            image_bytes = f.read()

        headers = {"Authorization": f"Bearer {api_key}"}
        response = requests.post(endpoint, headers=headers, data=image_bytes, timeout=30)

        if response.status_code != 200:
            return f"❌ Model API Error: {response.text}"

        data = response.json()

        return json.dumps(data, indent=2)

    except Exception as e:
        return f"Error analyzing image: {str(e)}"


# Create LangChain tool
huggingface_medimage_tool = Tool(
    name="Medical Image Explainer (Hugging Face)",
    description="Explains medical images (rashes, lesions, etc.) using Hugging Face medical vision model.",
    func=explain_medical_image,
)



def check_drug_interactions_drugbank(drugs_list):
    """
    Checks for drug interactions using the DrugBank API.
    Returns a list of interaction descriptions or an empty list if none found.
    Requires DrugBank API key in environment variable DRUGBANK_API_KEY.
    """
    api_key = os.getenv("DRUGBANK_API_KEY")
    if not api_key:
        print("[DrugBank] API key not set (DRUGBANK_API_KEY)")
        return ["DrugBank API key not configured."]
    base_url = "https://api.drugbank.com/v1/drug-interactions"
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        params = {"drugs": ",".join(drugs_list)}
        resp = requests.get(base_url, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        interactions = []
        for interaction in data.get("interactions", []):
            desc = interaction.get("description", "No description")
            interactions.append(desc)
        return interactions if interactions else ["No interactions found."]
    except Exception as e:
        print(f"[ERROR] DrugBank API: {e}")
        return ["Could not check drug interactions."]


drugbank_interaction_tool = Tool(
    name="drugbank_interactions",
    description="Check for drug interactions using DrugBank API.",
    func=check_drug_interactions_drugbank,
)


def check_symptoms(symptoms_list):
    """
    Suggests possible conditions based on a list of symptoms using an LLM prompt.
    Returns a list of likely diseases/conditions.
    """
    from langchain_google_genai import ChatGoogleGenerativeAI
    model = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite")
    prompt = (
        "Given the following symptoms: " + ", ".join(symptoms_list) +
        ". List the most likely diseases or conditions, and explain briefly why."
    )
    try:
        response = model.invoke(prompt)
        # Extract conditions from response (simple split, can be improved)
        return response.content if hasattr(response, 'content') else str(response)
    except Exception as e:
        print(f"[ERROR] Symptom checker LLM: {e}")
        return "Could not analyze symptoms."
    
    
symptom_checker_tool = Tool(
    name="symptom_checker",
    description="Suggest possible conditions based on symptoms using LLM.",
    func=check_symptoms,
)


# --- Modular Tool Functions ---
def get_remedies(disease):
    """
    Returns remedies for a given disease/abnormality.
    This can be expanded to query a database or API.
    """
    remedies = {
        "diabetes": [
            "Dietary modifications: Low sugar, high fiber foods",
            "Allopathic: Metformin, Insulin",
            "Ayurvedic: Jamun, Bitter gourd",
            "Homeopathic: Syzygium jambolanum",
            "Precautions: Regular blood sugar monitoring"
        ],
        "hypertension": [
            "Dietary: Low salt, DASH diet",
            "Allopathic: ACE inhibitors, Beta blockers",
            "Ayurvedic: Ashwagandha, Garlic",
            "Homeopathic: Rauwolfia",
            "Precautions: Regular BP checks"
        ]
    }
    return remedies.get(disease.lower(), ["No remedies found. Consult a doctor."])

remedies_tool = Tool(
    name="remedies",
    description="Get remedies for a disease or abnormality.",
    func=get_remedies,
)


def get_research_papers_api(disease):
    """
    Fetches recent research papers for a disease using the PubMed E-utilities API.
    Returns a list of dicts: {title, summary, link}.
    """
    # Step 1: Search PubMed for relevant articles
    search_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={disease}&retmax=3&retmode=json"
    try:
        search_resp = requests.get(search_url, timeout=10)
        search_resp.raise_for_status()
        search_data = search_resp.json()
        id_list = search_data.get("esearchresult", {}).get("idlist", [])
        if not id_list:
            return []
        # Step 2: Fetch details for each article
        ids = ",".join(id_list)
        fetch_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={ids}&retmode=json"
        fetch_resp = requests.get(fetch_url, timeout=10)
        fetch_resp.raise_for_status()
        fetch_data = fetch_resp.json()
        papers = []
        for pid in id_list:
            doc = fetch_data.get("result", {}).get(pid, {})
            title = doc.get("title", "No title")
            summary = doc.get("elocationid", "No summary available.")
            link = f"https://pubmed.ncbi.nlm.nih.gov/{pid}/"
            papers.append({
                "title": title,
                "summary": summary,
                "link": link
            })
        return papers
    except Exception as e:
        print(f"[ERROR] PubMed API: {e}")
        return []


research_papers_tool = Tool(
    name="research_papers",
    description="Fetch recent research papers for a disease using Semantic Scholar API.",
    func=get_research_papers_api,
)




def get_exercises(disease):
    """
    Suggests exercises for a disease/condition.
    """
    exercises = {
        "diabetes": ["Walking", "Yoga", "Cycling"],
        "hypertension": ["Breathing exercises", "Yoga", "Swimming"]
    }
    return exercises.get(disease.lower(), ["Consult a physiotherapist for personalized exercises."])


exercises_tool = Tool(
    name="exercises",
    description="Suggest exercises for a disease or condition.",
    func=get_exercises,
)




def get_yoga_videos(disease):
    """
    Provides video links for yoga related to a disease.
    """
    videos = {
        "diabetes": ["https://youtube.com/diabetes-yoga1", "https://youtube.com/diabetes-yoga2"],
        "hypertension": ["https://youtube.com/hypertension-yoga1"]
    }
    return videos.get(disease.lower(), ["No specific yoga videos found."])


yoga_videos_tool = Tool(
    name="yoga_videos",
    description="Provide yoga video links for a disease.",
    func=get_yoga_videos,
)

def dall_e_api(prompt):
    """
    Calls Dall-E API to generate a medical image from a prompt.
    Returns image URL or base64 string.
    """
    # Placeholder: Replace with actual Dall-E API integration
    # Example: Use OpenAI API if available
    # import openai
    # response = openai.Image.create(prompt=prompt, n=1, size="512x512")
    # return response['data'][0]['url']
    return "https://via.placeholder.com/512x512?text=Dall-E+Image"

dall_e_tool = Tool(
    name="dall_e",
    description="Generate a medical image from a prompt using Dall-E API.",
    func=dall_e_api,
)

def google_imagen_api(prompt):
    """
    Calls Google Imagen API to generate a medical image from a prompt.
    Returns image URL or base64 string.
    """
    # Placeholder: Replace with actual Google Imagen API integration
    return "https://via.placeholder.com/512x512?text=Imagen+Image"

google_imagen_tool = Tool(
    name="google_imagen",
    description="Generate a medical image from a prompt using Google Imagen API.",
    func=google_imagen_api,
)

medical_tools = [
    remedies_tool,
    research_papers_tool,
    exercises_tool,
    yoga_videos_tool,
    symptom_checker_tool,
    drugbank_interaction_tool,
    huggingface_medimage_tool,
    dall_e_tool,
    google_imagen_tool
]

# Central LLM for medical assistance (simplified without Agent)
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")

# Simple medical assistant class that wraps the LLM
class MedicalAssistant:
    def __init__(self, llm_instance):
        self.llm = llm_instance
    
    def run(self, input_text):
        """Run the LLM with medical context and return response."""
        system_prompt = """You are a helpful medical assistant with access to medical information.
        Provide accurate, helpful information about medical topics, health parameters, symptoms, and remedies.
        Always recommend consulting with a healthcare professional for serious conditions."""
        
        message = f"{system_prompt}\n\nUser request: {input_text}"
        try:
            response = self.llm.invoke(message)
            return response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            return f"Error processing request: {str(e)}"

medical_agent = MedicalAssistant(llm)

## Example usage:
# response = medical_agent.run("What are the remedies for diabetes?")
# print(response)



#pdf export

def export_annotation_pdf(image_url, explanation, generated_image_url=None):
    """
    Export the annotation (image, explanation, generated image) as a PDF.
    Returns a Django HttpResponse with PDF content.
    """
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer)
    y = 800
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, y, "Medical Image Annotation Report")
    y -= 40
    p.setFont("Helvetica", 12)
    p.drawString(50, y, f"Explanation: {explanation}")
    y -= 40
    if image_url:
        p.drawString(50, y, f"Image: {image_url}")
        y -= 40
    if generated_image_url:
        p.drawString(50, y, f"Generated Image: {generated_image_url}")
        y -= 40
    p.showPage()
    p.save()
    buffer.seek(0)
    return HttpResponse(buffer, content_type='application/pdf')
