from fastapi import FastAPI, UploadFile, Form, File
from fastapi.responses import JSONResponse
from sentence_transformers import SentenceTransformer, util
import torch
from typing import List, Optional
import os
import tempfile
import shutil

from utils import (
    process_resume_files,
    extract_all_resume_texts,
    calculate_skill_bonus
)

# Initialize FastAPI app
app = FastAPI(title="Resume Ranker API", version="1.0.0")

# Load the embedding model (all-MiniLM-L6-v2)
print("Loading sentence transformer model...")
model = SentenceTransformer('all-MiniLM-L6-v2')
print("Model loaded successfully!")

# Store for cleanup
temp_dirs = []


@app.post("/rank_resumes")
async def rank_resumes(
    job_circular: str = Form(..., description="Job description text"),
    resume_files: List[UploadFile] = File(..., description="Resume files (PDF, DOCX, TXT, or ZIP)"),
    top_k: int = Form(5, description="Number of top candidates to return"),
    skills: Optional[str] = Form(None, description="Comma-separated list of skills"),
    min_experience: Optional[int] = Form(0, description="Minimum years of experience")
):
    """
    Rank resumes based on similarity to job circular.
    
    Parameters:
    - job_circular: Job description text
    - resume_files: List of resume files (ZIP or individual files)
    - top_k: Number of top candidates to return
    - skills: Optional comma-separated skills for bonus scoring
    - min_experience: Optional minimum years of experience
    
    Returns:
    - Ranked list of resumes with scores
    """
    temp_dir = None
    
    try:
        # Create temporary directory for file processing
        temp_dir = tempfile.mkdtemp()
        temp_dirs.append(temp_dir)
        
        # Parse skills if provided
        skills_list = []
        if skills:
            skills_list = [s.strip() for s in skills.split(',') if s.strip()]
        
        # Process uploaded files
        print("Processing resume files...")
        resumes = process_resume_files(resume_files, temp_dir)
        print(f"Found {len(resumes)} resume files")
        
        # Extract text from all resumes
        print("Extracting text from resumes...")
        resume_texts = extract_all_resume_texts(resumes)
        print(f"Successfully extracted text from {len(resume_texts)} resumes")
        
        if not resume_texts:
            return JSONResponse(
                status_code=400,
                content={"error": "Could not extract text from any resume files"}
            )
        
        # Compute embeddings for job circular and resumes
        print("Computing embeddings...")
        job_embedding = model.encode(job_circular, convert_to_tensor=True)
        
        # Compute similarity scores
        results = []
        
        for filename, resume_text in resume_texts.items():
            resume_embedding = model.encode(resume_text, convert_to_tensor=True)
            
            # Compute cosine similarity
            similarity_score = util.pytorch_cos_sim(job_embedding, resume_embedding).item()
            
            # Add skill/experience bonus if provided
            bonus_score = 0.0
            if skills_list or min_experience > 0:
                bonus_score = calculate_skill_bonus(resume_text, skills_list, min_experience)
            
            # Final score: weighted combination
            final_score = (similarity_score * 0.8) + (bonus_score * 0.2)
            
            results.append({
                "filename": filename,
                "similarity_score": round(similarity_score, 4),
                "bonus_score": round(bonus_score, 4),
                "final_score": round(final_score, 4)
            })
        
        # Sort by final score and return top_k
        results.sort(key=lambda x: x["final_score"], reverse=True)
        top_results = results[:top_k]
        
        return {
            "total_resumes": len(resume_texts),
            "top_k": top_k,
            "job_circular_preview": job_circular[:200] + "..." if len(job_circular) > 200 else job_circular,
            "skills_searched": skills_list if skills_list else None,
            "min_experience_searched": min_experience if min_experience > 0 else None,
            "ranked_resumes": top_results
        }
    
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"error": f"Validation error: {str(e)}"}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Internal server error: {str(e)}"}
        )
    finally:
        # Cleanup temporary directory
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "model": "all-MiniLM-L6-v2",
        "message": "Resume Ranker API is running"
    }


@app.get("/")
def root():
    """Root endpoint with API info."""
    return {
        "name": "Resume Ranker API",
        "version": "1.0.0",
        "endpoints": {
            "POST /rank_resumes": "Rank resumes based on job circular",
            "GET /health": "Health check",
            "GET /": "API info"
        },
        "supported_formats": ["PDF", "DOCX", "TXT", "ZIP"],
        "model": "all-MiniLM-L6-v2"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
