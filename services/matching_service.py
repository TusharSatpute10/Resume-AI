import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy.orm import Session, joinedload

from services.skill_normalizer import normalize_skill_key

from db.models.application import Application
from db.models.job import Job
from db.models.job_skill import JobSkill
from db.models.match_result import MatchResult
from db.models.resume import Resume
from db.models.resume_skill import ResumeSkill


MODEL_VERSION = "minilm-matching-v5-evidence-aware-scoring"

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


# Load the embedding model only once per backend process.
_embedding_model = None
_embedding_model_initialized = False


def get_embedding_model():
    global _embedding_model, _embedding_model_initialized

    if not _embedding_model_initialized:
        _embedding_model_initialized = True

        try:
            from sentence_transformers import SentenceTransformer

            _embedding_model = SentenceTransformer(
                "sentence-transformers/all-MiniLM-L6-v2",
                device="cpu",
            )

            print("Sentence Transformer model loaded successfully.")

        except Exception as error:
            print(f"Embedding model unavailable: {error}")
            _embedding_model = None

    return _embedding_model


def semantic_similarity(job_text: str, resume_text: str) -> float:
    """
    Calculate contextual similarity using Sentence Transformers.

    Falls back to TF-IDF if the embedding model is unavailable.
    Returns a score between 0 and 100.
    """

    if not job_text.strip() or not resume_text.strip():
        return 0.0

    model = get_embedding_model()

    if model is not None:
        try:
            embeddings = model.encode(
                [job_text, resume_text],
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False,
            )

            similarity = cosine_similarity(
                embeddings[0:1],
                embeddings[1:2],
            )[0][0]

            return round(
                max(0.0, min(float(similarity), 1.0)) * 100,
                2,
            )

        except Exception as error:
            print(f"Embedding similarity failed: {error}")

    # TF-IDF fallback
    try:
        vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            max_features=10000,
        )

        matrix = vectorizer.fit_transform([job_text, resume_text])

        similarity = cosine_similarity(
            matrix[0:1],
            matrix[1:2],
        )[0][0]

        return round(float(similarity) * 100, 2)

    except ValueError:
        return 0.0

def calculate_skill_score(
    job_requirements: list,
    resume_skills: list,
) -> tuple[float, list[str], list[str]]:
    """
    Calculate weighted skill coverage using:
    - Normalized skill names
    - Required/preferred importance
    - Minimum experience requirements
    - Recorded proficiency, when available

    Missing per-skill experience/proficiency does not reduce skill credit. Recorded values are heuristic signals, not verified measurements.
    """

    # Index candidate skills using normalized names.
    candidate_skills = {}

    for item in resume_skills:
        if not item.skill or not item.skill.name:
            continue

        key = normalize_skill_key(item.skill.name)

        if key:
            candidate_skills[key] = item

    # Merge duplicate job requirements.
    requirements = {}

    for requirement in job_requirements:
        if not requirement.skill or not requirement.skill.name:
            continue

        skill_name = requirement.skill.name
        key = normalize_skill_key(skill_name)

        if not key:
            continue

        requirement_type = normalize_text(
            requirement.requirement_type
        )

        default_weight = (
            0.5 if requirement_type == "preferred" else 1.0
        )

        importance = (
            requirement.importance_weight
            if requirement.importance_weight is not None
            else default_weight
        )

        importance = max(0.0, min(float(importance), 1.0))

        minimum_years = requirement.minimum_years

        if key not in requirements:
            requirements[key] = {
                "name": skill_name,
                "weight": importance,
                "minimum_years": minimum_years,
            }
        else:
            existing = requirements[key]

            existing["weight"] = max(
                existing["weight"],
                importance,
            )

            if minimum_years is not None:
                existing["minimum_years"] = max(
                    existing["minimum_years"] or 0.0,
                    minimum_years,
                )

    total_weight = sum(
        item["weight"] for item in requirements.values()
    )

    if total_weight <= 0:
        return 0.0, [], []

    earned_weight = 0.0
    matched_skills = []
    missing_skills = []

    # Proficiency multipliers are heuristic signals, not verified measurements.
    proficiency_factors = {
        "beginner": 0.75,
        "novice": 0.60,
        "intermediate": 0.90,
        "advanced": 1.0,
        "expert": 1.0,
    }

    for key, requirement in requirements.items():

        candidate_skill = candidate_skills.get(key)

        if candidate_skill is None:
            missing_skills.append(requirement["name"])
            continue

        matched_skills.append(requirement["name"])

        skill_factor = 1.0

        # Apply experience adjustment only when both values are available.
        required_years = requirement["minimum_years"]
        candidate_years = candidate_skill.years_experience

        if (
            required_years is not None
            and required_years > 0
            and candidate_years is not None
        ):
            experience_factor = min(
                max(candidate_years, 0.0) / required_years,
                1.0,
            )

            skill_factor *= experience_factor

        # Apply proficiency adjustment only for recognized values.
        proficiency = normalize_text(
            candidate_skill.proficiency
        )

        if proficiency in proficiency_factors:
            skill_factor *= proficiency_factors[proficiency]

        earned_weight += (
            requirement["weight"] * skill_factor
        )

    score = (earned_weight / total_weight) * 100

    return (
        round(score, 2),
        matched_skills,
        missing_skills,
    )

def calculate_experience_score(job: Job, resume: Resume) -> float:
    """Return experience fit; 0 is a real shortfall, 100 is neutral when unrequired.

    If the job requires experience but the resume has no extracted total,
    the returned 0 is only a storage-compatible placeholder. The component
    is marked unavailable and excluded from the final weighted score.
    """
    required = job.required_experience_years or 0.0
    candidate = resume.total_experience_years

    if required <= 0:
        return 0.0
    if candidate is None:
        return 0.0

    return round(
        min(max(candidate, 0.0) / required, 1.0) * 100,
        2,
    )


def calculate_education_score(job: Job, resume: Resume) -> float:
    """Estimate education relevance from extracted education fields.

    A 0 return value is a storage-compatible placeholder when this component
    cannot be evaluated; availability is handled separately.
    """
    required = normalize_text(job.required_education)
    if not required or not resume.education:
        return 0.0

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
    """Compare extracted project information with the job description."""
    projects = resume.projects
    job_text = normalize_text(f"{job.title or ''} {job.description or ''}")

    if not projects or not job_text:
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
    availability: dict[str, bool] | None = None,
) -> str:
    """Explain observed evidence without treating missing extraction as failure."""
    availability = availability or {}
    strengths: list[str] = []
    gaps: list[str] = []
    unavailable: list[str] = []

    if availability.get("skill", False):
        if matched_skills:
            strengths.append(
                f"matches {len(matched_skills)} listed job skill(s): "
                + ", ".join(matched_skills[:8])
            )
        if missing_skills:
            gaps.append(
                "job skills not found in the parsed resume: "
                + ", ".join(missing_skills[:8])
            )
    else:
        unavailable.append("no job skill requirements were available to compare")

    if availability.get("experience", False):
        required_years = job.required_experience_years or 0.0
        candidate_years = resume.total_experience_years
        if candidate_years is not None:
            if experience_score >= 99.99:
                strengths.append(
                    f"recorded experience ({candidate_years:g} years) meets "
                    f"the {required_years:g}-year requirement"
                )
            elif experience_score >= 60:
                strengths.append(
                    f"recorded experience ({candidate_years:g} years) partly "
                    f"meets the {required_years:g}-year requirement"
                )
                gaps.append("recorded experience is below the stated requirement")
            else:
                gaps.append(
                    f"recorded experience ({candidate_years:g} years) is below "
                    f"the {required_years:g}-year requirement"
                )
        else:
            unavailable.append("experience information was not extracted")
    elif (job.required_experience_years or 0) <= 0:
        unavailable.append("the job does not specify a minimum experience requirement")
    else:
        unavailable.append("experience information was not extracted")

    if availability.get("education", False):
        if education_score >= 80:
            strengths.append("extracted education details align well with the stated requirement")
        else:
            gaps.append("extracted education details have limited overlap with the stated requirement")
    elif job.required_education and not resume.education:
        unavailable.append("education information was not extracted")
    elif not job.required_education:
        unavailable.append("the job does not specify an education requirement")
    else:
        unavailable.append("education details were present but could not be compared reliably")

    if availability.get("project", False):
        if project_score >= 35:
            strengths.append("at least one extracted project shares terminology with the job description")
        else:
            gaps.append("extracted project descriptions show limited keyword overlap with the job description")
    else:
        unavailable.append("no project information was available for comparison")

    if availability.get("semantic", False):
        if semantic_score >= 20:
            strengths.append("resume text has measurable similarity to the job description")
        else:
            gaps.append("resume wording has low text similarity to the job description")
    else:
        unavailable.append("insufficient resume or job text for text-similarity analysis")

    if strengths:
        rationale = "This candidate shows potential fit based on the extracted resume evidence: " + "; ".join(strengths) + "."
    else:
        rationale = "The available extracted resume data provides limited positive evidence for this role."

    if gaps:
        rationale += " Evidence-based gaps: " + "; ".join(gaps) + "."
    if unavailable:
        rationale += " Not evaluated: " + "; ".join(unavailable) + "."

    rationale += (
        f" Component scores (0–100; unavailable components are excluded from "
        f"the final score): skills {skill_score:.1f} (40% nominal weight), "
        f"text similarity {semantic_score:.1f} (25%), "
        f"experience {experience_score:.1f} (15%), "
        f"education {education_score:.1f} (10%), "
        f"projects {project_score:.1f} (10%). "
        "Text similarity uses Sentence Transformer embeddings when available, "
        "with TF-IDF similarity as a fallback; it is not an LLM judgment. "
        "Scores rely only on extracted resume data and should support, not replace, "
        "human review."
    )
    return rationale


def calculate_candidate_match(job: Job, resume: Resume) -> dict:
    """Calculate component scores and renormalize weights over available evidence."""
    skill_score, matched_skills, missing_skills = calculate_skill_score(
        job.job_skills,
        resume.resume_skills,
    )

    job_text = f"{job.title or ''} {job.description or ''}".strip()
    resume_text = " ".join(
        [
            resume.summary or "",
            resume.raw_text or "",
            " ".join(
                skill.skill.name
                for skill in resume.resume_skills
                if skill.skill and skill.skill.name
            ),
            " ".join(
                f"{project.name or ''} "
                f"{project.description or ''} "
                f"{project.technologies or ''}"
                for project in resume.projects
            ),
        ]
    ).strip()

    # These flags distinguish an actual score of zero from unavailable evidence.
    availability = {
        "skill": bool(job.job_skills),
        "semantic": bool(job_text and resume_text),
        "experience": (
            (job.required_experience_years or 0) > 0
            and resume.total_experience_years is not None
        ),
        "education": bool(
            normalize_text(job.required_education) and resume.education
        ),
        "project": bool(resume.projects and job_text),
    }

    semantic_score = (
        semantic_similarity(job_text, resume_text)
        if availability["semantic"] else 0.0
    )
    experience_score = calculate_experience_score(job, resume)
    education_score = calculate_education_score(job, resume)
    project_score = calculate_project_score(job, resume)

    component_scores = {
        "skill": skill_score,
        "semantic": semantic_score,
        "experience": experience_score,
        "education": education_score,
        "project": project_score,
    }

    available_weight = sum(
        WEIGHTS[name]
        for name, is_available in availability.items()
        if is_available
    )

    if available_weight > 0:
        final_score = sum(
            component_scores[name] * WEIGHTS[name]
            for name, is_available in availability.items()
            if is_available
        ) / available_weight
    else:
        final_score = 0.0

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
        availability,
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
        "score_availability": availability,
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
