from datetime import datetime

from sqlalchemy import (
    DateTime, Float, ForeignKey, Integer, JSON,
    String, Text, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


class MatchResult(Base):
    __tablename__ = "match_results"

    __table_args__ = (
    UniqueConstraint(
        "job_id",
        "resume_id",
        name="uq_match_results_job_resume",
    ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True
    )

    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    resume_id: Mapped[int] = mapped_column(
        ForeignKey("resumes.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    semantic_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True
    )

    skill_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True
    )

    experience_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True
    )

    education_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True
    )

    project_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True
    )

    final_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True
    )

    rank: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    matched_skills: Mapped[list | None] = mapped_column(
        JSON,
        nullable=True
    )

    missing_skills: Mapped[list | None] = mapped_column(
        JSON,
        nullable=True
    )

    explanation: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    model_version: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    job = relationship(
        "Job",
        back_populates="match_results"
    )

    resume = relationship(
        "Resume",
        back_populates="match_results"
    )