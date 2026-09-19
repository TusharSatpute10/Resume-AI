from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


class Application(Base):
    __tablename__ = "applications"

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

    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    resume_id: Mapped[int] = mapped_column(
        ForeignKey("resumes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default="APPLIED",
        nullable=False
    )

    applied_at: Mapped[datetime] = mapped_column(
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
        back_populates="applications"
    )

    job = relationship(
        "Job",
        back_populates="applications"
    )

    resume = relationship(
        "Resume",
        back_populates="applications"
    )
    
    shortlist = relationship(
        "Shortlist",
        back_populates="application",
        uselist=False,
        cascade="all, delete-orphan"
    )
    
    interviews = relationship(
        "Interview",
        back_populates="application",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint(
            "student_id",
            "job_id",
            name="uq_application_student_job"
        ),
    )