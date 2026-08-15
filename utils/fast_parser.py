import re
import uuid
import spacy
from loguru import logger

nlp = spacy.load("en_core_web_sm")

TECH_SKILLS = {
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "rust",
    "ruby", "php", "swift", "kotlin", "scala", "r", "matlab",
    "react", "angular", "vue", "node.js", "fastapi", "django", "flask",
    "express", "spring", "html", "css", "rest", "graphql",
    "sql", "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
    "apache spark", "kafka", "airflow", "pandas", "numpy", "tensorflow",
    "pytorch", "scikit-learn", "keras",
    "aws", "azure", "gcp", "docker", "kubernetes", "terraform", "jenkins",
    "linux", "git", "machine learning", "deep learning", "nlp",
    "microservices", "agile", "scrum",
}


def fast_parse_resume(text):
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    text_lower = text.lower()

    # Smart name extraction — spaCy PERSON first
    doc_short = nlp(text[:1500])
    name = ""
    for ent in doc_short.ents:
        if ent.label_ == "PERSON" and len(ent.text.split()) >= 2:
            name = ent.text.strip()
            break

    # Fallback: scan first 5 lines for a name-like line
    if not name:
        for line in lines[:5]:
            words = line.split()
            if (2 <= len(words) <= 4
                and all(w.replace(".", "").isalpha() for w in words)
                and not line.isupper()
                and not any(w.lower() in {
                    "resume", "curriculum", "vitae", "cv",
                    "profile", "summary", "objective",
                    "engineer", "developer", "manager",
                    "analyst", "consultant", "specialist",
                    "senior", "junior", "lead", "head",
                } for w in words)):
                name = line.strip()
                break

    if not name:
        name = lines[0] if lines else "Unknown"

    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    email = email_match.group() if email_match else ""

    phone_match = re.search(r'(\+?\d[\d\s\-().]{8,}\d)', text)
    phone = phone_match.group().strip() if phone_match else ""

    hard_skills = [s.title() for s in TECH_SKILLS if s in text_lower]

    exp_match = re.search(r'(\d+)\+?\s*years?\s*(of\s*)?(experience|exp)', text_lower)
    exp_years = float(exp_match.group(1)) if exp_match else 0.0
    if exp_years < 2:    level = "entry"
    elif exp_years < 5:  level = "mid"
    elif exp_years < 10: level = "senior"
    else:                level = "lead"

    edu_match = re.search(r'(b\.?tech|b\.?e|b\.?sc|m\.?tech|mba|phd|bachelor|master)[^\n]*', text_lower)
    edu = [{"degree": edu_match.group().strip().title(), "institution": "", "field_of_study": "", "graduation_year": 0, "gpa": None}] if edu_match else []

    doc = nlp(text[:3000])
    orgs = [e.text for e in doc.ents if e.label_ == "ORG"]
    work_exp = [{"company": o, "role": "", "start_date": "", "end_date": "",
                 "duration_months": 0, "responsibilities": [],
                 "achievements": [], "tech_used": []} for o in orgs[:5]]

    logger.debug(f"Fast parsed resume | name={name} | skills={len(hard_skills)}")

    return {
        "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, text[:100])),
        "raw_doc_id": "fast_parse",
        "name": name,
        "email": email,
        "phone": phone,
        "location": "",
        "summary": "",
        "total_experience_years": exp_years,
        "experience_level": level,
        "hard_skills": hard_skills,
        "soft_skills": [],
        "certifications": [],
        "languages": [],
        "work_experience": work_exp,
        "education": edu,
        "projects": [],
        "awards": [],
        "parse_confidence": 0.75,
        "parse_warnings": ["Fast parsed"],
    }


def fast_parse_jd(text):
    text_lower = text.lower()
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    title = lines[0] if lines else "Unknown Role"

    for line in lines[:5]:
        words = line.split()
        if (1 <= len(words) <= 6
            and not line.isupper()
            and not any(c.isdigit() for c in line)):
            title = line.strip()
            break

    doc = nlp(text[:1000])
    company = next((e.text for e in doc.ents if e.label_ == "ORG"), "")
    required_skills = [s.title() for s in TECH_SKILLS if s in text_lower]
    exp_match = re.search(r'(\d+)\+?\s*years?', text_lower)
    exp_years = float(exp_match.group(1)) if exp_match else 0.0

    logger.debug(f"Fast parsed JD | title={title} | skills={len(required_skills)}")

    return {
        "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, text[:100])),
        "raw_doc_id": "fast_parse",
        "title": title,
        "company": company,
        "location": "",
        "remote_policy": "remote" if "remote" in text_lower else "",
        "employment_type": "",
        "salary_range": None,
        "required_skills": required_skills,
        "preferred_skills": [],
        "required_experience_years": exp_years,
        "experience_level": "senior" if exp_years >= 5 else "mid",
        "required_education": "",
        "responsibilities": [],
        "nice_to_have": [],
        "benefits": [],
        "parse_confidence": 0.75,
    }