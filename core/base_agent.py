"""
core/base_agent.py
──────────────────
Abstract base class every agent inherits from.
"""

from abc import ABC, abstractmethod
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential, before_log, after_log
import logging

from langchain_ollama import OllamaLLM
from langchain_core.output_parsers import StrOutputParser

from config.settings import get_settings
from schemas.models import AgentMessage, AgentRole, AgentStatus
from datetime import datetime

settings = get_settings()


class BaseAgent(ABC):
    agent_role: AgentRole

    def __init__(self):
        self.settings = get_settings()
        self.llm = self._init_llm()
        self.logger = logger.bind(agent=self.__class__.__name__)
        self.logger.info(f"Agent initialized | model={self.settings.ollama_model}")

    def _init_llm(self) -> OllamaLLM:
        return OllamaLLM(
            base_url=self.settings.ollama_base_url,
            model=self.settings.ollama_model,
            temperature=0.1,
            timeout=self.settings.agent_timeout_seconds,
            num_predict=600,
            num_ctx=2048,
            num_thread=10,
            top_k=10,
            top_p=0.5,
            repeat_penalty=1.1,
        )

    def _build_chain(self, prompt_template):
        return prompt_template | self.llm | StrOutputParser()

    async def run(self, message: AgentMessage) -> AgentMessage:
        message.status = AgentStatus.RUNNING
        self.logger.info(f"Starting task | task={message.task} | msg_id={message.message_id}")
        try:
            result = await self._execute_with_retry(message)
            message.result = result
            message.status = AgentStatus.SUCCESS
            message.completed_at = datetime.utcnow()
            self.logger.success(f"Task complete | task={message.task}")
        except Exception as e:
            message.status = AgentStatus.FAILED
            message.error = str(e)
            message.completed_at = datetime.utcnow()
            self.logger.error(f"Task failed | task={message.task} | error={e}")
        return message

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        before=before_log(logger, logging.DEBUG),
        after=after_log(logger, logging.DEBUG),
        reraise=True,
    )
    async def _execute_with_retry(self, message: AgentMessage) -> dict:
        message.retries += 1
        if message.retries > 1:
            message.status = AgentStatus.RETRYING
            self.logger.warning(f"Retrying | attempt={message.retries}")
        return await self.execute(message)

    @abstractmethod
    async def execute(self, message: AgentMessage) -> dict: ...

    def _safe_llm_call(self, chain, inputs: dict) -> str:
        try:
            response = chain.invoke(inputs)
            if not response or not response.strip():
                raise ValueError("LLM returned empty response")
            return response.strip()
        except Exception as e:
            self.logger.error(f"LLM call failed: {e}")
            raise

    def _parse_list_from_text(self, text: str) -> list[str]:
        import re
        cleaned = re.sub(r"^[\s\-\*\•\d\.]+", "", text, flags=re.MULTILINE)
        lines = [l.strip() for l in cleaned.split("\n") if l.strip()]
        if not lines:
            lines = [l.strip() for l in text.split(",") if l.strip()]
        return lines

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} role={self.agent_role} model={self.settings.ollama_model}>"