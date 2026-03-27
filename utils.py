import logging
import os
import tempfile
import zipfile
from pathlib import Path

from PyPDF2 import PdfReader
from docx import Document

logger = logging.getLogger(__name__)


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from a PDF file."""
    try:
        reader = PdfReader(pdf_path)
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(pages).strip()
    except Exception as e:
        raise Exception(f"Error extracting text from PDF {pdf_path}: {e}")


def extract_text_from_docx(docx_path: str) -> str:
    """Extract text from a DOCX file."""
    try:
        doc = Document(docx_path)
        return "\n".join(p.text for p in doc.paragraphs).strip()
    except Exception as e:
        raise Exception(f"Error extracting text from DOCX {docx_path}: {e}")


def extract_text_from_txt(txt_path: str) -> str:
    """Extract text from a TXT file."""
    try:
        with open(txt_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read().strip()
    except Exception as e:
        raise Exception(f"Error extracting text from TXT {txt_path}: {e}")


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


def extract_resumes_from_zip(zip_path: str, temp_dir: str) -> dict[str, str]:
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
        raise Exception(f"Error extracting ZIP file: {e}")


def process_resume_files(files: list, temp_dir: str = None) -> dict[str, str]:
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


def extract_all_resume_texts(resumes: dict[str, str]) -> dict[str, str]:
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
            logger.warning("Could not extract text from %s: %s", filename, e)
    
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


# Common short stopwords to ignore when comparing texts
_STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "that", "this", "these",
    "those", "it", "its", "into", "as", "up", "if", "then", "than",
    "so", "not", "no", "also", "any", "all", "more", "other",
}


def _meaningful_words(text: str) -> set[str]:
    """Lowercase word tokens, 3+ chars, stripped of stopwords."""
    return {
        w for w in text.lower().split()
        if len(w) >= 3 and w not in _STOPWORDS
    }


def infer_job_category_from_resumes(
    job_circular: str,
    predictions: dict[str, dict],
    resume_texts: dict[str, str],
) -> str | None:
    """
    Dynamically infer which category best matches this job circular.

    Bias-correction: if one category captures >50% of all predictions
    (i.e. it acts as a catch-all due to an undertrained model), resumes
    assigned to that dominant category are re-bucketed using their
    second-best predicted category. This prevents the catch-all from
    absorbing all vocabulary and always winning inference.

    Scoring: instead of union-vocabulary overlap (biased toward large corpora),
    uses the average per-resume relevance score within each category group,
    so 5 highly-relevant resumes can beat 100 loosely-relevant ones.
    """
    if not job_circular or not predictions or not resume_texts:
        return None

    total = len(predictions)

    # --- Step 1: Detect the dominant catch-all category (if any) ---
    cat_counts: dict[str, int] = {}
    for pred in predictions.values():
        c = pred.get("predicted_category", "")
        if c:
            cat_counts[c] = cat_counts.get(c, 0) + 1

    dominant_cat: str | None = None
    for cat, count in cat_counts.items():
        if count / total > 0.5:          # majority → probable catch-all
            dominant_cat = cat
            logger.debug(
                "Dominant catch-all category detected: '%s' (%d/%d = %.0f%%)",
                cat, count, total, 100 * count / total,
            )
            break

    # --- Step 2: Build category → [resume_texts] corpus ---
    # Resumes classified as the dominant catch-all are re-bucketed using
    # their SECOND-best predicted probability instead.
    job_words = _meaningful_words(job_circular)
    if not job_words:
        return None

    category_corpus: dict[str, list[str]] = {}
    for filename, pred in predictions.items():
        text = resume_texts.get(filename, "")
        if not text:
            continue

        top_cat = pred.get("predicted_category", "")
        all_preds: dict[str, float] = pred.get("all_predictions", {})

        if top_cat == dominant_cat and len(all_preds) > 1:
            # Sort by probability descending, skip the dominant category
            sorted_preds = sorted(all_preds.items(), key=lambda x: x[1], reverse=True)
            effective_cat = next(
                (c for c, _ in sorted_preds if c != dominant_cat),
                top_cat,   # fallback: keep original if nothing else exists
            )
        else:
            effective_cat = top_cat

        category_corpus.setdefault(effective_cat, []).append(text)

    if not category_corpus:
        return None

    # --- Step 3: Score each category by AVERAGE per-resume relevance ---
    # Average relevance = (sum of per-resume word-overlaps) / num_resumes
    # This avoids the large-corpus bias of vocabulary-union overlap.
    best_cat: str | None = None
    best_score: float = 0.0

    for cat, texts in category_corpus.items():
        if not texts:
            continue
        total_overlap = sum(
            len(job_words & _meaningful_words(t)) / len(job_words) for t in texts
        )
        avg_score = total_overlap / len(texts)

        logger.debug(
            "Inference score — '%s': %d resumes, avg_relevance=%.4f",
            cat, len(texts), avg_score,
        )

        if avg_score > best_score:
            best_score = avg_score
            best_cat = cat

    return best_cat if best_score > 0.0 else None


def calculate_job_relevance(resume_text: str, job_circular: str) -> float:
    """
    Calculate keyword-overlap relevance between a resume and a job circular.
    Returns a score between 0.0 and 1.0.
    """
    job_words = _meaningful_words(job_circular)
    resume_words = _meaningful_words(resume_text)
    if not job_words:
        return 0.0
    overlap = job_words & resume_words
    return len(overlap) / len(job_words)
