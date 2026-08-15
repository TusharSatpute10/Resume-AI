"""
agents/screener_agent.py
─────────────────────────
Screener Agent — scores and ranks candidates against a job description.

Scoring rubric:
  - Skills match      40%
  - Experience        30%
  - Education         15%
  - Soft signals      15%
"""

import json
import re
from loguru import logger
from langchain_core.prompts import PromptTemplate

from core.base_agent import BaseAgent
from schemas.models import (
    AgentMessage, AgentRole,
    ScreeningResult, ShortlistReport,
    ScoreBreakdown, SkillMatchDetail,
)
from config.settings import get_settings

settings = get_settings()


# ── Prompt ────────────────────────────────────────────────────────

SCREEN_PROMPT = PromptTemplate.from_template("""
You are an expert technical recruiter. Evaluate this candidate against the job description.
Return ONLY a valid JSON object, no explanation or markdown.

JOB DESCRIPTION:
Title: {jd_title}
Required Skills: {required_skills}
Preferred Skills: {preferred_skills}
Required Experience: {required_years} years
Required Education: {required_education}
Responsibilities: {responsibilities}

CANDIDATE:
Name: {candidate_name}
Skills: {candidate_skills}
Experience: {candidate_experience} years
Education: {candidate_education}
Work History: {work_history}

Score the candidate and return this exact JSON:
{{
  "skills_score": 0,
  "experience_score": 0,
  "education_score": 0,
  "signals_score": 0,
  "matched_skills": [],
  "missing_skills": [],
  "bonus_skills": [],
  "strengths": [],
  "red_flags": [],
  "summary": "",
  "recommendation": ""
}}

Rules:
- All scores are 0-100
- recommendation must be exactly one of: "Strong Hire", "Consider", "Pass"
- summary should be 2-3 sentences explaining the decision
- matched_skills: required skills the candidate HAS
- missing_skills: required skills the candidate LACKS
- bonus_skills: preferred skills the candidate has
- strengths: list of 2-3 candidate strengths
- red_flags: list of concerns (empty list if none)
""")


class ScreenerAgent(BaseAgent):
    agent_role = AgentRole.SCREENER

    def __init__(self):
        super().__init__()
        self.screen_chain = self._build_chain(SCREEN_PROMPT)
        self.logger.info("Screener Agent ready")

    async def execute(self, message: AgentMessage) -> dict:
        parsed_jd = message.payload.get("parsed_jd", {})
        parsed_resumes = message.payload.get("parsed_resumes", [])
        top_n = message.payload.get("top_n", 10)

        if not parsed_resumes:
            raise ValueError("No resumes provided for screening")

        self.logger.info(f"Screening {len(parsed_resumes)} candidates for: {parsed_jd.get('title', 'Unknown')}")

        # Score each candidate
        results = []
        for i, resume in enumerate(parsed_resumes):
            self.logger.debug(f"Scoring candidate {i+1}/{len(parsed_resumes)}: {resume.get('name', 'Unknown')}")
            try:
                result = await self._score_candidate(resume, parsed_jd)
                results.append(result)
            except Exception as e:
                self.logger.warning(f"Failed to score candidate {resume.get('name', 'Unknown')}: {e}")

        # Sort by total score descending
        results.sort(key=lambda r: r.score_breakdown.total_score, reverse=True)

        # Take top N
        results = results[:top_n]

        report = ShortlistReport(
            jd_id=parsed_jd.get("id", "unknown"),
            jd_title=parsed_jd.get("title"),
            total_candidates_evaluated=len(parsed_resumes),
            results=results,
        )

        self.logger.success(f"Screening complete | ranked={len(results)} | top_score={results[0].score_breakdown.total_score:.1f}")
        return {"report": report.model_dump()}

    async def _score_candidate(self, resume: dict, jd: dict) -> ScreeningResult:
        """Score a single candidate against the JD using Mistral."""

        # Prepare work history summary
        work_history = []
        for w in resume.get("work_experience", [])[:3]:
            work_history.append(f"{w.get('role')} at {w.get('company')} ({w.get('start_date')} - {w.get('end_date', 'Present')})")

        # Prepare education summary
        edu_list = []
        for e in resume.get("education", [])[:2]:
            edu_list.append(f"{e.get('degree')} in {e.get('field_of_study')} from {e.get('institution')}")

        # Call Mistral
        raw_response = self._safe_llm_call(self.screen_chain, {
            "jd_title": jd.get("title", "Unknown"),
            "required_skills": ", ".join(jd.get("required_skills", [])),
            "preferred_skills": ", ".join(jd.get("preferred_skills", [])),
            "required_years": jd.get("required_experience_years", 0),
            "required_education": jd.get("required_education", "Not specified"),
            "responsibilities": ", ".join(jd.get("responsibilities", [])[:5]),
            "candidate_name": resume.get("name", "Unknown"),
            "candidate_skills": ", ".join(resume.get("hard_skills", [])),
            "candidate_experience": resume.get("total_experience_years", 0),
            "candidate_education": "; ".join(edu_list) if edu_list else "Not specified",
            "work_history": "; ".join(work_history) if work_history else "Not specified",
        })

        # Parse response
        data = self._extract_json(raw_response)

        # Calculate weighted total score
        skills_score = float(data.get("skills_score", 0))
        experience_score = float(data.get("experience_score", 0))
        education_score = float(data.get("education_score", 0))
        signals_score = float(data.get("signals_score", 0))

        total_score = (
            skills_score * 0.40 +
            experience_score * 0.30 +
            education_score * 0.15 +
            signals_score * 0.15
        )

        return ScreeningResult(
            resume_id=resume.get("id", "unknown"),
            jd_id=jd.get("id", "unknown"),
            candidate_name=resume.get("name"),
            score_breakdown=ScoreBreakdown(
                skills_score=skills_score,
                experience_score=experience_score,
                education_score=education_score,
                signals_score=signals_score,
                total_score=round(total_score, 1),
            ),
            skill_match=SkillMatchDetail(
                matched=data.get("matched_skills", []),
                missing=data.get("missing_skills", []),
                bonus=data.get("bonus_skills", []),
            ),
            summary=data.get("summary", ""),
            recommendation=data.get("recommendation", "Consider"),
            strengths=data.get("strengths", []),
            red_flags=data.get("red_flags", []),
        )

    def _extract_json(self, text: str) -> dict:
        """Extract JSON from Mistral response."""
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        self.logger.warning("Could not extract JSON from screener response")
        return {}