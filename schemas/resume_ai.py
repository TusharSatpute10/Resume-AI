from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class ProfileLinks(BaseModel):
    model_config = ConfigDict(extra="ignore")

    linkedin_url: HttpUrl | None = None
    github_url: HttpUrl | None = None
    portfolio_url: HttpUrl | None = None


class SkillItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str = Field(min_length=1, max_length=100)


class EducationItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    degree: str | None = None
    field_of_study: str | None = None
    institution: str = Field(min_length=1, max_length=255)
    start_year: int | None = None
    end_year: int | None = None
    grade: str | None = None


class ExperienceItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    company_name: str = Field(min_length=1, max_length=255)
    job_title: str | None = None
    location: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    description: str | None = None
    years: float | None = Field(default=None, ge=0)


class ProjectItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    technologies: list[str] = Field(default_factory=list)
    project_url: HttpUrl | None = None


class CertificationItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str = Field(min_length=1, max_length=255)
    issuer: str | None = None
    issue_date: str | None = None
    credential_url: HttpUrl | None = None


class ParsedResume(BaseModel):
    model_config = ConfigDict(extra="ignore")

    profile_links: ProfileLinks = Field(default_factory=ProfileLinks)
    skills: list[str] = Field(default_factory=list)
    education: list[EducationItem] = Field(default_factory=list)
    experience: list[ExperienceItem] = Field(default_factory=list)
    projects: list[ProjectItem] = Field(default_factory=list)
    certifications: list[CertificationItem] = Field(default_factory=list)

    summary: str = ""
    total_experience_years: float = Field(default=0, ge=0)
    experience_level: str = "Student"

    @field_validator("skills")
    @classmethod
    def clean_skills(cls, skills: list[str]) -> list[str]:
        unique_skills = []
        seen = set()

        for skill in skills:
            skill = skill.strip()

            if not skill:
                continue

            normalized = skill.casefold()

            if normalized not in seen:
                seen.add(normalized)
                unique_skills.append(skill)

        return unique_skills