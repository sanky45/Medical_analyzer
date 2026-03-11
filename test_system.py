#!/usr/bin/env python
"""
Quick test script to verify PDF text extraction and medical analysis works
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'medical_analyzer.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from analyzer.utils import extract_text_from_pdf, analyze_with_llm

def test_pdf_extraction():
    """Test PDF text extraction"""
    print("Testing PDF text extraction...")
    
    # Check if we have a test PDF (create a simple one for testing)
    test_pdf_path = os.path.join(os.path.dirname(__file__), 'test_report.pdf')
    
    if not os.path.exists(test_pdf_path):
        print("⚠️  No test PDF found. Creating one...")
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        c = canvas.Canvas(test_pdf_path, pagesize=letter)
        c.setFont("Helvetica", 12)
        c.drawString(100, 750, "MEDICAL TEST REPORT")
        c.drawString(100, 700, "Patient: John Doe")
        c.drawString(100, 650, "Date: 2026-03-04")
        c.drawString(100, 600, "")
        c.drawString(100, 550, "BLOOD TEST RESULTS:")
        c.drawString(100, 500, "- Hemoglobin: 14.5 g/dL (Normal)")
        c.drawString(100, 450, "- White Blood Cell Count: 7.2 K/uL (Normal)")
        c.drawString(100, 400, "- Glucose: 95 mg/dL (Normal)")
        c.drawString(100, 350, "- Cholesterol: 180 mg/dL (Normal)")
        c.drawString(100, 300, "")
        c.drawString(100, 250, "DIAGNOSIS: All values within normal range.")
        c.save()
        print(f"✅ Test PDF created at {test_pdf_path}")
    
    # Test extraction
    try:
        text = extract_text_from_pdf(test_pdf_path)
        if text.strip():
            print("✅ PDF text extraction successful!")
            print(f"Extracted {len(text)} characters")
            print(f"First 200 chars: {text[:200]}...")
            return True
        else:
            print("❌ PDF text extraction returned empty")
            return False
    except Exception as e:
        print(f"❌ PDF extraction failed: {e}")
        return False

def test_llm_analysis():
    """Test LLM analysis"""
    print("\nTesting LLM analysis...")
    
    test_prompt = "Analyze these health parameters: Hemoglobin 14.5 g/dL, White Blood Cells 7.2 K/uL, Glucose 95 mg/dL"
    
    try:
        answer_html, health_data = analyze_with_llm(test_prompt, retriever=None, context="")
        if answer_html:
            print("✅ LLM analysis successful!")
            print(f"Response length: {len(answer_html)} characters")
            print(f"Extracted health data: {health_data}")
            return True
        else:
            print("❌ LLM returned empty response")
            return False
    except Exception as e:
        print(f"⚠️  LLM analysis error (may need API keys): {e}")
        return False

if __name__ == '__main__':
    print("="*60)
    print("Medical Analyzer - System Test")
    print("="*60)
    
    test1 = test_pdf_extraction()
    test2 = test_llm_analysis()
    
    print("\n" + "="*60)
    if test1:
        print("✅ PDF processing is working!")
    else:
        print("❌ PDF processing has issues")
    
    if test2:
        print("✅ LLM analysis is available!")
    else:
        print("⚠️  LLM analysis requires API keys to be configured")
    
    print("="*60)
