import os
import zipfile
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple

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
        # Save uploaded file to temp directory
        temp_path = os.path.join(temp_dir, file.filename)
        with open(temp_path, 'wb') as f:
            f.write(file.file.read())
        
        ext = Path(file.filename).suffix.lower()
        
        # If it's a ZIP, extract contents
        if ext == '.zip':
            extracted = extract_resumes_from_zip(temp_path, temp_dir)
            resumes.update(extracted)
        elif ext in ['.pdf', '.docx', '.txt']:
            resumes[file.filename] = temp_path
        else:
            raise ValueError(f"Unsupported file format: {file.filename}")
    
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


def calculate_skill_bonus(resume_text: str, skills: List[str], 
                         min_experience: int = 0) -> float:
    """
    Calculate bonus score based on skills and experience found in resume.
    
    Args:
        resume_text: The resume text
        skills: List of required/desired skills
        min_experience: Minimum years of experience required
    
    Returns:
        Bonus score (0.0 to 1.0)
    """
    bonus = 0.0
    resume_lower = resume_text.lower()
    
    # Check for each skill
    if skills:
        skills_found = 0
        for skill in skills:
            if skill.lower() in resume_lower:
                skills_found += 1
        
        # Award bonus for skills found (max 0.5)
        if len(skills) > 0:
            bonus += (skills_found / len(skills)) * 0.5
    
    # Check for years of experience
    if min_experience > 0:
        # Simple heuristic: look for common experience phrases
        experience_indicators = (
            [
                f"{min_experience}+ years",
                f"{min_experience} years",
            ] + [f"{min_experience + i} years" for i in range(1, 20)]
        )
        
        for indicator in experience_indicators:
            if indicator.lower() in resume_lower:
                bonus += 0.3  # Award 0.3 bonus if experience found
                break
    
    return min(bonus, 1.0)  # Cap at 1.0
