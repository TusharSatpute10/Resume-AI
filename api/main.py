"""
api/main.py
───────────
FastAPI application — updated with PDF upload + NLP pipeline.
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from loguru import logger
import httpx
import sys
from typing import Optional
from api.students import router as students_router
from api.resumes import router as resumes_router
from api.hr import router as hr_router
from api.companies import router as companies_router
from api.jobs import router as jobs_router
from api.job_skills import router as job_skills_router
from api.applications import router as applications_router
from api.matching import router as matching_router
from api.skills import router as skills_router
from api.interviews import router as interviews_router

from config.settings import get_settings
from schemas.models import (
    ScreenRequest, RecommendRequest, APIResponse
)
from agents.orchestrator import Orchestrator
from api.auth import router as auth_router

settings = get_settings()

logger.remove()
logger.add(
    sys.stdout,
    level=settings.log_level,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{extra[agent]}</cyan> | {message}",
)
logger.add("logs/app.log", rotation="10 MB", level="DEBUG", serialize=True)

orchestrator: Orchestrator = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global orchestrator
    logger.bind(agent="App").info(f"Starting {settings.app_name}...")
    orchestrator = Orchestrator()
    yield
    logger.bind(agent="App").info("Shutting down...")


app = FastAPI(
    title="ResumeAI",
    description="Agentic AI system with NLP + KNN screening",
    version="0.2.0",
    lifespan=lifespan,
)

app.include_router(auth_router)
app.include_router(students_router)
app.include_router(resumes_router)
app.include_router(hr_router)
app.include_router(companies_router)
app.include_router(jobs_router)
app.include_router(job_skills_router)
app.include_router(applications_router)
app.include_router(matching_router)
app.include_router(skills_router)
app.include_router(interviews_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════════════
# HEALTH
# ═══════════════════════════════════════════════════════════════════

@app.get("/health", tags=["System"])
async def health_check():
    ollama_status = "unknown"
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{settings.ollama_base_url}/api/tags", timeout=5)
            ollama_status = "connected" if r.status_code == 200 else "error"
    except Exception:
        ollama_status = "unreachable"
    return {
        "status": "ok",
        "app": settings.app_name,
        "env": settings.app_env,
        "ollama": ollama_status,
        "model": settings.ollama_model,
    }


# ═══════════════════════════════════════════════════════════════════
# PARSE ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.post("/parse/resume", tags=["Parse"], response_model=APIResponse)
async def parse_resume(request: RecommendRequest):
    from schemas.models import AgentMessage, AgentRole, AgentStatus
    try:
        msg = AgentMessage(
            from_agent=AgentRole.ORCHESTRATOR,
            to_agent=AgentRole.PARSER,
            task="parse_resume",
            payload={"text": request.resume_text},
        )
        result = await orchestrator.parser.run(msg)
        if result.status != AgentStatus.SUCCESS:
            raise HTTPException(status_code=500, detail=result.error)
        return APIResponse(success=True, data=result.result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/parse/jd", tags=["Parse"], response_model=APIResponse)
async def parse_jd(request: RecommendRequest):
    from schemas.models import AgentMessage, AgentRole, AgentStatus
    try:
        msg = AgentMessage(
            from_agent=AgentRole.ORCHESTRATOR,
            to_agent=AgentRole.PARSER,
            task="parse_jd",
            payload={"text": request.resume_text},
        )
        result = await orchestrator.parser.run(msg)
        if result.status != AgentStatus.SUCCESS:
            raise HTTPException(status_code=500, detail=result.error)
        return APIResponse(success=True, data=result.result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════
# PDF UPLOAD ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.post("/upload/resume", tags=["Upload"], response_model=APIResponse)
async def upload_resume(file: UploadFile = File(...)):
    """Upload a PDF/DOCX resume — extracts text using fast parser."""
    from parsers.pdf_parser import extract_from_upload
    from utils.fast_parser import fast_parse_resume
    try:
        file_bytes = await file.read()
        text = extract_from_upload(file.filename, file_bytes)
        if not text.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from file")

        parsed = fast_parse_resume(text)

        return APIResponse(success=True, data={
            "parsed_resume": parsed,
            "filename": file.filename,
            "extracted_chars": len(text),
            "extracted_text": text,
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload/jd", tags=["Upload"], response_model=APIResponse)
async def upload_jd(file: UploadFile = File(...)):
    """Upload a PDF/DOCX job description."""
    from parsers.pdf_parser import extract_from_upload
    from schemas.models import AgentMessage, AgentRole, AgentStatus
    try:
        file_bytes = await file.read()
        text = extract_from_upload(file.filename, file_bytes)

        msg = AgentMessage(
            from_agent=AgentRole.ORCHESTRATOR,
            to_agent=AgentRole.PARSER,
            task="parse_jd",
            payload={"text": text},
        )
        result = await orchestrator.parser.run(msg)
        if result.status != AgentStatus.SUCCESS:
            raise HTTPException(status_code=500, detail=result.error)

        return APIResponse(success=True, data={
            **result.result,
            "filename": file.filename,
            "extracted_chars": len(text),
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/nlp/screen/files", tags=["NLP"])
async def nlp_screen_files(
    jd_text: str = Form(...),
    files: list[UploadFile] = File(...),
    top_n: int = Form(10)
):
    """Screen resumes uploaded as PDF files directly - no LLM parsing."""
    from parsers.pdf_parser import extract_from_upload
    from utils.nlp_pipeline import nlp_pipeline
    from utils.fast_parser import fast_parse_resume, fast_parse_jd
    from langchain_core.prompts import PromptTemplate
    from langchain_ollama import OllamaLLM

    try:
        # Extract text from all PDFs instantly
        resume_texts = []
        for f in files:
            file_bytes = await f.read()
            text = extract_from_upload(f.filename, file_bytes)
            if text.strip():
                resume_texts.append(text)

        if not resume_texts:
            raise HTTPException(status_code=400, detail="No text extracted from files")

        # Fast parse + NLP rank + LLM top 3
        parsed_jd = fast_parse_jd(jd_text)
        parsed_resumes = [fast_parse_resume(t) for t in resume_texts]
        candidate_names = [p.get("name", f"Candidate {i+1}") for i, p in enumerate(parsed_resumes)]

        nlp_rankings = nlp_pipeline.rank_candidates(
            jd_text=jd_text,
            resume_texts=resume_texts,
            candidate_names=candidate_names,
        )

        EXPLAIN_PROMPT = PromptTemplate.from_template("""You are a recruiter. In 2-3 sentences explain why this candidate is a {recommendation} for this role. Be specific and concise.
Job: {job_title}
Required Skills: {required_skills}
Candidate: {candidate_name}
Their Skills: {candidate_skills}
Experience: {experience_years} years
Matched: {matched_skills}
Missing: {missing_skills}
Write only the explanation.""")

        llm = OllamaLLM(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            temperature=0.1, timeout=60,
            num_predict=300, num_ctx=1024, num_thread=10
        )
        explain_chain = EXPLAIN_PROMPT | llm

        results = []
        for i, nlp_result in enumerate(nlp_rankings[:top_n]):
            idx = nlp_result["resume_index"]
            parsed = parsed_resumes[idx]
            score = nlp_result["nlp_score"]
            recommendation = "Strong Hire" if score >= 65 else "Consider" if score >= 40 else "Pass"

            explanation = ""
            if i < 3:
                try:
                    explanation = explain_chain.invoke({
                        "job_title": parsed_jd.get("title", "this role"),
                        "required_skills": ", ".join(parsed_jd.get("required_skills", [])[:8]),
                        "candidate_name": nlp_result["name"],
                        "candidate_skills": ", ".join(parsed.get("hard_skills", [])[:10]),
                        "experience_years": parsed.get("total_experience_years", 0),
                        "nlp_score": score,
                        "matched_skills": ", ".join(nlp_result["matched_skills"][:8]),
                        "missing_skills": ", ".join(nlp_result["missing_skills"][:5]),
                        "recommendation": recommendation,
                    }).strip()
                except:
                    explanation = f"NLP Score: {score}/100. Matched {len(nlp_result['matched_skills'])} skills."

            results.append({
                "rank": nlp_result["rank"],
                "candidate_name": nlp_result["name"],
                "nlp_score": nlp_result["nlp_score"],
                "cosine_similarity": nlp_result["cosine_similarity"],
                "skill_match_score": nlp_result["skill_match_score"],
                "matched_skills": nlp_result["matched_skills"],
                "missing_skills": nlp_result["missing_skills"],
                "bonus_skills": nlp_result["bonus_skills"],
                "experience_years": parsed.get("total_experience_years", 0),
                "experience_level": parsed.get("experience_level", "unknown"),
                "recommendation": recommendation,
                "explanation": explanation,
                "has_llm_explanation": i < 3,
            })

        return APIResponse(success=True, data={
            "jd_title": parsed_jd.get("title", "Unknown"),
            "total_candidates": len(resume_texts),
            "method": "Fast Parse + TF-IDF + KNN + LLM Top-3",
            "results": results,
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ═══════════════════════════════════════════════════════════════════
# NLP SCREENING ENDPOINT
# ═══════════════════════════════════════════════════════════════════

@app.post("/nlp/screen", tags=["NLP"], response_model=APIResponse)
async def nlp_screen(request: ScreenRequest):
    """
    Hybrid screening:
    1. Fast parse all resumes (regex + spaCy) — instant
    2. NLP rank all candidates (TF-IDF + KNN) — instant  
    3. LLM explains top 3 only (Mistral) — ~45 sec
    """
    try:
        from utils.nlp_pipeline import nlp_pipeline
        from utils.fast_parser import fast_parse_resume, fast_parse_jd
        from langchain_core.prompts import PromptTemplate
        from langchain_ollama import OllamaLLM

        # ── Step 1: Fast parse everything ─────────────────────────
        logger.bind(agent="NLP").info("Step 1: Fast parsing...")
        parsed_jd = fast_parse_jd(request.jd_text)

        parsed_resumes = []
        resume_texts = []
        candidate_names = []

        for resume_text in request.resume_texts:
            parsed = fast_parse_resume(resume_text)
            parsed_resumes.append(parsed)
            resume_texts.append(resume_text)
            candidate_names.append(parsed.get("name", f"Candidate {len(parsed_resumes)}"))

        # ── Step 2: NLP ranking ────────────────────────────────────
        logger.bind(agent="NLP").info("Step 2: NLP ranking...")
        nlp_rankings = nlp_pipeline.rank_candidates(
            jd_text=request.jd_text,
            resume_texts=resume_texts,
            candidate_names=candidate_names,
        )

        # ── Step 3: LLM explains top 3 only ───────────────────────
        logger.bind(agent="NLP").info("Step 3: LLM explaining top 3...")

        EXPLAIN_PROMPT = PromptTemplate.from_template("""
You are a technical recruiter. In 2-3 sentences, explain why this candidate is a {recommendation} for this role.
Be specific about their strengths and gaps. Be concise.

Job: {job_title}
Required Skills: {required_skills}

Candidate: {candidate_name}
Skills: {candidate_skills}
Experience: {experience_years} years
NLP Match Score: {nlp_score}/100
Matched Skills: {matched_skills}
Missing Skills: {missing_skills}

Write only the explanation, no JSON, no bullet points.
""")

        llm = OllamaLLM(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            temperature=0.1,
            timeout=60,
        )
        explain_chain = EXPLAIN_PROMPT | llm

        # Build results
        results = []
        for i, nlp_result in enumerate(nlp_rankings[:request.top_n]):
            idx = nlp_result["resume_index"]
            parsed = parsed_resumes[idx]

            # Recommendation label based on NLP score
            score = nlp_result["nlp_score"]
            if score >= 65:
                recommendation = "Strong Hire"
            elif score >= 40:
                recommendation = "Consider"
            else:
                recommendation = "Pass"

            # LLM explanation for top 3 only
            explanation = ""
            if i < 3:
                try:
                    explanation = explain_chain.invoke({
                        "job_title": parsed_jd.get("title", "this role"),
                        "required_skills": ", ".join(parsed_jd.get("required_skills", [])[:8]),
                        "candidate_name": nlp_result["name"],
                        "candidate_skills": ", ".join(parsed.get("hard_skills", [])[:10]),
                        "experience_years": parsed.get("total_experience_years", 0),
                        "nlp_score": nlp_result["nlp_score"],
                        "matched_skills": ", ".join(nlp_result["matched_skills"][:8]),
                        "missing_skills": ", ".join(nlp_result["missing_skills"][:5]),
                        "recommendation": recommendation,
                    }).strip()
                except Exception as e:
                    logger.bind(agent="NLP").warning(f"LLM explanation failed: {e}")
                    explanation = f"NLP Score: {score}/100. Matched {len(nlp_result['matched_skills'])} required skills."

            results.append({
                "rank": nlp_result["rank"],
                "candidate_name": nlp_result["name"],
                "nlp_score": nlp_result["nlp_score"],
                "cosine_similarity": nlp_result["cosine_similarity"],
                "skill_match_score": nlp_result["skill_match_score"],
                "matched_skills": nlp_result["matched_skills"],
                "missing_skills": nlp_result["missing_skills"],
                "bonus_skills": nlp_result["bonus_skills"],
                "experience_years": parsed.get("total_experience_years", 0),
                "experience_level": parsed.get("experience_level", "unknown"),
                "recommendation": recommendation,
                "explanation": explanation,
                "has_llm_explanation": i < 3,
            })

        return APIResponse(success=True, data={
            "jd_title": parsed_jd.get("title", "Unknown"),
            "total_candidates": len(parsed_resumes),
            "method": "Fast Parse + TF-IDF + KNN + LLM Top-3",
            "results": results,
        })

    except Exception as e:
        logger.bind(agent="API").error(f"NLP screening error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════
# CORE ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.post("/screen", tags=["Core"], response_model=APIResponse)
async def screen_candidates(request: ScreenRequest):
    try:
        report = await orchestrator.screen_candidates(request)
        return APIResponse(success=True, data=report.model_dump())
    except Exception as e:
        logger.bind(agent="API").error(f"Screening error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/recommend", tags=["Core"], response_model=APIResponse)
async def recommend_jobs(request: RecommendRequest):
    try:
        result = await orchestrator.recommend_jobs(request)
        return APIResponse(success=True, data=result.model_dump())
    except Exception as e:
        logger.bind(agent="API").error(f"Recommendation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/extract/text", tags=["Upload"])
async def extract_text(file: UploadFile = File(...)):
    """Extract raw text from PDF/DOCX without LLM parsing."""
    from parsers.pdf_parser import extract_from_upload
    try:
        file_bytes = await file.read()
        text = extract_from_upload(file.filename, file_bytes)
        return APIResponse(success=True, data={
            "text": text,
            "filename": file.filename,
            "chars": len(text)
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
    )
    
    