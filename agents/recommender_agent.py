"""
agents/recommender_agent.py
────────────────────────────
Recommender Agent — matches a candidate to the best job openings.

How it works:
  1. Takes a parsed resume
  2. Searches stored JDs using embedding similarity
  3. Re-ranks using Mistral for deep matching
  4. Returns ranked job matches with explanations
"""

import json
import re
from loguru import logger
from langchain_core.prompts import PromptTemplate
from langchain_ollama import OllamaEmbeddings

from core.base_agent import BaseAgent
from schemas.models import (
    AgentMessage, AgentRole,
    RecommendationResult, JobMatch,
)
from db.chroma_client import search_jds
from config.settings import get_settings

settings = get_settings()


# ── Prompt ────────────────────────────────────────────────────────

RECOMMEND_PROMPT = PromptTemplate.from_template("""
You are a career advisor. Evaluate how well this job matches the candidate.
Return ONLY a valid JSON object, no explanation or markdown.

CANDIDATE PROFILE:
Name: {candidate_name}
Skills: {candidate_skills}
Experience: {candidate_experience} years
Education: {candidate_education}
Career Goals: {career_goals}

JOB OPPORTUNITY:
Title: {job_title}
Company: {job_company}
Required Skills: {required_skills}
Required Experience: {required_years} years
Responsibilities: {responsibilities}

Return this exact JSON:
{{
  "match_score": 0,
  "match_reason": "",
  "skill_gaps": [],
  "apply_priority": ""
}}

Rules:
- match_score is 0-100
- match_reason is 2 sentences explaining the match
- skill_gaps is a list of skills the candidate should learn for this role
- apply_priority must be exactly one of: "High", "Medium", "Low"
""")

INSIGHT_PROMPT = PromptTemplate.from_template("""
You are a career advisor. Based on this candidate's profile, give them 2-3 sentences of career advice.
Be specific, practical, and encouraging.

Candidate: {candidate_name}
Skills: {candidate_skills}
Experience: {candidate_experience} years
Top Job Match: {top_job}

Return only the advice text, no JSON, no bullet points.
""")


class RecommenderAgent(BaseAgent):
    agent_role = AgentRole.RECOMMENDER

    def __init__(self):
        super().__init__()
        self.recommend_chain = self._build_chain(RECOMMEND_PROMPT)
        self.insight_chain = self._build_chain(INSIGHT_PROMPT)
        self.embeddings = OllamaEmbeddings(
            base_url=settings.ollama_base_url,
            model=settings.ollama_embedding_model,
        )
        self.logger.info("Recommender Agent ready")

    async def execute(self, message: AgentMessage) -> dict:
        resume = message.payload.get("parsed_resume", {})
        career_goals = message.payload.get("career_goals", "Not specified")
        top_n = message.payload.get("top_n", 5)

        if not resume:
            raise ValueError("No resume provided for recommendation")

        candidate_name = resume.get("name", "Candidate")
        self.logger.info(f"Finding jobs for: {candidate_name}")

        # Step 1: Get candidate embedding
        resume_text = self._build_resume_text(resume)
        query_embedding = self.embeddings.embed_query(resume_text[:2000])

        # Step 2: Search stored JDs by similarity
        similar_jds = search_jds(query_embedding, top_k=top_n * 2)

        if not similar_jds:
            self.logger.warning("No JDs in database yet — returning empty recommendations")
            return {
                "recommendation": RecommendationResult(
                    resume_id=resume.get("id", "unknown"),
                    candidate_name=candidate_name,
                    job_matches=[],
                    career_insight="No job listings available yet. Ask a recruiter to add job descriptions to the system.",
                ).model_dump()
            }

        # Step 3: Re-rank each JD using Mistral
        job_matches = []
        for jd_result in similar_jds[:top_n]:
            try:
                match = await self._evaluate_match(resume, jd_result, career_goals)
                job_matches.append(match)
            except Exception as e:
                self.logger.warning(f"Failed to evaluate job match: {e}")

        # Sort by match score
        job_matches.sort(key=lambda m: m.match_score, reverse=True)

        # Step 4: Generate career insight
        career_insight = ""
        if job_matches:
            try:
                career_insight = self._safe_llm_call(self.insight_chain, {
                    "candidate_name": candidate_name,
                    "candidate_skills": ", ".join(resume.get("hard_skills", [])[:10]),
                    "candidate_experience": resume.get("total_experience_years", 0),
                    "top_job": job_matches[0].job_title or "the top matched role",
                })
            except Exception as e:
                self.logger.warning(f"Career insight generation failed: {e}")

        result = RecommendationResult(
            resume_id=resume.get("id", "unknown"),
            candidate_name=candidate_name,
            job_matches=job_matches,
            career_insight=career_insight,
        )

        self.logger.success(f"Recommendations ready | matches={len(job_matches)} | top_score={job_matches[0].match_score if job_matches else 0}")
        return {"recommendation": result.model_dump()}

    async def _evaluate_match(self, resume: dict, jd_result: dict, career_goals: str) -> JobMatch:
        """Evaluate a single job match using Mistral."""
        metadata = jd_result.get("metadata", {})

        # Education summary
        edu_list = []
        for e in resume.get("education", [])[:1]:
            edu_list.append(f"{e.get('degree')} in {e.get('field_of_study')}")

        raw_response = self._safe_llm_call(self.recommend_chain, {
            "candidate_name": resume.get("name", "Candidate"),
            "candidate_skills": ", ".join(resume.get("hard_skills", [])[:10]),
            "candidate_experience": resume.get("total_experience_years", 0),
            "candidate_education": "; ".join(edu_list) if edu_list else "Not specified",
            "career_goals": career_goals or "Not specified",
            "job_title": metadata.get("title", "Unknown"),
            "job_company": metadata.get("company", "Unknown"),
            "required_skills": metadata.get("required_skills", ""),
            "required_years": metadata.get("experience_years", 0),
            "responsibilities": jd_result.get("document", "")[:300],
        })

        data = self._extract_json(raw_response)

        return JobMatch(
            jd_id=jd_result.get("id", "unknown"),
            job_title=metadata.get("title"),
            company=metadata.get("company"),
            match_score=float(data.get("match_score", 0)),
            match_reason=data.get("match_reason", ""),
            skill_gaps=data.get("skill_gaps", []),
            apply_priority=data.get("apply_priority", "Medium"),
        )

    def _build_resume_text(self, resume: dict) -> str:
        """Build a searchable text summary from a parsed resume."""
        parts = []
        if resume.get("name"):
            parts.append(resume["name"])
        if resume.get("hard_skills"):
            parts.append("Skills: " + ", ".join(resume["hard_skills"]))
        if resume.get("total_experience_years"):
            parts.append(f"Experience: {resume['total_experience_years']} years")
        for w in resume.get("work_experience", [])[:2]:
            parts.append(f"{w.get('role')} at {w.get('company')}")
        return "\n".join(parts)

    def _extract_json(self, text: str) -> dict:
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
        return {}