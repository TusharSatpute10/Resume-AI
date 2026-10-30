from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from db.database import get_db
from db.models.job import Job
from db.models.job_skill import JobSkill
from db.models.skill import Skill
from db.models.hr_user import HRUser
from db.models.user import User

from core.dependencies import get_current_user, require_role
from constants.roles import UserRole

from schemas.job_skill import (
    JobSkillCreate,
    JobSkillResponse,
    JobSkillDetailResponse,
)

router = APIRouter(
    prefix="/jobs",
    tags=["Job Skill Requirements"],
)


def get_owned_job(
    job_id: int,
    current_user: User,
    db: Session,
) -> Job:
    """Return a job owned by the HR user's company."""

    hr = (
        db.query(HRUser)
        .filter(HRUser.user_id == current_user.id)
        .first()
    )

    if not hr:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
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
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found or you do not own this job.",
        )

    return job


@router.post(
    "/{job_id}/skills",
    response_model=JobSkillResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_job_skill(
    job_id: int,
    payload: JobSkillCreate,
    current_user: User = Depends(
        require_role(UserRole.HR)
    ),
    db: Session = Depends(get_db),
):
    """Add a skill requirement to a job."""

    job = get_owned_job(job_id, current_user, db)

    if job.status == "CLOSED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify skills for a closed job.",
        )

    skill = db.query(Skill).filter(
        Skill.id == payload.skill_id
    ).first()

    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skill not found.",
        )

    existing = db.query(JobSkill).filter(
        JobSkill.job_id == job_id,
        JobSkill.skill_id == payload.skill_id,
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This skill is already associated with the job.",
        )

    job_skill = JobSkill(
        job_id=job_id,
        skill_id=payload.skill_id,
        requirement_type=payload.requirement_type,
        minimum_years=payload.minimum_years,
        importance_weight=payload.importance_weight,
    )

    try:
        db.add(job_skill)
        db.commit()
        db.refresh(job_skill)
        return job_skill

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not add the job skill.",
        )


@router.get(
    "/{job_id}/skills",
    response_model=list[JobSkillDetailResponse],
)
def list_job_skills(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List skill requirements for a job."""

    job = db.query(Job).filter(
        Job.id == job_id
    ).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found.",
        )

    # Students can view published jobs only.
    if current_user.role == UserRole.STUDENT:
        if job.status != "PUBLISHED":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found.",
            )

    # HR users can view skills for jobs owned by their company.
    elif current_user.role == UserRole.HR:
        hr = db.query(HRUser).filter(
            HRUser.user_id == current_user.id
        ).first()

        if not hr or hr.company_id != job.company_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot view skills for this job.",
            )

    results = (
        db.query(JobSkill, Skill)
        .join(Skill, JobSkill.skill_id == Skill.id)
        .filter(JobSkill.job_id == job_id)
        .order_by(Skill.name)
        .all()
    )

    return [
        JobSkillDetailResponse(
            job_id=job_skill.job_id,
            skill_id=job_skill.skill_id,
            requirement_type=job_skill.requirement_type,
            minimum_years=job_skill.minimum_years,
            importance_weight=job_skill.importance_weight,
            skill_name=skill.name,
            skill_category=skill.category,
        )
        for job_skill, skill in results
    ]


@router.patch(
    "/{job_id}/skills/{skill_id}",
    response_model=JobSkillResponse,
)
def update_job_skill(
    job_id: int,
    skill_id: int,
    payload: JobSkillCreate,
    current_user: User = Depends(
        require_role(UserRole.HR)
    ),
    db: Session = Depends(get_db),
):
    """Update a skill requirement for a job."""

    get_owned_job(job_id, current_user, db)

    job_skill = db.query(JobSkill).filter(
        JobSkill.job_id == job_id,
        JobSkill.skill_id == skill_id,
    ).first()

    if not job_skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job skill requirement not found.",
        )

    # Prevent changing the skill ID through this endpoint.
    if payload.skill_id != skill_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use the original skill ID when updating a requirement.",
        )

    job_skill.requirement_type = payload.requirement_type
    job_skill.minimum_years = payload.minimum_years
    job_skill.importance_weight = payload.importance_weight

    try:
        db.commit()
        db.refresh(job_skill)
        return job_skill

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not update the job skill.",
        )


@router.delete(
    "/{job_id}/skills/{skill_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_job_skill(
    job_id: int,
    skill_id: int,
    current_user: User = Depends(
        require_role(UserRole.HR)
    ),
    db: Session = Depends(get_db),
):
    """Remove a skill requirement from a job."""

    job = get_owned_job(job_id, current_user, db)

    if job.status == "CLOSED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify skills for a closed job.",
        )

    job_skill = db.query(JobSkill).filter(
        JobSkill.job_id == job_id,
        JobSkill.skill_id == skill_id,
    ).first()

    if not job_skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job skill requirement not found.",
        )

    try:
        db.delete(job_skill)
        db.commit()

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not delete the job skill.",
        )