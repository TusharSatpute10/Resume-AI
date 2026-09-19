from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


class HRUser(Base):
    __tablename__ = "hr_users"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    full_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    designation: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    user = relationship(
        "User",
        back_populates="hr_user",
    )

    company = relationship(
        "Company",
        back_populates="hr_users",
    )

    jobs = relationship(
        "Job",
        back_populates="created_by_user",
    )
    
    shortlists = relationship(
        "Shortlist",
        back_populates="shortlisted_by_user"
    )
    
    interviews = relationship(
        "Interview",
        back_populates="scheduled_by_user"
    )