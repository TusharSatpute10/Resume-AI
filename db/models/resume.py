from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True
    )

    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    file_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    file_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False
    )

    raw_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    total_experience_years: Mapped[float | None] = mapped_column(
        nullable=True
    )

    experience_level: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True
    )

    parse_confidence: Mapped[float | None] = mapped_column(
        nullable=True
    )

    is_primary: Mapped[bool] = mapped_column(
        default=False,
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    student = relationship(
        "Student",
        back_populates="resumes"
    )
    
    resume_skills = relationship(
        "ResumeSkill",
        back_populates="resume",
        cascade="all, delete-orphan"
    )
    
    education = relationship(
        "Education",
        back_populates="resume",
        cascade="all, delete-orphan"
    )
    
    work_experience = relationship(
        "WorkExperience",
        back_populates="resume",
        cascade="all, delete-orphan"
    )
    
    projects = relationship(
        "Project",
        back_populates="resume",
        cascade="all, delete-orphan"
    )
    
    certifications = relationship(
        "Certification",
        back_populates="resume",
        cascade="all, delete-orphan"
    )
    
    applications = relationship(
        "Application",
        back_populates="resume"
    )
    
    match_results = relationship(
        "MatchResult",
        back_populates="resume",
        cascade="all, delete-orphan"
    )