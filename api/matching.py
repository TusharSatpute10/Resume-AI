import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi import Query
from sqlalchemy.orm import joinedload

from db.models.student import Student
from services.matching_service import calculate_candidate_match
from db.models.resume_skill import ResumeSkill
from db.models.job_skill import JobSkill

from db.database import get_db
from db.models.application import Application
from db.models.hr_user import HRUser
from db.models.job import Job
from db.models.match_result import MatchResult
from db.models.resume import Resume
from db.models.user import User

from core.dependencies import require_role
from constants.roles import UserRole
from schemas.matching import RankedCandidateResponse
from services.matching_service import rank_candidates


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/matching",
    tags=["AI Candidate Matching"],
)


def get_hr_owned_job(job_id: int, current_user: User, db: Session) -> Job:
    hr = (
        db.query(HRUser)
        .filter(HRUser.user_id == current_user.id)
        .first()
    )
    if not hr:
        raise HTTPException(status_code=403, detail="HR profile not found.")

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


def build_candidate_response(result: MatchResult, resume: Resume) -> dict:
    return {
        "id": result.id,
        "job_id": result.job_id,
        "resume_id": result.resume_id,
        "semantic_score": result.semantic_score,
        "skill_score": result.skill_score,
        "experience_score": result.experience_score,
        "education_score": result.education_score,
        "project_score": result.project_score,
        "final_score": result.final_score,
        "rank": result.rank,
        "matched_skills": result.matched_skills or [],
        "missing_skills": result.missing_skills or [],
        "explanation": result.explanation,
        "model_version": result.model_version,
        "created_at": result.created_at,
        "student_name": resume.student.full_name,
        "resume_file_name": resume.file_name,
    }


def build_responses_for_results(
    db: Session,
    results: list[MatchResult],
    applicant_resume_ids: set[int],
) -> list[dict]:
    response = []
    for result in results:
        # Defensively filter stale records at response time as well.
        if result.resume_id not in applicant_resume_ids:
            continue
        resume = (
            db.query(Resume)
            .filter(Resume.id == result.resume_id)
            .first()
        )
        if resume and resume.student:
            response.append(build_candidate_response(result, resume))
    return response


@router.post(
    "/jobs/{job_id}/run",
    response_model=list[RankedCandidateResponse],
)
def run_candidate_matching(
    job_id: int,
    current_user: User = Depends(require_role(UserRole.HR)),
    db: Session = Depends(get_db),
):
    job = get_hr_owned_job(job_id, current_user, db)
    if job.status != "PUBLISHED":
        raise HTTPException(
            status_code=400,
            detail="Only published jobs can be matched.",
        )

    try:
        results = rank_candidates(db, job.id)
        applicant_resume_ids = {
            resume_id
            for (resume_id,) in (
                db.query(Application.resume_id)
                .filter(Application.job_id == job.id)
                .all()
            )
            if resume_id is not None
        }
        return build_responses_for_results(
            db, results, applicant_resume_ids
        )
    except ValueError as exc:
        logger.warning(
            "Candidate matching validation failed for job_id=%s: %s",
            job_id,
            exc,
            exc_info=True,
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception(
            "Candidate matching failed for job_id=%s",
            job_id,
        )
        raise HTTPException(
            status_code=500,
            detail="Candidate matching failed. Check the server logs.",
        ) from exc


@router.get(
    "/jobs/{job_id}/results",
    response_model=list[RankedCandidateResponse],
)
def get_matching_results(
    job_id: int,
    current_user: User = Depends(require_role(UserRole.HR)),
    db: Session = Depends(get_db),
):
    job = get_hr_owned_job(job_id, current_user, db)
    try:
        applicant_resume_ids = {
            resume_id
            for (resume_id,) in (
                db.query(Application.resume_id)
                .filter(Application.job_id == job.id)
                .all()
            )
            if resume_id is not None
        }
        if not applicant_resume_ids:
            return []

        results = (
            db.query(MatchResult)
            .filter(
                MatchResult.job_id == job.id,
                MatchResult.resume_id.in_(applicant_resume_ids),
            )
            .order_by(
                MatchResult.rank.asc().nullslast(),
                MatchResult.final_score.desc(),
            )
            .all()
        )
        return build_responses_for_results(
            db, results, applicant_resume_ids
        )
    except Exception:
        logger.exception(
            "Failed to retrieve matching results for job_id=%s",
            job_id,
        )
        raise

@router.get(
    "/recommendations",
    tags=["Student AI Recommendations"],
)
def get_student_recommendations(
    resume_id: int = Query(..., gt=0),
    current_user: User = Depends(
        require_role(UserRole.STUDENT)
    ),
    db: Session = Depends(get_db),
):
    # 1. Get the logged-in student's profile.
    student = (
        db.query(Student)
        .filter(Student.user_id == current_user.id)
        .first()
    )

    if not student:
        raise HTTPException(
            status_code=404,
            detail="Student profile not found.",
        )

    # 2. Verify that the selected resume belongs to this student.
    resume = (
        db.query(Resume)
        .options(
            joinedload(Resume.resume_skills).joinedload(
                ResumeSkill.skill
            ),
            joinedload(Resume.education),
            joinedload(Resume.projects),
        )
        .filter(
            Resume.id == resume_id,
            Resume.student_id == student.id,
        )
        .first()
    )

    if not resume:
        raise HTTPException(
            status_code=404,
            detail="Selected resume was not found in your account.",
        )

    # 3. Load published jobs and their skill requirements.
    jobs = (
        db.query(Job)
        .options(
            joinedload(Job.job_skills).joinedload(
                JobSkill.skill
            ),
            joinedload(Job.company),
        )
        .filter(Job.status == "PUBLISHED")
        .order_by(Job.created_at.desc())
        .all()
    )

    # 4. Calculate the match score for every published job.
    recommendations = []

    for job in jobs:
        try:
            scores = calculate_candidate_match(job, resume)

            recommendations.append({
                "job_id": job.id,
                "title": job.title,
                "company_name": (
                    job.company.name if job.company else None
                ),
                "location": job.location,
                "remote_policy": job.remote_policy,
                "employment_type": job.employment_type,
                "salary_min": job.salary_min,
                "salary_max": job.salary_max,
                "required_experience_years": (
                    job.required_experience_years
                ),
                "experience_level": job.experience_level,
                "required_education": job.required_education,
                "description": job.description,
                "resume_id": resume.id,
                "resume_file_name": resume.file_name,
                "final_score": scores["final_score"],
                "skill_score": scores["skill_score"],
                "semantic_score": scores["semantic_score"],
                "experience_score": scores["experience_score"],
                "education_score": scores["education_score"],
                "project_score": scores["project_score"],
                "matched_skills": scores["matched_skills"],
                "missing_skills": scores["missing_skills"],
                "explanation": scores["explanation"],
            })

        except Exception:
            logger.exception(
                "Failed to calculate recommendation for "
                "job_id=%s, resume_id=%s",
                job.id,
                resume.id,
            )

    # 5. Show the strongest matches first.
    recommendations.sort(
        key=lambda item: item["final_score"],
        reverse=True,
    )

    return recommendations