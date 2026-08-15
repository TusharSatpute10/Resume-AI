"""
agents/parser_agent.py
â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
Parser Agent â€” the first agent in the pipeline.

Responsibilities:
  1. Receive raw resume or JD text
  2. Send to Mistral with a structured prompt
  3. Parse the JSON response into Pydantic models
  4. Generate embeddings via nomic-embed-text
  5. Store in ChromaDB
"""

import json
import re
from loguru import logger
from langchain_core.prompts import PromptTemplate
from langchain_ollama import OllamaEmbeddings

from core.base_agent import BaseAgent
from schemas.models import (
    AgentMessage, AgentRole,
    ParsedResume, ParsedJobDescription,
    WorkExperience, Education, ExperienceLevel,
)
from db.chroma_client import store_resume, store_jd
from config.settings import get_settings

settings = get_settings()


# â”€â”€ Prompts â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

RESUME_PROMPT = PromptTemplate.from_template("""
Extract resume data. Return ONLY raw JSON, no explanation, no markdown.

Resume:
{text}

JSON:
{{
  "name": "",
  "email": "",
  "phone": "",
  "location": "",
  "total_experience_years": 0,
  "hard_skills": [],
  "soft_skills": [],
  "certifications": [],
  "work_experience": [{{"company":"","role":"","start_date":"","end_date":"","responsibilities":[]}}],
  "education": [{{"institution":"","degree":"","field_of_study":"","graduation_year":0}}]
}}
""")

JD_PROMPT = PromptTemplate.from_template("""
Extract job description data. Return ONLY raw JSON, no explanation, no markdown.

Job Description:
{text}

JSON:
{{
  "title": "",
  "company": "",
  "location": "",
  "required_skills": [],
  "preferred_skills": [],
  "required_experience_years": 0,
  "required_education": "",
  "responsibilities": []
}}
""")


# â”€â”€ Parser Agent â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class ParserAgent(BaseAgent):
    agent_role = AgentRole.PARSER

    def __init__(self):
        super().__init__()
        self.embeddings = OllamaEmbeddings(
            base_url=settings.ollama_base_url,
            model=settings.ollama_embedding_model,
        )
        self.resume_chain = self._build_chain(RESUME_PROMPT)
        self.jd_chain = self._build_chain(JD_PROMPT)
        self.logger.info("Parser Agent ready")

    async def execute(self, message: AgentMessage) -> dict:
        task = message.task
        text = message.payload.get("text", "")

        if not text.strip():
            raise ValueError("Empty text received â€” nothing to parse")

        if task == "parse_resume":
            return await self._parse_resume(text)
        elif task == "parse_jd":
            return await self._parse_jd(text)
        else:
            raise ValueError(f"Unknown task: {task}")

    # â”€â”€ Resume Parsing â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    async def _parse_resume(self, text: str) -> dict:
        self.logger.info("Parsing resume...")

        # Step 1: Call Mistral
        raw_response = self._safe_llm_call(self.resume_chain, {"text": text[:2000]})

        # Step 2: Extract JSON
        data = self._extract_json(raw_response)

        # Step 3: Build Pydantic model
        resume = self._build_resume(data, text)

        # Step 4: Generate embedding
        embedding = self.embeddings.embed_query(text[:2000])

        # Step 5: Store in ChromaDB
        store_resume(
            doc_id=resume.id,
            text=text[:2000],
            embedding=embedding,
            metadata={
                "name": resume.name or "unknown",
                "email": resume.email or "",
                "skills": ", ".join(resume.hard_skills[:10]),
                "experience_years": str(resume.total_experience_years or 0),
            },
        )

        self.logger.success(f"Resume parsed | name={resume.name} | skills={len(resume.hard_skills)}")
        return {"parsed_resume": resume.model_dump()}

    # â”€â”€ JD Parsing â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    async def _parse_jd(self, text: str) -> dict:
        self.logger.info("Parsing job description...")

        # Step 1: Call Mistral
        raw_response = self._safe_llm_call(self.jd_chain, {"text": text[:2000]})

        # Step 2: Extract JSON
        data = self._extract_json(raw_response)

        # Step 3: Build Pydantic model
        jd = self._build_jd(data, text)

        # Step 4: Generate embedding
        embedding = self.embeddings.embed_query(text[:2000])

        # Step 5: Store in ChromaDB
        store_jd(
            doc_id=jd.id,
            text=text[:2000],
            embedding=embedding,
            metadata={
                "title": jd.title or "unknown",
                "company": jd.company or "",
                "required_skills": ", ".join(jd.required_skills[:10]),
                "experience_years": str(jd.required_experience_years or 0),
            },
        )

        self.logger.success(f"JD parsed | title={jd.title} | skills={len(jd.required_skills)}")
        return {"parsed_jd": jd.model_dump()}

    # â”€â”€ Helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _extract_json(self, text: str) -> dict:
        """
        Safely extract JSON from Mistral's response.
        Handles cases where the model adds extra text around the JSON.
        """
        # Try direct parse first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try extracting JSON block from markdown
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        # Try finding first { ... } block
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        self.logger.warning("Could not extract JSON â€” returning empty dict")
        return {}

    def _build_resume(self, data: dict, raw_text: str) -> ParsedResume:
        """Build a ParsedResume Pydantic model from extracted data."""
        work_exp = []
        for w in data.get("work_experience", []):
            try:
                work_exp.append(WorkExperience(**{
                    k: v for k, v in w.items()
                    if k in WorkExperience.model_fields
                }))
            except Exception:
                pass

        education = []
        for e in data.get("education", []):
            try:
                education.append(Education(**{
                    k: v for k, v in e.items()
                    if k in Education.model_fields
                }))
            except Exception:
                pass

        # Estimate experience level
        years = data.get("total_experience_years", 0) or 0
        if years < 2:
            level = ExperienceLevel.ENTRY
        elif years < 5:
            level = ExperienceLevel.MID
        elif years < 10:
            level = ExperienceLevel.SENIOR
        else:
            level = ExperienceLevel.LEAD

        confidence = 0.9 if data.get("name") and data.get("hard_skills") else 0.5

        return ParsedResume(
            raw_doc_id="direct_input",
            name=data.get("name"),
            email=data.get("email"),
            phone=data.get("phone"),
            location=data.get("location"),
            summary=data.get("summary"),
            total_experience_years=years,
            experience_level=level,
            hard_skills=data.get("hard_skills", []),
            soft_skills=data.get("soft_skills", []),
            certifications=[c if isinstance(c, str) else c.get("name", str(c)) for c in data.get("certifications", [])],
            languages=data.get("languages", []),
            work_experience=work_exp,
            education=education,
            projects=data.get("projects", []),
            awards=data.get("awards", []),
            parse_confidence=confidence,
        )

    def _build_jd(self, data: dict, raw_text: str) -> ParsedJobDescription:
        """Build a ParsedJobDescription Pydantic model from extracted data."""
        years = data.get("required_experience_years", 0) or 0
        if years < 2:
            level = ExperienceLevel.ENTRY
        elif years < 5:
            level = ExperienceLevel.MID
        elif years < 10:
            level = ExperienceLevel.SENIOR
        else:
            level = ExperienceLevel.LEAD

        confidence = 0.9 if data.get("title") and data.get("required_skills") else 0.5

        return ParsedJobDescription(
            raw_doc_id="direct_input",
            title=data.get("title"),
            company=data.get("company"),
            location=data.get("location"),
            remote_policy=data.get("remote_policy"),
            employment_type=data.get("employment_type"),
            salary_range=data.get("salary_range"),
            required_skills=data.get("required_skills", []),
            preferred_skills=data.get("preferred_skills", []),
            required_experience_years=years,
            experience_level=level,
            required_education=data.get("required_education"),
            responsibilities=data.get("responsibilities", []),
            nice_to_have=data.get("nice_to_have", []),
            benefits=data.get("benefits", []),
            parse_confidence=confidence,
        )
