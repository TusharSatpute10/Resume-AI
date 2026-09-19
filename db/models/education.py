from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


class Education(Base):
    __tablename__ = "education"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True
    )

    resume_id: Mapped[int] = mapped_column(
        ForeignKey("resumes.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    institution: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    degree: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True
    )

    field_of_study: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True
    )

    start_year: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    end_year: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    grade: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True
    )

    resume = relationship(
        "Resume",
        back_populates="education"
    )