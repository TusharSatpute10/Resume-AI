"""
agents/orchestrator.py
───────────────────────
The Orchestrator is the top-level controller.

Responsibilities:
  1. Receive user intent (screen OR recommend)
  2. Build an AgentMessage for the appropriate agent chain
  3. Route: Parser → Screener  OR  Parser → Recommender
  4. Collect and return final results

Pattern: ReAct-style (Reason → Act → Observe → Repeat if needed)
"""

from loguru import logger
from schemas.models import (
    AgentMessage, AgentRole, AgentStatus,
    ScreenRequest, RecommendRequest,
    ShortlistReport, RecommendationResult,
)
from datetime import datetime
import uuid


class Orchestrator:
    """
    Stateless orchestrator — creates agents lazily on first use.
    Import and instantiate once in your FastAPI app lifespan.
    """

    def __init__(self):
        # Lazy imports to avoid circular deps and slow startup
        self._parser = None
        self._screener = None
        self._recommender = None
        self.logger = logger.bind(agent="Orchestrator")
        self.logger.info("Orchestrator initialized")

    # ── Lazy agent loading ────────────────────────────────────────

    @property
    def parser(self):
        if self._parser is None:
            from agents.parser_agent import ParserAgent
            self._parser = ParserAgent()
        return self._parser

    @property
    def screener(self):
        if self._screener is None:
            from agents.screener_agent import ScreenerAgent
            self._screener = ScreenerAgent()
        return self._screener

    @property
    def recommender(self):
        if self._recommender is None:
            from agents.recommender_agent import RecommenderAgent
            self._recommender = RecommenderAgent()
        return self._recommender

    # ── Main Flows ────────────────────────────────────────────────

    async def screen_candidates(self, request: ScreenRequest) -> ShortlistReport:
        """
        Flow: Parse JD → Parse each Resume → Screen → Return ShortlistReport

        Steps:
          1. Parse the JD
          2. Parse all resumes (can be parallelized in Phase 5)
          3. Run Screener Agent against JD
          4. Return ranked ShortlistReport
        """
        session_id = str(uuid.uuid4())[:8]
        self.logger.info(f"[{session_id}] START screen_candidates | resumes={len(request.resume_texts)}")

        # ── Step 1: Parse JD ──────────────────────────────────────
        jd_msg = self._make_message(
            from_agent=AgentRole.ORCHESTRATOR,
            to_agent=AgentRole.PARSER,
            task="parse_jd",
            payload={"text": request.jd_text},
        )
        jd_msg = await self.parser.run(jd_msg)
        self._assert_success(jd_msg, "JD parsing")
        parsed_jd = jd_msg.result["parsed_jd"]

        self.logger.info(f"[{session_id}] JD parsed | title={parsed_jd.get('title', 'Unknown')}")

        # ── Step 2: Parse all Resumes ─────────────────────────────
        parsed_resumes = []
        for i, resume_text in enumerate(request.resume_texts):
            resume_msg = self._make_message(
                from_agent=AgentRole.ORCHESTRATOR,
                to_agent=AgentRole.PARSER,
                task="parse_resume",
                payload={"text": resume_text, "index": i},
            )
            resume_msg = await self.parser.run(resume_msg)
            if resume_msg.status == AgentStatus.SUCCESS:
                parsed_resumes.append(resume_msg.result["parsed_resume"])
                self.logger.debug(f"[{session_id}] Resume {i+1}/{len(request.resume_texts)} parsed")
            else:
                self.logger.warning(f"[{session_id}] Resume {i+1} parse failed — skipping")

        if not parsed_resumes:
            raise RuntimeError("All resumes failed to parse")

        # ── Step 3: Screen ────────────────────────────────────────
        screen_msg = self._make_message(
            from_agent=AgentRole.ORCHESTRATOR,
            to_agent=AgentRole.SCREENER,
            task="screen_candidates",
            payload={
                "parsed_jd": parsed_jd,
                "parsed_resumes": parsed_resumes,
                "top_n": request.top_n,
            },
        )
        screen_msg = await self.screener.run(screen_msg)
        self._assert_success(screen_msg, "Screening")

        report = ShortlistReport(**screen_msg.result["report"])
        self.logger.success(f"[{session_id}] Screening done | candidates_ranked={len(report.results)}")
        return report

    async def recommend_jobs(self, request: RecommendRequest) -> RecommendationResult:
        """
        Flow: Parse Resume → Recommend Jobs → Return RecommendationResult

        Steps:
          1. Parse the resume
          2. Run Recommender Agent
          3. Return ranked job matches
        """
        session_id = str(uuid.uuid4())[:8]
        self.logger.info(f"[{session_id}] START recommend_jobs")

        # ── Step 1: Parse Resume ──────────────────────────────────
        resume_msg = self._make_message(
            from_agent=AgentRole.ORCHESTRATOR,
            to_agent=AgentRole.PARSER,
            task="parse_resume",
            payload={"text": request.resume_text},
        )
        resume_msg = await self.parser.run(resume_msg)
        self._assert_success(resume_msg, "Resume parsing")
        parsed_resume = resume_msg.result["parsed_resume"]

        # ── Step 2: Recommend ─────────────────────────────────────
        rec_msg = self._make_message(
            from_agent=AgentRole.ORCHESTRATOR,
            to_agent=AgentRole.RECOMMENDER,
            task="recommend_jobs",
            payload={
                "parsed_resume": parsed_resume,
                "career_goals": request.career_goals,
                "top_n": request.top_n,
            },
        )
        rec_msg = await self.recommender.run(rec_msg)
        self._assert_success(rec_msg, "Recommendation")

        result = RecommendationResult(**rec_msg.result["recommendation"])
        self.logger.success(f"[{session_id}] Recommendations done | matches={len(result.job_matches)}")
        return result

    # ── Helpers ───────────────────────────────────────────────────

    def _make_message(
        self,
        from_agent: AgentRole,
        to_agent: AgentRole,
        task: str,
        payload: dict,
    ) -> AgentMessage:
        return AgentMessage(
            from_agent=from_agent,
            to_agent=to_agent,
            task=task,
            payload=payload,
            status=AgentStatus.PENDING,
        )

    def _assert_success(self, message: AgentMessage, stage: str):
        if message.status != AgentStatus.SUCCESS:
            raise RuntimeError(
                f"{stage} failed after {message.retries} retries: {message.error}"
            )
