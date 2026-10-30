from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload
from pathlib import Path

from db.database import get_db
from db.models.application import Application
from db.models.job import Job
from db.models.resume import Resume
from db.models.student import Student
from db.models.hr_user import HRUser
from db.models.user import User

from core.dependencies import get_current_user, require_role
from constants.roles import UserRole

from schemas.application import (
    ApplicationCreate,
    ApplicationResponse,
    ApplicationStatusUpdate,
    ApplicantResponse,
)

router = APIRouter(
    prefix="/applications",
    tags=["Applications"],
)

ALLOWED_STATUSES = {
    "APPLIED",
    "UNDER_REVIEW",
    "SHORTLISTED",
    "INTERVIEW_SCHEDULED",
    "REJECTED",
    "HIRED",
}


def get_student_profile(user_id: int, db: Session) -> Student:
    student = (
        db.query(Student)
        .filter(Student.user_id == user_id)
        .first()
    )

    if not student:
        raise HTTPException(
            status_code=404,
            detail="Student profile not found.",
        )

    return student


def get_application_for_student(
    application_id: int,
    student_id: int,
    db: Session,
) -> Application:
    application = (
        db.query(Application)
        .filter(
            Application.id == application_id,
            Application.student_id == student_id,
        )
        .first()
    )

    if not application:
        raise HTTPException(
            status_code=404,
            detail="Application not found.",
        )

    return application


def get_hr_job(
    job_id: int,
    user_id: int,
    db: Session,
) -> Job:
    hr = (
        db.query(HRUser)
        .filter(HRUser.user_id == user_id)
        .first()
    )

    if not hr:
        raise HTTPException(
            status_code=403,
            detail="HR profile not found.",
        )

    job = (
        db.query(Job)
        .filter(
            Job.id == job_id,
            Job.company_id == hr.company_id,
        )
        .first()
    )

    if not job:
        raise HTTPException(
            status_code=404,
            detail="Job not found or not accessible.",
        )

    return job


# --------------------------------------------------
# STUDENT: APPLY FOR A JOB
# --------------------------------------------------

@router.post(
    "/jobs/{job_id}",
    response_model=ApplicationResponse,
    status_code=status.HTTP_201_CREATED,
)
def apply_for_job(
    job_id: int,
    payload: ApplicationCreate,
    current_user: User = Depends(
        require_role(UserRole.STUDENT)
    ),
    db: Session = Depends(get_db),
):
    student = get_student_profile(current_user.id, db)

    job = db.query(Job).filter(
        Job.id == job_id
    ).first()

    if not job or job.status != "PUBLISHED":
        raise HTTPException(
            status_code=404,
            detail="Published job not found.",
        )

    resume = db.query(Resume).filter(
        Resume.id == payload.resume_id,
        Resume.student_id == student.id,
    ).first()

    if not resume:
        raise HTTPException(
            status_code=404,
            detail="Resume not found in your account.",
        )

    existing = db.query(Application).filter(
        Application.student_id == student.id,
        Application.job_id == job.id,
    ).first()

    if existing:
        raise HTTPException(
            status_code=409,
            detail="You have already applied for this job.",
        )

    application = Application(
        student_id=student.id,
        job_id=job.id,
        resume_id=resume.id,
        status="APPLIED",
    )

    try:
        db.add(application)
        db.commit()
        db.refresh(application)
        return application

    except Exception as exc:
        db.rollback()

        # The database constraint also protects against
        # simultaneous duplicate submissions.
        from sqlalchemy.exc import IntegrityError

        if isinstance(exc, IntegrityError):
            raise HTTPException(
                status_code=409,
                detail="An application for this job already exists.",
            ) from exc

        raise HTTPException(
            status_code=500,
            detail="Could not submit the application.",
        ) from exc


# --------------------------------------------------
# STUDENT: VIEW OWN APPLICATIONS
# --------------------------------------------------

@router.get(
    "/me",
    response_model=list[ApplicationResponse],
)
def get_my_applications(
    current_user: User = Depends(
        require_role(UserRole.STUDENT)
    ),
    db: Session = Depends(get_db),
):
    student = get_student_profile(current_user.id, db)

    return (
        db.query(Application)
        .filter(Application.student_id == student.id)
        .order_by(Application.applied_at.desc())
        .all()
    )


# --------------------------------------------------
# HR: VIEW/DOWNLOAD THE RESUME ATTACHED TO AN APPLICATION
# --------------------------------------------------

@router.get("/{application_id}/resume-file")
def get_application_resume_file(
    application_id: int,
    current_user: User = Depends(require_role(UserRole.HR)),
    db: Session = Depends(get_db),
):
    # Join through the job and HR company so an HR user can only access
    # resumes attached to applications for jobs owned by their company.
    application = (
        db.query(Application)
        .join(Job, Application.job_id == Job.id)
        .join(HRUser, HRUser.company_id == Job.company_id)
        .filter(
            Application.id == application_id,
            HRUser.user_id == current_user.id,
        )
        .first()
    )
    if not application:
        raise HTTPException(status_code=404, detail="Application not found.")
    if not application.resume:
        raise HTTPException(status_code=404, detail="No resume is attached to this application.")

    stored_path = Path(application.resume.file_path)
    upload_root = Path("uploads/resumes").resolve()
    file_path = (Path.cwd() / stored_path).resolve() if not stored_path.is_absolute() else stored_path.resolve()
    try:
        file_path.relative_to(upload_root)
    except ValueError:
        raise HTTPException(status_code=404, detail="Resume file is unavailable.")

    if file_path.suffix.lower() not in {".pdf", ".docx"} or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Resume file is unavailable.")

    original_name = Path(application.resume.file_name or file_path.name).name
    if file_path.suffix.lower() == ".pdf":
        return FileResponse(
            path=file_path,
            media_type="application/pdf",
            filename=original_name,
            content_disposition_type="inline",
        )

    return FileResponse(
        path=file_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=original_name,
        content_disposition_type="attachment",
    )


# --------------------------------------------------
# STUDENT: VIEW APPLICATION DETAILS
# --------------------------------------------------

@router.get(
    "/{application_id}",
    response_model=ApplicationResponse,
)
def get_application_details(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role == UserRole.STUDENT:
        student = get_student_profile(current_user.id, db)

        return get_application_for_student(
            application_id,
            student.id,
            db,
        )

    if current_user.role == UserRole.HR:
        application = (
            db.query(Application)
            .join(Job, Application.job_id == Job.id)
            .join(HRUser, HRUser.company_id == Job.company_id)
            .filter(
                Application.id == application_id,
                HRUser.user_id == current_user.id,
            )
            .first()
        )

        if not application:
            raise HTTPException(
                status_code=404,
                detail="Application not found.",
            )

        return application

    if current_user.role == UserRole.ADMIN:
        application = db.query(Application).filter(
            Application.id == application_id
        ).first()

        if application:
            return application

    raise HTTPException(
        status_code=404,
        detail="Application not found.",
    )


# --------------------------------------------------
# HR: VIEW APPLICANTS FOR A COMPANY'S JOB
# --------------------------------------------------

@router.get(
    "/jobs/{job_id}/applicants",
    response_model=list[ApplicantResponse],
)
def get_job_applicants(
    job_id: int,
    current_user: User = Depends(
        require_role(UserRole.HR)
    ),
    db: Session = Depends(get_db),
):
    get_hr_job(job_id, current_user.id, db)

    applications = (
        db.query(Application)
        .options(
            joinedload(Application.student).joinedload(Student.user)
        )
        .filter(Application.job_id == job_id)
        .order_by(Application.applied_at.desc())
        .all()
    )

    return [
        ApplicantResponse(
            id=application.id,
            student_id=application.student_id,
            student_name=application.student.full_name,
            student_email=application.student.user.email,
            resume_id=application.resume_id,
            status=application.status,
            applied_at=application.applied_at,
            updated_at=application.updated_at,
        )
        for application in applications
    ]


# --------------------------------------------------
# HR: UPDATE APPLICATION STATUS
# --------------------------------------------------

@router.patch(
    "/{application_id}/status",
    response_model=ApplicationResponse,
)
def update_application_status(
    application_id: int,
    payload: ApplicationStatusUpdate,
    current_user: User = Depends(
        require_role(UserRole.HR)
    ),
    db: Session = Depends(get_db),
):
    application = (
        db.query(Application)
        .join(Job, Application.job_id == Job.id)
        .join(HRUser, HRUser.company_id == Job.company_id)
        .filter(
            Application.id == application_id,
            HRUser.user_id == current_user.id,
        )
        .first()
    )

    if not application:
        raise HTTPException(
            status_code=404,
            detail="Application not found.",
        )

    if payload.status not in ALLOWED_STATUSES:
        raise HTTPException(
            status_code=400,
            detail="Invalid application status.",
        )

    application.status = payload.status

    try:
        db.commit()
        db.refresh(application)
        return application

    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Could not update application status.",
        ) from exc