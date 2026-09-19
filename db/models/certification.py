from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


class Certification(Base):
    __tablename__ = "certifications"

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

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    issuer: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    issue_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True
    )

    credential_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True
    )

    resume = relationship(
        "Resume",
        back_populates="certifications"
    )