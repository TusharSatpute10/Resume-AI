from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True
    )

    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    created_by: Mapped[int] = mapped_column(
        ForeignKey("hr_users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    location: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True
    )

    remote_policy: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True
    )

    employment_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True
    )

    salary_min: Mapped[float | None] = mapped_column(
        Float,
        nullable=True
    )

    salary_max: Mapped[float | None] = mapped_column(
        Float,
        nullable=True
    )

    required_experience_years: Mapped[float | None] = mapped_column(
        Float,
        nullable=True
    )

    experience_level: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True
    )

    required_education: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default="DRAFT",
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
    
    openings: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False
    )

    company = relationship(
        "Company",
        back_populates="jobs"
    )

    created_by_user = relationship(
        "HRUser",
        back_populates="jobs"
    )

    job_skills = relationship(
        "JobSkill",
        back_populates="job",
        cascade="all, delete-orphan"
    )
    
    applications = relationship(
        "Application",
        back_populates="job",
        cascade="all, delete-orphan"
    )
    
    match_results = relationship(
        "MatchResult",
        back_populates="job",
        cascade="all, delete-orphan"
    )