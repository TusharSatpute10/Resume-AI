from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


class Shortlist(Base):
    __tablename__ = "shortlists"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True
    )

    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )

    shortlisted_by: Mapped[int] = mapped_column(
        ForeignKey("hr_users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )

    ai_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True
    )

    hr_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    application = relationship(
        "Application",
        back_populates="shortlist"
    )

    shortlisted_by_user = relationship(
        "HRUser",
        back_populates="shortlists"
    )