import os
import zipfile
import tempfile
from pathlib import Path
from typing import Dict, List

from PyPDF2 import PdfReader
from docx import Document


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from a PDF file."""
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        return text.strip()
    except Exception as e:
        raise Exception(f"Error extracting text from PDF {pdf_path}: {str(e)}")


def extract_text_from_docx(docx_path: str) -> str:
    """Extract text from a DOCX file."""
    try:
        doc = Document(docx_path)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text.strip()
    except Exception as e:
        raise Exception(f"Error extracting text from DOCX {docx_path}: {str(e)}")


def extract_text_from_txt(txt_path: str) -> str:
    """Extract text from a TXT file."""
    try:
        with open(txt_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read().strip()
    except Exception as e:
        raise Exception(f"Error extracting text from TXT {txt_path}: {str(e)}")


def extract_text_from_file(file_path: str) -> str:
    """Route to appropriate extraction function based on file extension."""
    ext = Path(file_path).suffix.lower()
    
    if ext == '.pdf':
        return extract_text_from_pdf(file_path)
    elif ext == '.docx':
        return extract_text_from_docx(file_path)
    elif ext == '.txt':
        return extract_text_from_txt(file_path)
    else:
        raise ValueError(f"Unsupported file format: {ext}")


def extract_resumes_from_zip(zip_path: str, temp_dir: str) -> Dict[str, str]:
    """
    Extract all resumes from a ZIP file.
    Returns dict: {filename: file_path}
    """
    resumes = {}
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        # Walk through extracted files
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                ext = Path(file).suffix.lower()
                if ext in ['.pdf', '.docx', '.txt']:
                    file_path = os.path.join(root, file)
                    resumes[file] = file_path
        
        return resumes
    except Exception as e:
        raise Exception(f"Error extracting ZIP file: {str(e)}")


def process_resume_files(files: List, temp_dir: str = None) -> Dict[str, str]:
    """
    Process multiple resume files (can be mixed types: PDF, DOCX, TXT).
    Returns dict: {filename: file_path}
    """
    resumes = {}
    if temp_dir is None:
        temp_dir = tempfile.mkdtemp()
    
    for file in files:
        filename = os.path.basename(file.name)
        temp_path = os.path.join(temp_dir, filename)
        with open(temp_path, 'wb') as f:
            f.write(file.read())
        
        ext = Path(filename).suffix.lower()
        
        # If it's a ZIP, extract contents
        if ext == '.zip':
            extracted = extract_resumes_from_zip(temp_path, temp_dir)
            resumes.update(extracted)
        elif ext in ['.pdf', '.docx', '.txt']:
            resumes[filename] = temp_path
        else:
            raise ValueError(f"Unsupported file format: {filename}")
    
    return resumes


def extract_all_resume_texts(resumes: Dict[str, str]) -> Dict[str, str]:
    """
    Extract text from all resume files.
    Returns dict: {filename: extracted_text}
    """
    resume_texts = {}
    for filename, file_path in resumes.items():
        try:
            text = extract_text_from_file(file_path)
            resume_texts[filename] = text
        except Exception as e:
            print(f"Warning: Could not extract text from {filename}: {str(e)}")
    
    return resume_texts


def calculate_skill_bonus(resume_text: str, skills: list, min_experience: int = 0) -> float:
    """
    Calculate bonus score based on skills and experience found in resume.
    Returns a score between 0.0 and 1.0.
    """
    bonus = 0.0
    resume_lower = resume_text.lower()

    if skills:
        found = sum(1 for s in skills if s.lower() in resume_lower)
        bonus += (found / len(skills)) * 0.5

    if min_experience > 0:
        for yrs in range(min_experience, min_experience + 20):
            if f"{yrs} years" in resume_lower or f"{yrs}+ years" in resume_lower:
                bonus += 0.3
                break

    return min(bonus, 1.0)


def calculate_job_relevance(resume_text: str, job_circular: str) -> float:
    """
    Calculate keyword-overlap relevance between a resume and a job circular.
    Returns a score between 0.0 and 1.0.
    """
    job_words = set(job_circular.lower().split())
    resume_words = set(resume_text.lower().split())
    if not job_words:
        return 0.0
    overlap = job_words & resume_words
    return len(overlap) / len(job_words)
