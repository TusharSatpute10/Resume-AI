from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


class JobSkill(Base):
    __tablename__ = "job_skills"

    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"),
        primary_key=True
    )

    skill_id: Mapped[int] = mapped_column(
        ForeignKey("skills.id", ondelete="CASCADE"),
        primary_key=True
    )

    requirement_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )

    minimum_years: Mapped[float | None] = mapped_column(
        Float,
        nullable=True
    )

    importance_weight: Mapped[float | None] = mapped_column(
        Float,
        nullable=True
    )

    job = relationship(
        "Job",
        back_populates="job_skills"
    )

    skill = relationship(
        "Skill",
        back_populates="job_skills"
    )