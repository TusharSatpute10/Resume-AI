import json
import re

from ollama import Client

from config.settings import get_settings
from schemas.resume_ai import ParsedResume

settings = get_settings()

client = Client(host=settings.ollama_base_url)


RESUME_SCHEMA = {
    "profile_links": {
        "linkedin_url": None,
        "github_url": None,
        "portfolio_url": None,
    },
    "skills": [],
    "education": [
        {
            "degree": "",
            "field_of_study": "",
            "institution": "",
            "start_year": None,
            "end_year": None,
            "grade": "",
        }
    ],
    "experience": [
        {
            "company_name": "",
            "job_title": "",
            "location": "",
            "start_date": "",
            "end_date": "",
            "description": "",
            "years": 0,
        }
    ],
    "projects": [
        {
            "name": "",
            "description": "",
            "technologies": [],
            "project_url": None,
        }
    ],
    "certifications": [
        {
            "name": "",
            "issuer": "",
            "issue_date": "",
            "credential_url": None,
        }
    ],
    "summary": "",
    "total_experience_years": 0,
    "experience_level": "",
}


def extract_json_from_response(content: str) -> dict:
    """
    Extract a JSON object from an LLM response.

    Supports:
    - Raw JSON
    - Markdown JSON code fences
    - Explanatory text before or after the JSON
    """

    if not isinstance(content, str) or not content.strip():
        raise ValueError("AI returned an empty response")

    content = content.strip()

    # First, attempt to parse the complete response.
    try:
        parsed = json.loads(content)

        if isinstance(parsed, dict):
            return parsed

    except json.JSONDecodeError:
        pass

    # Remove Markdown code fences if present.
    content = re.sub(
        r"^\s*```(?:json)?\s*",
        "",
        content,
        flags=re.IGNORECASE,
    )

    content = re.sub(
        r"\s*```\s*$",
        "",
        content,
    ).strip()

    # Attempt to parse the cleaned response.
    try:
        parsed = json.loads(content)

        if isinstance(parsed, dict):
            return parsed

    except json.JSONDecodeError:
        pass

    # Extract the first complete JSON object from surrounding text.
    start = content.find("{")

    if start == -1:
        raise ValueError(
            "AI response does not contain a JSON object"
        )

    try:
        parsed, _ = json.JSONDecoder().raw_decode(
            content[start:]
        )

    except json.JSONDecodeError as exc:
        raise ValueError(
            f"AI returned invalid JSON: {exc}"
        ) from exc

    if not isinstance(parsed, dict):
        raise ValueError(
            "AI response must contain a JSON object"
        )

    return parsed


def normalize_url(value):
    """
    Convert invalid, missing, or placeholder URL values to None.
    Preserve valid HTTP and HTTPS URLs.
    """

    if not isinstance(value, str):
        return None

    value = value.strip()

    # Normalize common AI-generated placeholders.
    if value.casefold() in {
        "",
        "null",
        "none",
        "n/a",
        "na",
        "not available",
        "not provided",
        "unknown",
    }:
        return None

    # Extract the URL from a Markdown link.
    markdown_match = re.fullmatch(
        r"\[.*?\]\((https?://[^)]+)\)",
        value,
    )

    if markdown_match:
        value = markdown_match.group(1).strip()

    # Only accept HTTP or HTTPS URLs.
    if not value.startswith(("https://", "http://")):
        return None

    return value


def normalize_resume_urls(parsed: dict) -> dict:
    """
    Normalize profile links and project URLs before schema validation.
    """

    parsed = parsed.copy()

    # Normalize profile links.
    profile_links = parsed.get("profile_links") or {}

    if not isinstance(profile_links, dict):
        profile_links = {}

    profile_links = profile_links.copy()

    for key in (
        "linkedin_url",
        "github_url",
        "portfolio_url",
    ):
        profile_links[key] = normalize_url(
            profile_links.get(key)
        )

    parsed["profile_links"] = profile_links

    # Normalize project URLs.
    projects = parsed.get("projects") or []

    if not isinstance(projects, list):
        projects = []

    normalized_projects = []

    for project in projects:
        if not isinstance(project, dict):
            continue

        project = project.copy()

        project["project_url"] = normalize_url(
            project.get("project_url")
        )

        normalized_projects.append(project)

    parsed["projects"] = normalized_projects

    # Normalize certification URLs.
    certifications = parsed.get("certifications") or []

    if not isinstance(certifications, list):
        certifications = []

    normalized_certifications = []

    for certification in certifications:
        if not isinstance(certification, dict):
            continue

        certification = certification.copy()

        certification["credential_url"] = normalize_url(
            certification.get("credential_url")
        )

        normalized_certifications.append(certification)

    parsed["certifications"] = normalized_certifications

    return parsed


def parse_resume_with_ai(resume_text: str) -> dict:
    """
    Parse resume text using Ollama/Mistral and validate the result.
    """

    if not isinstance(resume_text, str) or not resume_text.strip():
        raise ValueError("Resume text cannot be empty")

    prompt = f"""
You are a professional resume information extraction system.

Extract structured information from the resume below.

IMPORTANT RULES:

1. Return a single valid JSON object.
2. Do not include explanations, introductions, Markdown, or code fences.
3. Do not invent information.
4. For missing information, use:
   - [] for missing lists
   - "" for missing text
   - 0 for missing numeric values
   - null for missing URLs and unavailable dates where appropriate
5. Extract only information explicitly supported by the resume.
6. Preserve the candidate's actual wording where practical.
7. Extract technical and professional skills explicitly mentioned in the resume.
8. Return skills as a simple list of skill names.
9. Do not invent skill proficiency or years of experience.
10. Calculate total_experience_years only from explicitly stated or
    clearly dated professional work experience.
11. Do not count education, coursework, or personal projects as
    professional employment experience.
12. Use "Student" when the candidate is studying and has no
    professional work experience.
13. Use "Entry Level" for candidates with limited professional
    work experience.
14. Use "Mid Level" or "Senior Level" only when supported by
    sufficient professional work experience.
15. Generate the summary from the resume's actual content.
16. Return projects as structured objects, not strings.
17. Extract profile links only when explicitly present in the resume
    or supplied source hyperlinks.
18. Do not fabricate LinkedIn, GitHub, portfolio, or project URLs.
19. Use null for unavailable URLs.

Use exactly this JSON structure:

{json.dumps(RESUME_SCHEMA, indent=2)}

RESUME:
--------------------
{resume_text}
--------------------
"""

    try:
        response = client.chat(
            model=settings.ollama_model,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            options={
                "temperature": 0,
            },
        )

    except Exception as exc:
        raise ValueError(
            f"Failed to communicate with Ollama: {exc}"
        ) from exc

    # Ollama's response is a ChatResponse object.
    # Access its message content using attributes.
    try:
        content = response.message.content

    except AttributeError:
        # Compatibility fallback for dictionary-like responses.
        try:
            content = response["message"]["content"]
        except (TypeError, KeyError, AttributeError) as exc:
            raise ValueError(
                "Could not read the AI response content"
            ) from exc

    print("\n========== MISTRAL DEBUG ==========")
    print("Model:", settings.ollama_model)
    print("Response object type:", type(response).__name__)
    print("Content type:", type(content).__name__)
    print(
        "Content length:",
        len(content) if isinstance(content, str) else 0,
    )

    if isinstance(content, str):
        print("Content preview:", repr(content[:500]))

    print("===================================\n")

    # Step 1: Extract the JSON object.
    parsed = extract_json_from_response(content)

    # Step 2: Normalize URL placeholders and invalid URLs.
    parsed = normalize_resume_urls(parsed)

    # Step 3: Validate the extracted data.
    try:
        validated_resume = ParsedResume.model_validate(parsed)

    except Exception as exc:
        raise ValueError(
            f"AI resume data failed schema validation: {exc}"
        ) from exc

    # Step 4: Return validated, JSON-compatible data.
    return validated_resume.model_dump(mode="json")