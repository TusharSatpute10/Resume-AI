from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from constants.roles import UserRole
from core.dependencies import get_current_user, require_role
from db.database import get_db
from db.models.application import Application
from db.models.company import Company
from db.models.hr_user import HRUser
from db.models.interview import Interview
from db.models.job import Job
from db.models.student import Student
from db.models.user import User
from services.email_service import send_interview_notification
from schemas.interview import (
    BulkInterviewCreate,
    InterviewActionResponse,
    InterviewCreate,
    InterviewResponse,
    InterviewUpdate,
    MeetingLinkUpdate,
)

router = APIRouter(prefix="/interviews", tags=["Interviews"])


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _get_hr_profile(user_id: int, db: Session) -> HRUser:
    hr = (
        db.query(HRUser)
        .filter(HRUser.user_id == user_id)
        .first()
    )
    if not hr:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="HR profile not found.",
        )
    return hr


def _get_hr_interview(
    interview_id: int,
    hr: HRUser,
    db: Session,
) -> Interview:
    interview = (
        db.query(Interview)
        .join(Application, Interview.application_id == Application.id)
        .join(Job, Application.job_id == Job.id)
        .filter(
            Interview.id == interview_id,
            Job.company_id == hr.company_id,
        )
        .options(
            joinedload(Interview.application)
            .joinedload(Application.student)
            .joinedload(Student.user),
            joinedload(Interview.application)
            .joinedload(Application.job)
            .joinedload(Job.company),
        )
        .first()
    )
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found.",
        )
    return interview


def _get_student_interview(
    interview_id: int,
    student: Student,
    db: Session,
) -> Interview:
    interview = (
        db.query(Interview)
        .join(Application, Interview.application_id == Application.id)
        .filter(
            Interview.id == interview_id,
            Application.student_id == student.id,
        )
        .options(
            joinedload(Interview.application)
            .joinedload(Application.student)
            .joinedload(Student.user),
            joinedload(Interview.application)
            .joinedload(Application.job)
            .joinedload(Job.company),
        )
        .first()
    )
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found.",
        )
    return interview


def _get_application_for_hr(
    application_id: int,
    hr: HRUser,
    db: Session,
) -> Application:
    application = (
        db.query(Application)
        .join(Job, Application.job_id == Job.id)
        .filter(
            Application.id == application_id,
            Job.company_id == hr.company_id,
        )
        .options(
            joinedload(Application.student).joinedload(Student.user),
            joinedload(Application.job).joinedload(Job.company),
        )
        .first()
    )
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application {application_id} not found in your company.",
        )
    if application.status not in {"SHORTLISTED", "INTERVIEW_SCHEDULED"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Only shortlisted candidates can be scheduled. "
                f"Current application status: {application.status}."
            ),
        )
    return application


def _validate_interview_location(
    interview_type: str,
    meeting_link: str | None,
    venue: str | None,
) -> None:
    if interview_type == "ONLINE" and venue:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Online interviews cannot have an offline venue.",
        )
    if interview_type == "OFFLINE" and meeting_link:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Offline interviews cannot have an online meeting link.",
        )


def _build_response(interview: Interview) -> InterviewResponse:
    application = interview.application
    student = application.student if application else None
    job = application.job if application else None
    company = job.company if job else None

    return InterviewResponse(
        id=interview.id,
        application_id=interview.application_id,
        scheduled_by=interview.scheduled_by,
        scheduled_at=interview.scheduled_at,
        duration_minutes=interview.duration_minutes,
        round_name=interview.round_name,
        interview_type=interview.interview_type,
        meeting_link=interview.meeting_link,
        meeting_link_status=interview.meeting_link_status,
        venue=interview.venue,
        instructions=interview.instructions,
        status=interview.status,
        feedback=interview.feedback,
        cancelled_at=interview.cancelled_at,
        created_at=interview.created_at,
        updated_at=interview.updated_at,
        student_name=student.full_name if student else None,
        student_email=student.user.email if student and student.user else None,
        job_title=job.title if job else None,
        company_name=company.name if company else None,
    )


def _create_interview(
    payload: InterviewCreate,
    hr: HRUser,
    db: Session,
) -> Interview:
    application = _get_application_for_hr(
        payload.application_id,
        hr,
        db,
    )

    _validate_interview_location(
        payload.interview_type,
        payload.meeting_link,
        payload.venue,
    )

    meeting_link = (
        payload.meeting_link.strip()
        if payload.meeting_link
        else None
    )

    interview = Interview(
        application_id=application.id,
        scheduled_by=hr.id,
        scheduled_at=payload.scheduled_at.replace(tzinfo=None),
        duration_minutes=payload.duration_minutes,
        round_name=payload.round_name.strip(),
        interview_type=payload.interview_type,
        meeting_link=meeting_link,
        meeting_link_status="AVAILABLE" if meeting_link else "PENDING",
        venue=payload.venue.strip() if payload.venue else None,
        instructions=payload.instructions,
        status="SCHEDULED",
    )
    db.add(interview)
    application.status = "INTERVIEW_SCHEDULED"
    return interview


@router.post(
    "",
    response_model=InterviewResponse,
    status_code=status.HTTP_201_CREATED,
)
def schedule_interview(
    payload: InterviewCreate,
    current_user: User = Depends(require_role(UserRole.HR)),
    db: Session = Depends(get_db),
):
    hr = _get_hr_profile(current_user.id, db)
    try:
        interview = _create_interview(payload, hr, db)
        db.commit()
        db.refresh(interview)
        send_interview_notification(interview, "scheduled")
        return _build_response(interview)
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not schedule interview.",
        ) from exc


@router.post(
    "/bulk",
    response_model=list[InterviewResponse],
    status_code=status.HTTP_201_CREATED,
)
def schedule_bulk_interviews(
    payload: BulkInterviewCreate,
    current_user: User = Depends(require_role(UserRole.HR)),
    db: Session = Depends(get_db),
):
    hr = _get_hr_profile(current_user.id, db)
    application_ids = [item.application_id for item in payload.interviews]
    if len(application_ids) != len(set(application_ids)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Each application can appear only once in a bulk request.",
        )

    try:
        interviews = [
            _create_interview(item, hr, db)
            for item in payload.interviews
        ]
        db.commit()

        for interview in interviews:
            db.refresh(interview)
            send_interview_notification(interview, "scheduled")

        return [_build_response(interview) for interview in interviews]
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Bulk interview scheduling failed. No interviews were saved.",
        ) from exc


@router.get(
    "/me",
    response_model=list[InterviewResponse],
)
def get_my_interviews(
    current_user: User = Depends(require_role(UserRole.STUDENT)),
    db: Session = Depends(get_db),
):
    student = (
        db.query(Student)
        .filter(Student.user_id == current_user.id)
        .first()
    )
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found.")

    interviews = (
        db.query(Interview)
        .join(Application, Interview.application_id == Application.id)
        .filter(Application.student_id == student.id)
        .options(
            joinedload(Interview.application)
            .joinedload(Application.student)
            .joinedload(Student.user),
            joinedload(Interview.application)
            .joinedload(Application.job)
            .joinedload(Job.company),
        )
        .order_by(Interview.scheduled_at.asc())
        .all()
    )
    return [_build_response(item) for item in interviews]


@router.get(
    "/hr",
    response_model=list[InterviewResponse],
)
def get_hr_interviews(
    job_id: int | None = Query(default=None, gt=0),
    interview_status: str | None = Query(default=None, alias="status"),
    current_user: User = Depends(require_role(UserRole.HR)),
    db: Session = Depends(get_db),
):
    hr = _get_hr_profile(current_user.id, db)
    query = (
        db.query(Interview)
        .join(Application, Interview.application_id == Application.id)
        .join(Job, Application.job_id == Job.id)
        .filter(Job.company_id == hr.company_id)
        .options(
            joinedload(Interview.application)
            .joinedload(Application.student)
            .joinedload(Student.user),
            joinedload(Interview.application)
            .joinedload(Application.job)
            .joinedload(Job.company),
        )
    )

    if job_id is not None:
        query = query.filter(Job.id == job_id)
    if interview_status:
        normalized_status = interview_status.strip().upper()
        if normalized_status not in {"SCHEDULED", "CANCELLED", "COMPLETED"}:
            raise HTTPException(
                status_code=422,
                detail="Invalid interview status filter.",
            )
        query = query.filter(Interview.status == normalized_status)

    interviews = query.order_by(Interview.scheduled_at.asc()).all()
    return [_build_response(item) for item in interviews]


@router.get(
    "/{interview_id}",
    response_model=InterviewResponse,
)
def get_interview(
    interview_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role == UserRole.HR:
        hr = _get_hr_profile(current_user.id, db)
        interview = _get_hr_interview(interview_id, hr, db)
    elif current_user.role == UserRole.STUDENT:
        student = (
            db.query(Student)
            .filter(Student.user_id == current_user.id)
            .first()
        )
        if not student:
            raise HTTPException(status_code=404, detail="Student profile not found.")
        interview = _get_student_interview(interview_id, student, db)
    else:
        raise HTTPException(status_code=403, detail="You cannot access interviews.")

    return _build_response(interview)


@router.patch(
    "/{interview_id}",
    response_model=InterviewResponse,
)
def update_interview(
    interview_id: int,
    payload: InterviewUpdate,
    current_user: User = Depends(require_role(UserRole.HR)),
    db: Session = Depends(get_db),
):
    hr = _get_hr_profile(current_user.id, db)
    interview = _get_hr_interview(interview_id, hr, db)

    if interview.status == "CANCELLED":
        raise HTTPException(status_code=409, detail="Cancelled interviews cannot be rescheduled.")
    if interview.status == "COMPLETED":
        raise HTTPException(status_code=409, detail="Completed interviews cannot be changed.")

    original_scheduled_at = interview.scheduled_at
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=422, detail="Provide at least one field to update.")

    new_type = changes.get("interview_type", interview.interview_type)
    new_link = changes.get("meeting_link", interview.meeting_link)
    new_venue = changes.get("venue", interview.venue)
    _validate_interview_location(new_type, new_link, new_venue)

    if "scheduled_at" in changes and changes["scheduled_at"] is not None:
        if changes["scheduled_at"] <= datetime.now(changes["scheduled_at"].tzinfo):
            raise HTTPException(
                status_code=422,
                detail="Interview must be scheduled in the future.",
            )
        interview.scheduled_at = changes["scheduled_at"].replace(tzinfo=None)

    for field in (
        "duration_minutes",
        "round_name",
        "interview_type",
        "venue",
        "instructions",
    ):
        if field in changes:
            value = changes[field]
            setattr(interview, field, value.strip() if field == "round_name" and value else value)

    if "meeting_link" in changes:
        link = changes["meeting_link"]
        interview.meeting_link = link.strip() if link else None
        interview.meeting_link_status = "AVAILABLE" if interview.meeting_link else "PENDING"

    interview.updated_at = _utc_now()

    try:
        db.commit()
        db.refresh(interview)
        if interview.scheduled_at != original_scheduled_at:
            send_interview_notification(interview, "rescheduled")
        elif "meeting_link" in changes and interview.meeting_link:
            send_interview_notification(interview, "meeting_link_added")
        return _build_response(interview)
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Could not update interview.",
        ) from exc


@router.patch(
    "/{interview_id}/meeting-link",
    response_model=InterviewResponse,
)
def update_meeting_link(
    interview_id: int,
    payload: MeetingLinkUpdate,
    current_user: User = Depends(require_role(UserRole.HR)),
    db: Session = Depends(get_db),
):
    hr = _get_hr_profile(current_user.id, db)
    interview = _get_hr_interview(interview_id, hr, db)

    if interview.status != "SCHEDULED":
        raise HTTPException(
            status_code=409,
            detail="Meeting links can only be updated for scheduled interviews.",
        )
    if interview.interview_type != "ONLINE":
        raise HTTPException(
            status_code=409,
            detail="Meeting links are only valid for online interviews.",
        )

    interview.meeting_link = payload.meeting_link.strip()
    interview.meeting_link_status = "AVAILABLE"
    interview.updated_at = _utc_now()

    try:
        db.commit()
        db.refresh(interview)
        send_interview_notification(interview, "meeting_link_added")
        return _build_response(interview)
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Could not update meeting link.",
        ) from exc


@router.patch(
    "/{interview_id}/cancel",
    response_model=InterviewActionResponse,
)
def cancel_interview(
    interview_id: int,
    current_user: User = Depends(require_role(UserRole.HR)),
    db: Session = Depends(get_db),
):
    hr = _get_hr_profile(current_user.id, db)
    interview = _get_hr_interview(interview_id, hr, db)

    if interview.status == "CANCELLED":
        raise HTTPException(status_code=409, detail="Interview is already cancelled.")
    if interview.status == "COMPLETED":
        raise HTTPException(status_code=409, detail="Completed interviews cannot be cancelled.")

    interview.status = "CANCELLED"
    interview.cancelled_at = _utc_now()
    interview.updated_at = _utc_now()

    try:
        db.commit()
        db.refresh(interview)
        send_interview_notification(interview, "cancelled")
        return InterviewActionResponse(
            message="Interview cancelled successfully.",
            interview=_build_response(interview),
        )
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Could not cancel interview.",
        ) from exc


@router.patch(
    "/{interview_id}/complete",
    response_model=InterviewResponse,
)
def complete_interview(
    interview_id: int,
    current_user: User = Depends(require_role(UserRole.HR)),
    db: Session = Depends(get_db),
):
    hr = _get_hr_profile(current_user.id, db)
    interview = _get_hr_interview(interview_id, hr, db)

    if interview.status != "SCHEDULED":
        raise HTTPException(
            status_code=409,
            detail="Only scheduled interviews can be marked completed.",
        )

    interview.status = "COMPLETED"
    interview.updated_at = _utc_now()

    try:
        db.commit()
        db.refresh(interview)
        return _build_response(interview)
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Could not complete interview.",
        ) from exc
