from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True
    )

    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True
    )

    category: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    resume_skills = relationship(
        "ResumeSkill",
        back_populates="skill",
        cascade="all, delete-orphan"
    )
    
    job_skills = relationship(
        "JobSkill",
        back_populates="skill",
        cascade="all, delete-orphan"
    )