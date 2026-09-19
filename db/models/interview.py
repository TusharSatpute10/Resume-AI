from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


class Interview(Base):
    __tablename__ = "interviews"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True
    )

    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    scheduled_by: Mapped[int] = mapped_column(
        ForeignKey("hr_users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )

    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False
    )

    interview_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    meeting_link: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default="SCHEDULED",
        nullable=False
    )

    feedback: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    application = relationship(
        "Application",
        back_populates="interviews"
    )

    scheduled_by_user = relationship(
        "HRUser",
        back_populates="interviews"
    )