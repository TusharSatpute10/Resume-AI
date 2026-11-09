from datetime import datetime

from sqlalchemy.orm import Session

from services.skill_normalizer import (
    canonical_skill_name,
    normalize_skill_key,
)

from db.models.resume import Resume
from db.models.student import Student
from db.models.skill import Skill
from db.models.resume_skill import ResumeSkill
from db.models.education import Education
from db.models.work_experience import WorkExperience
from db.models.project import Project
from db.models.certification import Certification


def store_parsed_resume(
    db: Session,
    resume: Resume,
    parsed_data: dict,
) -> Resume:

    # ---------------------------------------------------------
    # 1. Update resume-level information
    # ---------------------------------------------------------
    resume.summary = parsed_data.get("summary") or None

    total_experience = parsed_data.get("total_experience_years")
    resume.total_experience_years = (
        float(total_experience)
        if total_experience is not None
        else None
    )

    resume.experience_level = (
        parsed_data.get("experience_level") or None
    )

    # ---------------------------------------------------------
    # 2. Update student profile links
    # ---------------------------------------------------------
    student = (
        db.query(Student)
        .filter(Student.id == resume.student_id)
        .first()
    )

    if student:
        profile_links = parsed_data.get("profile_links", {})

        if profile_links.get("linkedin_url"):
            student.linkedin_url = profile_links["linkedin_url"]

        if profile_links.get("github_url"):
            student.github_url = profile_links["github_url"]

        if profile_links.get("portfolio_url"):
            student.portfolio_url = profile_links["portfolio_url"]

    # ---------------------------------------------------------
    # 3. Remove old structured resume data
    # ---------------------------------------------------------
    db.query(ResumeSkill).filter(
        ResumeSkill.resume_id == resume.id
    ).delete(synchronize_session=False)

    db.query(Education).filter(
        Education.resume_id == resume.id
    ).delete(synchronize_session=False)

    db.query(WorkExperience).filter(
        WorkExperience.resume_id == resume.id
    ).delete(synchronize_session=False)

    db.query(Project).filter(
        Project.resume_id == resume.id
    ).delete(synchronize_session=False)

    db.query(Certification).filter(
        Certification.resume_id == resume.id
    ).delete(synchronize_session=False)

    db.flush()

    # ---------------------------------------------------------
    # 4. Store normalized skills
    # ---------------------------------------------------------
    unique_skills = set()

    for raw_skill_name in parsed_data.get("skills", []):

        if not raw_skill_name:
            continue

        skill_name = canonical_skill_name(str(raw_skill_name))

        if not skill_name:
            continue

        normalized_name = normalize_skill_key(skill_name)

        if normalized_name in unique_skills:
            continue

        unique_skills.add(normalized_name)

        skill = (
            db.query(Skill)
            .filter(Skill.name.ilike(skill_name))
            .first()
        )

        if not skill:
            skill = Skill(
                name=skill_name,
                category=None,
            )
            db.add(skill)
            db.flush()

        db.add(
            ResumeSkill(
                resume_id=resume.id,
                skill_id=skill.id,
                proficiency=None,
                years_experience=None,
                source="AI",
            )
        )
    # ---------------------------------------------------------
    # 5. Store education
    # ---------------------------------------------------------
    for item in parsed_data.get("education", []):

        if not item.get("institution"):
            continue

        education = Education(
            resume_id=resume.id,
            institution=item.get("institution"),
            degree=item.get("degree") or None,
            field_of_study=item.get("field_of_study") or None,
            start_year=item.get("start_year"),
            end_year=item.get("end_year"),
            grade=item.get("grade") or None,
        )

        db.add(education)

    # ---------------------------------------------------------
    # 6. Store work experience
    # ---------------------------------------------------------
    for item in parsed_data.get("experience", []):

        if not item.get("company_name"):
            continue

        work_experience = WorkExperience(
            resume_id=resume.id,
            company_name=item.get("company_name"),
            job_title=item.get("job_title") or None,
            location=item.get("location") or None,
            start_date=parse_date(item.get("start_date")),
            end_date=parse_date(item.get("end_date")),
            description=item.get("description") or None,
            years=item.get("years"),
        )

        db.add(work_experience)

    # ---------------------------------------------------------
    # 7. Store projects
    # ---------------------------------------------------------
    for item in parsed_data.get("projects", []):

        if not item.get("name"):
            continue

        technologies = item.get("technologies", [])

        if isinstance(technologies, list):
            technologies_text = ", ".join(
                str(tech).strip()
                for tech in technologies
                if tech
            )
        else:
            technologies_text = str(technologies)

        project = Project(
            resume_id=resume.id,
            name=item.get("name"),
            description=item.get("description") or None,
            technologies=technologies_text or None,
            project_url=item.get("project_url"),
        )

        db.add(project)

    # ---------------------------------------------------------
    # 8. Store certifications
    # ---------------------------------------------------------
    for item in parsed_data.get("certifications", []):

        if not item.get("name"):
            continue

        certification = Certification(
            resume_id=resume.id,
            name=item.get("name"),
            issuer=item.get("issuer") or None,
            issue_date=parse_date(item.get("issue_date")),
            credential_url=item.get("credential_url"),
        )

        db.add(certification)

    # ---------------------------------------------------------
    # 9. Commit everything as one transaction
    # ---------------------------------------------------------
    db.commit()
    db.refresh(resume)

    return resume


def parse_date(value: str | None):

    if not value:
        return None

    if isinstance(value, datetime):
        return value.date()

    value = str(value).strip()

    if not value:
        return None

    formats = [
        "%Y-%m-%d",
        "%Y-%m",
        "%Y",
    ]

    for date_format in formats:

        try:

            parsed = datetime.strptime(
                value,
                date_format,
            )

            if date_format == "%Y":
                return parsed.date().replace(
                    month=1,
                    day=1,
                )

            if date_format == "%Y-%m":
                return parsed.date().replace(
                    day=1,
                )

            return parsed.date()

        except ValueError:
            continue

    return None
