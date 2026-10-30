import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy.orm import Session, joinedload

from db.models.application import Application
from db.models.job import Job
from db.models.job_skill import JobSkill
from db.models.match_result import MatchResult
from db.models.resume import Resume
from db.models.resume_skill import ResumeSkill


MODEL_VERSION = "tfidf-matching-v2-explanations"

WEIGHTS = {
    "skill": 0.40,
    "semantic": 0.25,
    "experience": 0.15,
    "education": 0.10,
    "project": 0.10,
}


def normalize_text(value: str | None) -> str:
    """Normalize text for consistent comparisons."""
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip().casefold()


def semantic_similarity(job_text: str, resume_text: str) -> float:
    """Calculate TF-IDF cosine similarity, returning a score from 0 to 100."""
    if not job_text.strip() or not resume_text.strip():
        return 0.0
    try:
        vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            max_features=10000,
        )
        matrix = vectorizer.fit_transform([job_text, resume_text])
        similarity = cosine_similarity(matrix[0:1], matrix[1:2])[0][0]
        return round(float(similarity) * 100, 2)
    except ValueError:
        return 0.0


def calculate_skill_score(
    job_requirements: list,
    resume_skills: list,
) -> tuple[float, list[str], list[str]]:
    """Calculate weighted skill coverage; required skills carry more weight."""
    candidate_skills = {
        normalize_text(item.skill.name)
        for item in resume_skills
        if item.skill and item.skill.name
    }
    matched_skills = []
    missing_skills = []
    total_weight = 0.0
    earned_weight = 0.0

    for requirement in job_requirements:
        skill_name = requirement.skill.name if requirement.skill else None
        if not skill_name:
            continue

        key = normalize_text(skill_name)
        default_weight = (
            0.5
            if normalize_text(requirement.requirement_type) == "preferred"
            else 1.0
        )
        importance = (
            requirement.importance_weight
            if requirement.importance_weight is not None
            else default_weight
        )
        importance = max(0.0, min(float(importance), 1.0))
        total_weight += importance

        if key in candidate_skills:
            matched_skills.append(skill_name)
            earned_weight += importance
        else:
            missing_skills.append(skill_name)

    if total_weight == 0:
        return 0.0, matched_skills, missing_skills

    return round((earned_weight / total_weight) * 100, 2), matched_skills, missing_skills


def calculate_experience_score(job: Job, resume: Resume) -> float:
    """Compare recorded candidate experience with the job requirement."""
    required = job.required_experience_years or 0.0
    candidate = resume.total_experience_years or 0.0
    if required <= 0:
        return 100.0
    return round(min(candidate / required, 1.0) * 100, 2)


def calculate_education_score(job: Job, resume: Resume) -> float:
    """Estimate education relevance using recorded education fields."""
    required = normalize_text(job.required_education)
    if not required:
        return 100.0

    candidate_education = " ".join(
        normalize_text(
            f"{education.degree or ''} "
            f"{education.field_of_study or ''} "
            f"{education.institution or ''}"
        )
        for education in resume.education
    )
    if not candidate_education.strip():
        return 0.0

    required_tokens = set(re.findall(r"\b[a-z0-9+#.]+\b", required))
    candidate_tokens = set(
        re.findall(r"\b[a-z0-9+#.]+\b", candidate_education)
    )
    if not required_tokens:
        return 0.0

    overlap = len(required_tokens & candidate_tokens)
    return round(overlap / len(required_tokens) * 100, 2)


def calculate_project_score(job: Job, resume: Resume) -> float:
    """Compare job wording with recorded project information."""
    projects = resume.projects
    if not projects:
        return 0.0

    job_text = normalize_text(f"{job.title} {job.description}")
    if not job_text:
        return 0.0

    job_tokens = set(re.findall(r"\b[a-z0-9+#.]+\b", job_text))
    if not job_tokens:
        return 0.0

    best_score = 0.0
    for project in projects:
        project_text = normalize_text(
            f"{project.name or ''} "
            f"{project.description or ''} "
            f"{project.technologies or ''}"
        )
        project_tokens = set(
            re.findall(r"\b[a-z0-9+#.]+\b", project_text)
        )
        if not project_tokens:
            continue

        overlap = len(job_tokens & project_tokens)
        best_score = max(best_score, overlap / len(job_tokens) * 100)

    return round(min(best_score, 100.0), 2)


def build_explanation(
    job: Job,
    resume: Resume,
    skill_score: float,
    semantic_score: float,
    experience_score: float,
    education_score: float,
    project_score: float,
    matched_skills: list[str],
    missing_skills: list[str],
) -> str:
    """Explain why the candidate scored as they did, using observed evidence."""
    strengths = []
    gaps = []

    if matched_skills:
        strengths.append(
            f"matches {len(matched_skills)} listed job skill(s): "
            + ", ".join(matched_skills[:8])
        )
    if experience_score >= 90:
        strengths.append("meets the recorded experience requirement")
    elif experience_score >= 60:
        strengths.append("partly meets the recorded experience requirement")
    elif (job.required_experience_years or 0) > 0:
        gaps.append(
            f"recorded experience ({resume.total_experience_years or 0:g} years) "
            f"is below the job requirement ({job.required_experience_years:g} years)"
        )

    if education_score >= 80:
        strengths.append("education details align well with the stated requirement")
    elif job.required_education:
        if resume.education:
            gaps.append("the parsed education details only partially match the stated requirement")
        else:
            gaps.append("no education details were extracted from the resume")

    if project_score >= 35:
        strengths.append("at least one listed project shares terminology with the job description")
    elif not resume.projects:
        gaps.append("no projects were extracted from the resume")
    else:
        gaps.append("project descriptions show limited keyword overlap with this job description")

    if semantic_score >= 20:
        strengths.append("resume text has a reasonable text similarity to the job description")
    else:
        gaps.append("overall resume wording has low text similarity to the job description")

    if missing_skills:
        gaps.append("job skills not found in the parsed resume: " + ", ".join(missing_skills[:8]))

    if strengths:
        rationale = "This candidate is a potential fit because the resume " + "; and ".join(strengths) + "."
    else:
        rationale = "The available parsed resume data provides limited positive evidence for this role."

    if gaps:
        rationale += " Main gaps to review: " + "; and ".join(gaps) + "."
    else:
        rationale += " No major gaps were detected in the fields this matcher checks."

    rationale += (
        f" Score drivers (0–100): skills {skill_score:.1f} (40% weight), "
        f"text similarity {semantic_score:.1f} (25%), experience {experience_score:.1f} (15%), "
        f"education {education_score:.1f} (10%), projects {project_score:.1f} (10%). "
        "Text similarity is TF-IDF keyword similarity, not an LLM judgment. "
        "These findings are based only on extracted resume data; verify the resume and requirements during human review."
    )
    return rationale


def calculate_candidate_match(job: Job, resume: Resume) -> dict:
    """Calculate all component scores for one job-resume pair."""
    skill_score, matched_skills, missing_skills = calculate_skill_score(
        job.job_skills,
        resume.resume_skills,
    )
    job_text = f"{job.title or ''} {job.description or ''}"
    resume_text = " ".join(
        [
            resume.summary or "",
            resume.raw_text or "",
            " ".join(
                skill.skill.name
                for skill in resume.resume_skills
                if skill.skill
            ),
            " ".join(
                f"{project.name or ''} "
                f"{project.description or ''} "
                f"{project.technologies or ''}"
                for project in resume.projects
            ),
        ]
    )

    semantic_score = semantic_similarity(job_text, resume_text)
    experience_score = calculate_experience_score(job, resume)
    education_score = calculate_education_score(job, resume)
    project_score = calculate_project_score(job, resume)

    final_score = (
        skill_score * WEIGHTS["skill"]
        + semantic_score * WEIGHTS["semantic"]
        + experience_score * WEIGHTS["experience"]
        + education_score * WEIGHTS["education"]
        + project_score * WEIGHTS["project"]
    )
    explanation = build_explanation(
        job,
        resume,
        skill_score,
        semantic_score,
        experience_score,
        education_score,
        project_score,
        matched_skills,
        missing_skills,
    )
    return {
        "semantic_score": semantic_score,
        "skill_score": skill_score,
        "experience_score": experience_score,
        "education_score": education_score,
        "project_score": project_score,
        "final_score": round(final_score, 2),
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "explanation": explanation,
    }


def rank_candidates(db: Session, job_id: int) -> list[MatchResult]:
    """
    Score and rank only resumes attached to applications for this job.
    Stale match rows for people who no longer have an application are removed.
    """
    job = (
        db.query(Job)
        .options(joinedload(Job.job_skills).joinedload(JobSkill.skill))
        .filter(Job.id == job_id)
        .first()
    )
    if not job:
        raise ValueError("Job not found.")
    if job.status != "PUBLISHED":
        raise ValueError("Only published jobs can be matched.")

    # Use the actual application records for this job as the source of truth.
    application_resume_ids = {
        resume_id
        for (resume_id,) in (
            db.query(Application.resume_id)
            .filter(Application.job_id == job.id)
            .all()
        )
        if resume_id is not None
    }

    # Remove results for resumes that are no longer applicants for this job.
    stale_query = db.query(MatchResult).filter(MatchResult.job_id == job.id)
    if application_resume_ids:
        stale_query = stale_query.filter(
            ~MatchResult.resume_id.in_(application_resume_ids)
        )
    stale_query.delete(synchronize_session=False)

    if not application_resume_ids:
        db.commit()
        return []

    eligible_resumes = (
        db.query(Resume)
        .filter(Resume.id.in_(application_resume_ids))
        .options(
            joinedload(Resume.resume_skills).joinedload(ResumeSkill.skill),
            joinedload(Resume.education),
            joinedload(Resume.projects),
            joinedload(Resume.student),
        )
        .all()
    )

    # Exclude any resume that is not linked to a valid student profile.
    eligible_resumes = [
        resume
        for resume in eligible_resumes
        if resume.student is not None
    ]

    # If application records exist but none point to usable resumes, clear old
    # results and return an empty list rather than showing stale candidates.
    eligible_resume_ids = {resume.id for resume in eligible_resumes}
    if eligible_resume_ids:
        db.query(MatchResult).filter(
            MatchResult.job_id == job.id,
            ~MatchResult.resume_id.in_(eligible_resume_ids),
        ).delete(synchronize_session=False)
    else:
        db.query(MatchResult).filter(
            MatchResult.job_id == job.id
        ).delete(synchronize_session=False)
        db.commit()
        return []

    scored_results = []
    try:
        for resume in eligible_resumes:
            scores = calculate_candidate_match(job, resume)
            existing = (
                db.query(MatchResult)
                .filter(
                    MatchResult.job_id == job.id,
                    MatchResult.resume_id == resume.id,
                )
                .first()
            )
            if existing is None:
                existing = MatchResult(
                    job_id=job.id,
                    resume_id=resume.id,
                )
                db.add(existing)

            existing.semantic_score = scores["semantic_score"]
            existing.skill_score = scores["skill_score"]
            existing.experience_score = scores["experience_score"]
            existing.education_score = scores["education_score"]
            existing.project_score = scores["project_score"]
            existing.final_score = scores["final_score"]
            existing.matched_skills = scores["matched_skills"]
            existing.missing_skills = scores["missing_skills"]
            existing.explanation = scores["explanation"]
            existing.model_version = MODEL_VERSION
            scored_results.append((existing, scores["final_score"]))

        db.flush()
        scored_results.sort(key=lambda item: item[1], reverse=True)
        for rank, (result, _) in enumerate(scored_results, start=1):
            result.rank = rank

        db.commit()
        for result, _ in scored_results:
            db.refresh(result)
        return [result for result, _ in scored_results]
    except Exception:
        db.rollback()
        raise
