from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


class ResumeSkill(Base):
    __tablename__ = "resume_skills"

    resume_id: Mapped[int] = mapped_column(
        ForeignKey("resumes.id", ondelete="CASCADE"),
        primary_key=True
    )

    skill_id: Mapped[int] = mapped_column(
        ForeignKey("skills.id", ondelete="CASCADE"),
        primary_key=True
    )

    proficiency: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True
    )

    years_experience: Mapped[float | None] = mapped_column(
        Float,
        nullable=True
    )

    source: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True
    )

    resume = relationship(
        "Resume",
        back_populates="resume_skills"
    )

    skill = relationship(
        "Skill",
        back_populates="resume_skills"
    )