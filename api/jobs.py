from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from constants.roles import UserRole
from core.dependencies import require_role
from db.database import get_db
from db.models.company import Company
from db.models.hr_user import HRUser
from db.models.job import Job
from db.models.user import User
from schemas.job import JobCreate, JobResponse, JobUpdate


router = APIRouter(
    prefix="/jobs",
    tags=["Jobs"],
)


def serialize_job(job: Job) -> dict:
    """Build the public job response including its registered company name."""
    return {
        "id": job.id,
        "company_id": job.company_id,
        "created_by": job.created_by,
        "title": job.title,
        "description": job.description,
        "company_name": job.company.name if job.company else None,
        "location": job.location,
        "remote_policy": job.remote_policy,
        "employment_type": job.employment_type,
        "salary_min": job.salary_min,
        "salary_max": job.salary_max,
        "required_experience_years": job.required_experience_years,
        "experience_level": job.experience_level,
        "required_education": job.required_education,
        "status": job.status,
        "openings": job.openings,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
    }


def get_current_hr(
    current_user: User,
    db: Session,
) -> HRUser:
    hr = (
        db.query(HRUser)
        .filter(HRUser.user_id == current_user.id)
        .first()
    )

    if not hr:
        raise HTTPException(
            status_code=404,
            detail="HR profile not found",
        )

    return hr


def get_owned_job(
    job_id: int,
    hr: HRUser,
    db: Session,
) -> Job:
    """Return the SQLAlchemy Job model for an HR-owned job."""
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
            detail="Job not found in your company",
        )

    # Return the model, not serialize_job(job), so callers can access
    # attributes and update the database record.
    return job


@router.post(
    "",
    response_model=JobResponse,
    status_code=201,
)
def create_job(
    job_data: JobCreate,
    current_user: User = Depends(
        require_role(UserRole.HR.value)
    ),
    db: Session = Depends(get_db),
):
    hr = get_current_hr(current_user, db)

    company = (
        db.query(Company)
        .filter(Company.id == hr.company_id)
        .first()
    )

    if not company:
        raise HTTPException(
            status_code=404,
            detail="Company not found",
        )

    job = Job(
        **job_data.model_dump(),
        company_id=hr.company_id,
        created_by=hr.id,
        status="DRAFT",
    )

    try:
        db.add(job)
        db.commit()
        db.refresh(job)
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to create job",
        ) from exc

    return serialize_job(job)


@router.get(
    "/my",
    response_model=list[JobResponse],
)
def get_my_jobs(
    current_user: User = Depends(
        require_role(UserRole.HR.value)
    ),
    db: Session = Depends(get_db),
):
    hr = get_current_hr(current_user, db)

    jobs = (
        db.query(Job)
        .filter(
            Job.company_id == hr.company_id,
            Job.created_by == hr.id,
        )
        .order_by(Job.created_at.desc())
        .all()
    )
    return [serialize_job(job) for job in jobs]


@router.get(
    "",
    response_model=list[JobResponse],
)
def list_published_jobs(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    jobs = (
        db.query(Job)
        .filter(Job.status == "PUBLISHED")
        .order_by(Job.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [serialize_job(job) for job in jobs]


@router.get(
    "/{job_id}",
    response_model=JobResponse,
)
def get_job(
    job_id: int,
    current_user: User = Depends(
        require_role(
            UserRole.STUDENT.value,
            UserRole.HR.value,
            UserRole.ADMIN.value,
        )
    ),
    db: Session = Depends(get_db),
):
    query = db.query(Job).filter(Job.id == job_id)

    # Students and HR users can view published jobs.
    # HR users can also view their own company's drafts.
    if current_user.role == UserRole.HR.value:
        hr = get_current_hr(current_user, db)
        query = query.filter(
            (Job.status == "PUBLISHED")
            | (Job.company_id == hr.company_id)
        )
    elif current_user.role == UserRole.STUDENT.value:
        query = query.filter(Job.status == "PUBLISHED")
    # Admins can inspect jobs in any status.

    job = query.first()

    if not job:
        raise HTTPException(
            status_code=404,
            detail="Job not found",
        )

    return serialize_job(job)


@router.patch(
    "/{job_id}",
    response_model=JobResponse,
)
def update_job(
    job_id: int,
    job_data: JobUpdate,
    current_user: User = Depends(
        require_role(UserRole.HR.value)
    ),
    db: Session = Depends(get_db),
):
    hr = get_current_hr(current_user, db)
    job = get_owned_job(job_id, hr, db)

    update_data = job_data.model_dump(exclude_unset=True)

    # Do not permit null values for required fields.
    for field in ("title", "description", "openings"):
        if field in update_data and update_data[field] is None:
            raise HTTPException(
                status_code=422,
                detail=f"{field} cannot be null",
            )

    new_min = update_data.get("salary_min", job.salary_min)
    new_max = update_data.get("salary_max", job.salary_max)

    if (
        new_min is not None
        and new_max is not None
        and new_min > new_max
    ):
        raise HTTPException(
            status_code=422,
            detail="salary_min cannot exceed salary_max",
        )

    try:
        for field, value in update_data.items():
            setattr(job, field, value)

        db.commit()
        db.refresh(job)
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to update job",
        ) from exc

    return serialize_job(job)


@router.patch(
    "/{job_id}/publish",
    response_model=JobResponse,
)
def publish_job(
    job_id: int,
    current_user: User = Depends(
        require_role(UserRole.HR.value)
    ),
    db: Session = Depends(get_db),
):
    hr = get_current_hr(current_user, db)
    job = get_owned_job(job_id, hr, db)

    # Draft jobs are publishable; only CLOSED jobs are blocked.
    if job.status == "CLOSED":
        raise HTTPException(
            status_code=409,
            detail="A closed job cannot be published",
        )

    if (
        not job.title
        or not job.title.strip()
        or not job.description
        or len(job.description.strip()) < 20
    ):
        raise HTTPException(
            status_code=422,
            detail=(
                "Job title and description are required; "
                "description must contain at least 20 characters"
            ),
        )

    try:
        job.status = "PUBLISHED"
        db.commit()
        db.refresh(job)
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to publish job",
        ) from exc

    return serialize_job(job)


@router.patch(
    "/{job_id}/close",
    response_model=JobResponse,
)
def close_job(
    job_id: int,
    current_user: User = Depends(
        require_role(UserRole.HR.value)
    ),
    db: Session = Depends(get_db),
):
    hr = get_current_hr(current_user, db)
    job = get_owned_job(job_id, hr, db)

    try:
        job.status = "CLOSED"
        db.commit()
        db.refresh(job)
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to close job",
        ) from exc

    return serialize_job(job)
