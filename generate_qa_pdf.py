#!/usr/bin/env python3
"""
Medical Analyzer Project - Comprehensive Q&A for RAG, LLM, and GenAI Interview
Generated PDF with Questions and Answers covering all project concepts
"""

import os
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, ListFlowable, ListItem
from reportlab.lib.units import inch
from reportlab.lib.colors import blue, black, darkblue
from datetime import datetime

def create_qa_pdf():
    """Create a comprehensive Q&A PDF for the Medical Analyzer project."""

    # Create PDF filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pdf_filename = f"Medical_Analyzer_QA_RAG_LLM_{timestamp}.pdf"

    # Create the PDF document
    doc = SimpleDocTemplate(pdf_filename, pagesize=A4)
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Title'],
        fontSize=24,
        spaceAfter=30,
        alignment=1,  # Center alignment
        textColor=darkblue
    )

    question_style = ParagraphStyle(
        'Question',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=10,
        textColor=blue,
        fontName='Helvetica-Bold'
    )

    answer_style = ParagraphStyle(
        'Answer',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=15,
        leftIndent=20
    )

    section_style = ParagraphStyle(
        'Section',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=20,
        textColor=darkblue
    )

    # Content elements
    elements = []

    # Title Page
    elements.append(Paragraph("Medical Analyzer Project", title_style))
    elements.append(Paragraph("Comprehensive Q&A Guide", styles['Title']))
    elements.append(Paragraph("RAG, LLM, and Generative AI Interview Preparation", styles['Title']))
    elements.append(Spacer(1, 0.5*inch))
    elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%B %d, %Y')}", styles['Normal']))
    elements.append(PageBreak())

    # Table of Contents
    elements.append(Paragraph("Table of Contents", section_style))
    toc_items = [
        "1. Project Overview & Architecture",
        "2. Django Framework Integration",
        "3. Retrieval-Augmented Generation (RAG) Deep Dive",
        "4. Large Language Models (LLM) Integration",
        "5. Vector Databases & Embeddings",
        "6. Agentic AI Implementation",
        "7. PDF Processing & Document Intelligence",
        "8. Chat History & Context Management",
        "9. Health Data Extraction & NLP",
        "10. API Integration & External Services",
        "11. Performance & Scalability",
        "12. Security & Compliance",
        "13. Interview Preparation Questions"
    ]

    for item in toc_items:
        elements.append(Paragraph(item, styles['Normal']))
    elements.append(PageBreak())

    # Section 1: Project Overview
    elements.append(Paragraph("1. Project Overview & Architecture", section_style))

    questions_answers = [
        ("What is the Medical Analyzer project and its core purpose?",
         "The Medical Analyzer is a Django-based web application that allows users to upload medical reports (PDFs), analyze them using AI, ask questions about their health data through a chatbot interface, check symptoms, and track health trends over time. It combines traditional web development with modern AI capabilities including RAG, LLMs, and computer vision."),

        ("What are the main technologies used in this project?",
         "Core technologies include: Django (web framework), PostgreSQL (database), LangChain (AI orchestration), Google Gemini (LLM), Pinecone (vector database), Firebase (additional storage), ReportLab (PDF generation), and various PDF processing libraries like PyPDF and PyPDFLoader."),

        ("Explain the system architecture from a high level.",
         "The architecture follows a layered approach: 1) Frontend (Django templates with Bootstrap), 2) Backend (Django views handling business logic), 3) AI Layer (LangChain orchestrating RAG pipeline), 4) Data Layer (PostgreSQL for structured data, Pinecone for vector embeddings, Firebase for NoSQL storage), and 5) External APIs (Google Gemini, Pinecone)."),

        ("How does the application handle user data privacy?",
         "User data is protected through Django's authentication system, encrypted database connections, secure API key management via environment variables, and proper session handling. Medical data is stored with user-specific access controls.")
    ]

    for question, answer in questions_answers:
        elements.append(Paragraph(f"Q: {question}", question_style))
        elements.append(Paragraph(f"A: {answer}", answer_style))
        elements.append(Spacer(1, 0.1*inch))

    elements.append(PageBreak())

    # Section 2: Django Integration
    elements.append(Paragraph("2. Django Framework Integration", section_style))

    django_qa = [
        ("How is Django integrated with the AI components?",
         "Django serves as the web framework handling HTTP requests, user authentication, file uploads, and database operations. The AI components (LangChain, LLM calls) are integrated through utility functions in utils.py that are called from Django views. This separation allows clean architecture where Django manages the web layer and AI utilities handle the intelligence layer."),

        ("Explain the model relationships in the context of AI features.",
         "The UploadedReport model stores PDF files and links to users. ChatHistory model maintains conversation threads tied to specific reports. HealthData model stores extracted medical parameters. This relational structure enables the AI system to provide contextual responses based on user's medical history and specific report analysis.")
    ]

    for question, answer in django_qa:
        elements.append(Paragraph(f"Q: {question}", question_style))
        elements.append(Paragraph(f"A: {answer}", answer_style))
        elements.append(Spacer(1, 0.1*inch))

    elements.append(PageBreak())

    # Section 3: RAG Deep Dive
    elements.append(Paragraph("3. Retrieval-Augmented Generation (RAG) Deep Dive", section_style))

    rag_qa = [
        ("What is RAG and how is it implemented in this project?",
         "RAG (Retrieval-Augmented Generation) combines information retrieval with generative AI. In this project, when a user uploads a PDF report, the system: 1) Extracts text using PyPDFLoader, 2) Splits text into chunks with RecursiveCharacterTextSplitter, 3) Creates vector embeddings using Google Generative AI embeddings, 4) Stores vectors in Pinecone with report-specific namespaces, 5) Retrieves relevant chunks during Q&A, 6) Passes retrieved context to Gemini LLM for answer generation."),

        ("Explain the process_pdf function and its role in RAG.",
         "The process_pdf function implements the core RAG pipeline: In 'create' mode, it loads PDF, splits into 5000-character chunks with 500-character overlap, creates embeddings, and stores in Pinecone. In 'retrieve' mode, it creates a retriever from existing vectors. Namespaces ensure report isolation. The function returns a LangChain retriever that can fetch relevant document chunks based on semantic similarity."),

        ("How does text chunking work in this RAG implementation?",
         "Text is split using RecursiveCharacterTextSplitter with chunk_size=5000 and chunk_overlap=500. This ensures: 1) Chunks fit within LLM context windows, 2) Overlap prevents information loss at chunk boundaries, 3) Recursive splitting respects document structure (paragraphs, sentences). This chunking strategy maintains semantic coherence while enabling efficient retrieval."),

        ("What embeddings model is used and why?",
         "Google Generative AI embeddings (model='gemini-embedding-001') with 768-dimensional vectors. Chosen because: 1) High quality semantic understanding, 2) Native integration with Gemini LLM, 3) Cost-effective, 4) Optimized for retrieval tasks. The embeddings capture medical terminology and contextual relationships effectively."),

        ("How are namespaces used in Pinecone for multi-user support?",
         "Each uploaded report gets a unique namespace (f'report_{report.id}'). This ensures: 1) User data isolation, 2) Efficient retrieval scoped to specific reports, 3) Ability to delete report vectors without affecting others. Namespaces act as logical partitions within the shared Pinecone index."),

        ("Explain the retriever implementation and its parameters.",
         "The retriever is created using vectorstore.as_retriever() with default parameters (k=4 relevant chunks). It uses cosine similarity for ranking. During Q&A, the retriever fetches semantically similar chunks from the report's namespace, providing context to the LLM for accurate, document-grounded answers."),

        ("How does RAG improve upon direct LLM questioning?",
         "RAG addresses LLM limitations: 1) Prevents hallucinations by grounding answers in actual document content, 2) Handles large documents beyond context windows, 3) Provides up-to-date information from user-specific reports, 4) Enables precise medical analysis rather than generic advice, 5) Maintains factual accuracy through retrieval verification.")
    ]

    for question, answer in rag_qa:
        elements.append(Paragraph(f"Q: {question}", question_style))
        elements.append(Paragraph(f"A: {answer}", answer_style))
        elements.append(Spacer(1, 0.1*inch))

    elements.append(PageBreak())

    # Section 4: LLM Integration
    elements.append(Paragraph("4. Large Language Models (LLM) Integration", section_style))

    llm_qa = [
        ("Which LLM is used and why was it chosen?",
         "Google Gemini 2.5-flash and 2.5-flash-lite models. Chosen for: 1) Excellent medical knowledge, 2) Multimodal capabilities (text + images), 3) Cost-effective API pricing, 4) Strong reasoning capabilities, 5) Native integration with Google ecosystem. Flash-lite is used for cost optimization on routine tasks."),

        ("Explain the analyze_with_llm function architecture.",
         "analyze_with_llm orchestrates the complete LLM interaction: 1) Constructs system prompt with medical analysis instructions, 2) Builds chat history from HumanMessage/AIMessage objects, 3) Combines user input with retrieved context, 4) Invokes Gemini model, 5) Extracts structured health data from response, 6) Returns formatted HTML and parsed JSON data."),

        ("How is the system prompt structured for medical analysis?",
         "The system prompt includes: 1) Role definition as medical AI assistant, 2) Structured output format (Summary, Key Parameters, Diseases, Remedies, Research), 3) Explicit instructions for health data extraction, 4) Safety disclaimers, 5) Full medical report context. This ensures consistent, medically-focused responses with structured data extraction."),

        ("Explain health data extraction from LLM responses.",
         "The extract_health_data_from_llm_output function uses regex to find JSON arrays in LLM responses. It looks for '## Extracted Health Data (JSON)' sections and parses the array into Python dictionaries containing parameter, value, unit, and date information. This structured extraction enables database storage and trend analysis."),

        ("How does chat history integration work?",
         "Chat history is reconstructed from stored messages into LangChain message objects (HumanMessage, AIMessage). The LLM receives full conversation context, enabling coherent multi-turn conversations. History prevents repetitive answers and maintains conversation flow about specific medical reports."),

        ("What error handling is implemented for LLM calls?",
         "Comprehensive error handling includes: 1) ResourceExhausted/TooManyRequests for API limits, 2) Pinecone rate limit exceptions, 3) Generic exception catching with user-friendly messages, 4) Graceful degradation when services are unavailable. Users see helpful error messages instead of technical stack traces."),

        ("How does the LLM handle multimodal inputs (text + images)?",
         "For medical images, analyze_medical_image_with_gemini encodes images as base64, sends to Gemini Vision API with structured prompts for medical analysis. The LLM provides detailed condition identification, severity assessment, physiological explanations, and treatment recommendations in formatted output.")
    ]

    for question, answer in llm_qa:
        elements.append(Paragraph(f"Q: {question}", question_style))
        elements.append(Paragraph(f"A: {answer}", answer_style))
        elements.append(Spacer(1, 0.1*inch))

    elements.append(PageBreak())

    # Section 5: Vector Databases & Embeddings
    elements.append(Paragraph("5. Vector Databases & Embeddings", section_style))

    vector_qa = [
        ("Why Pinecone over other vector databases?",
         "Pinecone chosen for: 1) Managed service (no infrastructure management), 2) High performance similarity search, 3) Easy integration with LangChain, 4) Serverless scaling, 5) Cost-effective for this use case. Its cosine similarity and metadata filtering capabilities perfectly suit medical document retrieval."),

        ("Explain the embedding creation process.",
         "Google Generative AI embeddings convert text chunks into 768-dimensional vectors. The process: 1) Text chunks from RecursiveCharacterTextSplitter, 2) Embeddings API call, 3) Vector storage in Pinecone with metadata (chunk content, source document), 4) Cosine similarity for retrieval. This captures semantic meaning of medical terminology."),

        ("How does vector similarity search work in practice?",
         "When user asks a question: 1) Question is embedded into vector, 2) Pinecone finds k most similar document chunks using cosine similarity, 3) Retrieved chunks provide context to LLM, 4) LLM generates answer grounded in actual document content. This ensures factual, document-specific medical answers."),

        ("What are the benefits of using embeddings for medical documents?",
         "Embeddings enable: 1) Semantic search (understanding meaning, not just keywords), 2) Handling medical synonyms and terminology variations, 3) Cross-language medical concept matching, 4) Efficient retrieval from large document collections, 5) Better context preservation than keyword matching.")
    ]

    for question, answer in vector_qa:
        elements.append(Paragraph(f"Q: {question}", question_style))
        elements.append(Paragraph(f"A: {answer}", answer_style))
        elements.append(Spacer(1, 0.1*inch))

    elements.append(PageBreak())

    # Section 6: Agentic AI Implementation
    elements.append(Paragraph("6. Agentic AI Implementation", section_style))

    agentic_qa = [
        ("What agentic AI concepts are implemented?",
         "The system implements agentic behaviors through: 1) Autonomous health data extraction during upload, 2) Dynamic symptom analysis with structured recommendations, 3) Context-aware chatbot responses, 4) Multi-step reasoning in medical analysis. The 'medical_agent' in symptom checker demonstrates agentic capabilities with tool use and structured output."),

        ("Explain the symptom checker agent implementation.",
         "The symptom checker uses a structured prompt that guides the LLM to act as a medical agent: 1) Analyze symptoms systematically, 2) Consider multiple medical conditions, 3) Assess severity levels, 4) Provide evidence-based recommendations, 5) Include appropriate disclaimers. This agentic approach ensures comprehensive, responsible medical guidance."),

        ("How does the system demonstrate autonomous behavior?",
         "Autonomous features include: 1) Automatic PDF processing and health data extraction upon upload, 2) Proactive health parameter identification, 3) Intelligent context retrieval for relevant answers, 4) Structured report analysis without user prompting. The system acts autonomously within defined medical analysis boundaries."),

        ("What tools and capabilities does the medical agent have?",
         "The agent can: 1) Access medical knowledge bases implicitly through LLM training, 2) Process and analyze medical documents, 3) Extract structured health data, 4) Provide differential diagnoses, 5) Generate treatment recommendations, 6) Maintain conversation context, 7) Handle multimodal medical data (text reports, images).")
    ]

    for question, answer in agentic_qa:
        elements.append(Paragraph(f"Q: {question}", question_style))
        elements.append(Paragraph(f"A: {answer}", answer_style))
        elements.append(Spacer(1, 0.1*inch))

    elements.append(PageBreak())

    # Section 7: PDF Processing & Document Intelligence
    elements.append(Paragraph("7. PDF Processing & Document Intelligence", section_style))

    pdf_qa = [
        ("How is PDF text extraction implemented?",
         "Dual approach: 1) Primary: pypdf.PdfReader for direct text extraction, 2) Fallback: LangChain PyPDFLoader. This ensures robust extraction from various PDF formats including scanned documents. Text is cleaned and prepared for chunking and embedding."),

        ("Explain the document intelligence pipeline.",
         "Document intelligence flow: 1) PDF upload and validation, 2) Text extraction with fallback handling, 3) Intelligent chunking preserving medical context, 4) Vector embedding creation, 5) Storage in Pinecone with metadata, 6) Retrieval-augmented analysis, 7) Structured health data extraction, 8) Database storage for trending."),

        ("How does the system handle different PDF types?",
         "The system handles: 1) Text-based PDFs (direct extraction), 2) Image-based PDFs (OCR through processing libraries), 3) Mixed content PDFs (hybrid extraction). Error handling ensures graceful degradation, with user notification of processing issues.")
    ]

    for question, answer in pdf_qa:
        elements.append(Paragraph(f"Q: {question}", question_style))
        elements.append(Paragraph(f"A: {answer}", answer_style))
        elements.append(Spacer(1, 0.1*inch))

    elements.append(PageBreak())

    # Section 8: Chat History & Context Management
    elements.append(Paragraph("8. Chat History & Context Management", section_style))

    chat_qa = [
        ("How is conversation context maintained?",
         "Chat history stored in ChatHistory model with foreign keys to User and UploadedReport. Each conversation thread is isolated by report, ensuring context relevance. Messages reconstructed into LangChain format for LLM consumption."),

        ("Explain the reconstruct_chat_history function.",
         "This function filters and converts stored chat messages into valid LangChain message objects. It handles: 1) Type validation (HumanMessage, AIMessage, SystemMessage), 2) Content extraction from various formats, 3) Filtering out invalid or corrupted messages, 4) Maintaining chronological order for coherent conversations."),

        ("How does context affect answer quality?",
         "Context enables: 1) Follow-up questions understanding previous discussion, 2) Reference to specific report sections, 3) Consistent medical analysis across conversation turns, 4) Prevention of repetitive or contradictory answers, 5) Building upon previous explanations and recommendations.")
    ]

    for question, answer in chat_qa:
        elements.append(Paragraph(f"Q: {question}", question_style))
        elements.append(Paragraph(f"A: {answer}", answer_style))
        elements.append(Spacer(1, 0.1*inch))

    elements.append(PageBreak())

    # Section 9: Health Data Extraction & NLP
    elements.append(Paragraph("9. Health Data Extraction & NLP", section_style))

    nlp_qa = [
        ("How is structured health data extracted from unstructured text?",
         "The LLM uses prompt engineering to identify and extract health parameters. The system prompt instructs extraction of parameter names, values, units, and dates. Regex parsing then converts the LLM's structured output into database-ready JSON format."),

        ("What NLP techniques are employed?",
         "NLP approaches include: 1) Named Entity Recognition for medical terms, 2) Relation extraction for parameter-value pairs, 3) Temporal information extraction for dates, 4) Unit normalization for consistent measurements, 5) Context-aware parsing for medical abbreviations."),

        ("How is data quality ensured in extraction?",
         "Quality measures: 1) LLM validation against medical knowledge, 2) Structured output format enforcement, 3) Unit consistency checking, 4) Date format standardization, 5) Manual review capabilities, 6) Error handling for extraction failures.")
    ]

    for question, answer in nlp_qa:
        elements.append(Paragraph(f"Q: {question}", question_style))
        elements.append(Paragraph(f"A: {answer}", answer_style))
        elements.append(Spacer(1, 0.1*inch))

    elements.append(PageBreak())

    # Section 10: API Integration & External Services
    elements.append(Paragraph("10. API Integration & External Services", section_style))

    api_qa = [
        ("How are multiple APIs coordinated?",
         "APIs are orchestrated through: 1) Environment variable configuration, 2) Centralized utility functions, 3) Error handling and fallback mechanisms, 4) Rate limit management, 5) Secure key storage. Each service has dedicated integration functions while maintaining loose coupling."),

        ("Explain the API key management strategy.",
         "API keys stored in .env file, loaded via python-dotenv. Accessed through os.getenv() with fallback defaults for development. Keys never logged or exposed in error messages. Different keys for different environments (dev/staging/prod)."),

        ("How are API failures handled gracefully?",
         "Failure handling includes: 1) Try-catch blocks with specific exception types, 2) User-friendly error messages, 3) Graceful degradation (continue with limited functionality), 4) Retry logic for transient failures, 5) Fallback to cached or default responses.")
    ]

    for question, answer in api_qa:
        elements.append(Paragraph(f"Q: {question}", question_style))
        elements.append(Paragraph(f"A: {answer}", answer_style))
        elements.append(Spacer(1, 0.1*inch))

    elements.append(PageBreak())

    # Section 11: Performance & Scalability
    elements.append(Paragraph("11. Performance & Scalability", section_style))

    perf_qa = [
        ("How is the system optimized for performance?",
         "Performance optimizations: 1) Asynchronous processing where possible, 2) Efficient vector retrieval with namespace isolation, 3) Database query optimization, 4) Caching of frequent operations, 5) Chunk size optimization for LLM context, 6) Background processing for heavy operations."),

        ("What scalability considerations are implemented?",
         "Scalability features: 1) Stateless Django views, 2) Horizontal scaling capability, 3) External service dependencies (Pinecone, Gemini) handle scaling, 4) Database connection pooling, 5) CDN-ready static file serving, 6) Microservice-ready architecture."),

        ("How are large documents handled efficiently?",
         "Large document handling: 1) Chunking prevents context window overflow, 2) Selective retrieval reduces processing load, 3) Progressive loading for UI responsiveness, 4) Background processing for uploads, 5) Memory-efficient text processing.")
    ]

    for question, answer in perf_qa:
        elements.append(Paragraph(f"Q: {question}", question_style))
        elements.append(Paragraph(f"A: {answer}", answer_style))
        elements.append(Spacer(1, 0.1*inch))

    elements.append(PageBreak())

    # Section 12: Security & Compliance
    elements.append(Paragraph("12. Security & Compliance", section_style))

    security_qa = [
        ("What security measures protect medical data?",
         "Security measures: 1) User authentication and authorization, 2) Encrypted database connections, 3) Secure API key management, 4) CSRF protection on forms, 5) Input validation and sanitization, 6) Access control at model and view levels, 7) Secure file upload handling."),

        ("How is HIPAA compliance addressed?",
         "HIPAA considerations: 1) User consent for data processing, 2) Data encryption at rest and in transit, 3) Access logging and audit trails, 4) Data minimization principles, 5) Right to data deletion, 6) Clear medical disclaimers, 7) No storage of sensitive personal information beyond necessary medical data."),

        ("What are the compliance challenges in AI medical applications?",
         "AI compliance challenges: 1) Algorithmic bias in medical recommendations, 2) Explainability of AI decisions, 3) Data privacy in training vs inference, 4) Liability for AI-generated medical advice, 5) Regulatory approval requirements, 6) Continuous monitoring and validation of AI outputs.")
    ]

    for question, answer in security_qa:
        elements.append(Paragraph(f"Q: {question}", question_style))
        elements.append(Paragraph(f"A: {answer}", answer_style))
        elements.append(Spacer(1, 0.1*inch))

    elements.append(PageBreak())

    # Section 13: Interview Preparation
    elements.append(Paragraph("13. Interview Preparation Questions", section_style))

    interview_qa = [
        ("Explain the complete RAG pipeline in this project.",
         "The RAG pipeline: 1) Document ingestion (PDF upload), 2) Text extraction and cleaning, 3) Document chunking (RecursiveCharacterTextSplitter), 4) Embedding creation (Google Generative AI), 5) Vector storage (Pinecone with namespaces), 6) Query processing (embed question), 7) Retrieval (semantic search), 8) Context augmentation (add retrieved chunks to prompt), 9) Generation (LLM creates answer), 10) Response formatting and health data extraction."),

        ("How would you optimize RAG for medical documents?",
         "Medical RAG optimization: 1) Domain-specific embeddings trained on medical corpus, 2) Medical ontology integration for better semantic understanding, 3) Hierarchical chunking (sections, paragraphs, sentences), 4) Metadata enrichment (document type, specialty, date), 5) Hybrid search (keyword + semantic), 6) Quality filtering of retrieved chunks, 7) Medical entity recognition in retrieval."),

        ("What are the limitations of current LLM integration?",
         "LLM limitations: 1) Hallucination potential despite RAG, 2) Context window constraints, 3) Lack of real-time medical knowledge updates, 4) Inability to perform physical examinations, 5) Cultural bias in medical recommendations, 6) Dependency on training data quality, 7) Token limits affecting complex medical analysis."),

        ("How would you implement agentic AI for medical diagnosis?",
         "Agentic medical AI: 1) Multi-step reasoning with tool use (lab results, imaging, patient history), 2) Uncertainty quantification in diagnoses, 3) Integration with medical guidelines and protocols, 4) Human-in-the-loop validation for critical decisions, 5) Longitudinal patient tracking, 6) Collaboration with healthcare providers, 7) Continuous learning from outcomes."),

        ("Design a RAG system for real-time medical consultations.",
         "Real-time medical RAG: 1) Streaming ingestion of patient data, 2) Real-time vector updates, 3) Low-latency retrieval with caching, 4) Incremental context building, 5) Multi-modal input handling (text, voice, images), 6) Integration with EHR systems, 7) Privacy-preserving federated learning, 8) Emergency protocol triggers, 9) Multi-language support, 10) Offline capability for remote areas."),

        ("How do you ensure RAG answers are medically accurate?",
         "Medical accuracy in RAG: 1) Retrieval from authoritative medical sources only, 2) Confidence scoring of retrieved information, 3) Cross-referencing multiple sources, 4) Integration with medical knowledge graphs, 5) Regular validation against clinical guidelines, 6) Human expert review pipelines, 7) Bias detection and mitigation, 8) Transparency in source attribution.")
    ]

    for question, answer in interview_qa:
        elements.append(Paragraph(f"Q: {question}", question_style))
        elements.append(Paragraph(f"A: {answer}", answer_style))
        elements.append(Spacer(1, 0.1*inch))

    # Build the PDF
    doc.build(elements)
    print(f"PDF created successfully: {pdf_filename}")
    return pdf_filename

if __name__ == "__main__":
    pdf_file = create_qa_pdf()
    print(f"Generated comprehensive Q&A PDF: {pdf_file}")