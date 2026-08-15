"""
schemas/models.py
─────────────────
Pydantic v2 schemas — the shared data contract for every agent.

Hierarchy:
  Raw Document → ParsedResume / ParsedJobDescription
               → CandidateProfile / JobProfile (enriched)
               → ScreeningResult / RecommendationResult
               → AgentMessage (inter-agent communication)
"""

from __future__ import annotations
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime
from enum import Enum
import uuid


# ═══════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════

class ExperienceLevel(str, Enum):
    ENTRY      = "entry"        # 0–2 years
    MID        = "mid"          # 2–5 years
    SENIOR     = "senior"       # 5–10 years
    LEAD       = "lead"         # 10+ years / team lead
    EXECUTIVE  = "executive"    # C-level / VP


class DocumentType(str, Enum):
    RESUME = "resume"
    JOB_DESCRIPTION = "job_description"


class AgentRole(str, Enum):
    ORCHESTRATOR  = "orchestrator"
    PARSER        = "parser"
    SCREENER      = "screener"
    RECOMMENDER   = "recommender"


class AgentStatus(str, Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    SUCCESS   = "success"
    FAILED    = "failed"
    RETRYING  = "retrying"


# ═══════════════════════════════════════════════════════════════════
# RAW INPUT
# ═══════════════════════════════════════════════════════════════════

class RawDocument(BaseModel):
    """Represents an unprocessed uploaded document."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    content: str                            # extracted plain text
    doc_type: DocumentType
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Document content cannot be empty")
        return v.strip()


# ═══════════════════════════════════════════════════════════════════
# WORK EXPERIENCE
# ═══════════════════════════════════════════════════════════════════

class WorkExperience(BaseModel):
    """A single job entry from a resume."""
    company: str
    role: str
    start_date: Optional[str] = None        # e.g. "Jan 2021"
    end_date: Optional[str] = None          # "Present" or "Dec 2023"
    duration_months: Optional[int] = None   # computed or extracted
    responsibilities: list[str] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list)
    tech_used: list[str] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════
# EDUCATION
# ═══════════════════════════════════════════════════════════════════

class Education(BaseModel):
    institution: str
    degree: Optional[str] = None            # e.g. "B.Tech", "MBA"
    field_of_study: Optional[str] = None    # e.g. "Computer Science"
    graduation_year: Optional[int] = None
    gpa: Optional[float] = None


# ═══════════════════════════════════════════════════════════════════
# PARSED RESUME  (output of Parser Agent)
# ═══════════════════════════════════════════════════════════════════

class ParsedResume(BaseModel):
    """
    Structured data extracted from a raw resume.
    The Parser Agent fills this from unstructured text.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    raw_doc_id: str                                 # links back to RawDocument

    # ── Personal Info ─────────────────────────────────────────────
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None

    # ── Professional Summary ───────────────────────────────────────
    summary: Optional[str] = None
    total_experience_years: Optional[float] = None
    experience_level: Optional[ExperienceLevel] = None

    # ── Skills ────────────────────────────────────────────────────
    hard_skills: list[str] = Field(default_factory=list)   # Python, React, SQL…
    soft_skills: list[str] = Field(default_factory=list)   # Leadership, Communication…
    certifications: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)

    # ── Experience & Education ────────────────────────────────────
    work_experience: list[WorkExperience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)

    # ── Extras ────────────────────────────────────────────────────
    projects: list[str] = Field(default_factory=list)
    awards: list[str] = Field(default_factory=list)

    parsed_at: datetime = Field(default_factory=datetime.utcnow)
    parse_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    parse_warnings: list[str] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════
# PARSED JOB DESCRIPTION  (output of Parser Agent)
# ═══════════════════════════════════════════════════════════════════

class ParsedJobDescription(BaseModel):
    """
    Structured data extracted from a raw job description.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    raw_doc_id: str

    # ── Job Info ──────────────────────────────────────────────────
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    remote_policy: Optional[str] = None     # "Remote" | "Hybrid" | "On-site"
    employment_type: Optional[str] = None   # "Full-time" | "Contract" | "Part-time"
    salary_range: Optional[str] = None      # e.g. "$80k–$110k"
    department: Optional[str] = None

    # ── Requirements ──────────────────────────────────────────────
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    required_experience_years: Optional[float] = None
    experience_level: Optional[ExperienceLevel] = None
    required_education: Optional[str] = None

    # ── Role Details ──────────────────────────────────────────────
    responsibilities: list[str] = Field(default_factory=list)
    nice_to_have: list[str] = Field(default_factory=list)
    benefits: list[str] = Field(default_factory=list)

    parsed_at: datetime = Field(default_factory=datetime.utcnow)
    parse_confidence: float = Field(default=0.0, ge=0.0, le=1.0)


# ═══════════════════════════════════════════════════════════════════
# SCREENING RESULT  (output of Screener Agent)
# ═══════════════════════════════════════════════════════════════════

class SkillMatchDetail(BaseModel):
    """Breakdown of individual skill matches."""
    matched: list[str] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)
    bonus: list[str] = Field(default_factory=list)   # preferred skills candidate has


class ScoreBreakdown(BaseModel):
    skills_score: float = Field(ge=0.0, le=100.0)       # 40% weight
    experience_score: float = Field(ge=0.0, le=100.0)   # 30% weight
    education_score: float = Field(ge=0.0, le=100.0)    # 15% weight
    signals_score: float = Field(ge=0.0, le=100.0)      # 15% weight
    total_score: float = Field(ge=0.0, le=100.0)


class ScreeningResult(BaseModel):
    """Per-candidate result from Screener Agent."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    resume_id: str
    jd_id: str
    candidate_name: Optional[str] = None

    score_breakdown: ScoreBreakdown
    skill_match: SkillMatchDetail
    summary: str                            # LLM-generated explanation
    recommendation: str                     # "Strong Hire" | "Consider" | "Pass"
    red_flags: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)

    screened_at: datetime = Field(default_factory=datetime.utcnow)


class ShortlistReport(BaseModel):
    """Full output of the Screener Agent for a given JD."""
    jd_id: str
    jd_title: Optional[str] = None
    total_candidates_evaluated: int
    results: list[ScreeningResult]          # sorted by score desc
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ═══════════════════════════════════════════════════════════════════
# RECOMMENDATION RESULT  (output of Recommender Agent)
# ═══════════════════════════════════════════════════════════════════

class JobMatch(BaseModel):
    """A single job match for a candidate."""
    jd_id: str
    job_title: Optional[str] = None
    company: Optional[str] = None
    match_score: float = Field(ge=0.0, le=100.0)
    match_reason: str                       # LLM-generated explanation
    skill_gaps: list[str] = Field(default_factory=list)
    apply_priority: str                     # "High" | "Medium" | "Low"


class RecommendationResult(BaseModel):
    """Full recommendation output for one candidate."""
    resume_id: str
    candidate_name: Optional[str] = None
    job_matches: list[JobMatch]             # sorted by match_score desc
    career_insight: Optional[str] = None   # LLM-generated career advice
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ═══════════════════════════════════════════════════════════════════
# AGENT MESSAGE  (inter-agent communication)
# ═══════════════════════════════════════════════════════════════════

class AgentMessage(BaseModel):
    """
    Standard envelope passed between agents.
    The Orchestrator wraps every task in this format.
    """
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    from_agent: AgentRole
    to_agent: AgentRole
    status: AgentStatus = AgentStatus.PENDING
    task: str                               # e.g. "parse_resume", "screen_candidates"
    payload: dict = Field(default_factory=dict)     # flexible task-specific data
    result: Optional[dict] = None
    error: Optional[str] = None
    retries: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None


# ═══════════════════════════════════════════════════════════════════
# API REQUEST / RESPONSE WRAPPERS
# ═══════════════════════════════════════════════════════════════════

class ScreenRequest(BaseModel):
    """Recruiter sends this to screen candidates against a JD."""
    jd_text: str = Field(..., description="Raw job description text")
    resume_texts: list[str] = Field(..., description="List of raw resume texts")
    top_n: int = Field(default=10, ge=1, le=50)


class RecommendRequest(BaseModel):
    """Candidate sends this to get job recommendations."""
    resume_text: str = Field(..., description="Raw resume text")
    career_goals: Optional[str] = Field(None, description="Optional career goals paragraph")
    top_n: int = Field(default=5, ge=1, le=20)


class APIResponse(BaseModel):
    """Standard API response envelope."""
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
