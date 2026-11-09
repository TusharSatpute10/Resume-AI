import re


SKILL_ALIASES = {
    # Frontend
    "react": "React",
    "reactjs": "React",
    "react.js": "React",
    "nextjs": "Next.js",
    "next.js": "Next.js",
    "vuejs": "Vue.js",
    "vue.js": "Vue.js",

    # JavaScript ecosystem
    "js": "JavaScript",
    "javascript": "JavaScript",
    "node": "Node.js",
    "nodejs": "Node.js",
    "node.js": "Node.js",
    "ts": "TypeScript",
    "typescript": "TypeScript",

    # Backend
    "express": "Express.js",
    "expressjs": "Express.js",
    "express.js": "Express.js",
    "fastapi": "FastAPI",
    "django": "Django",
    "flask": "Flask",

    # Programming languages
    "py": "Python",
    "python": "Python",
    "cpp": "C++",
    "c++": "C++",
    "csharp": "C#",
    "c#": "C#",
    "java": "Java",

    # Databases
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "mongo": "MongoDB",
    "mongodb": "MongoDB",
    "mysql": "MySQL",
    "sqlite": "SQLite",

    # Data science / AI
    "ml": "Machine Learning",
    "machine learning": "Machine Learning",
    "ai": "Artificial Intelligence",
    "artificial intelligence": "Artificial Intelligence",
    "dl": "Deep Learning",
    "deep learning": "Deep Learning",
    "nlp": "Natural Language Processing",
    "natural language processing": "Natural Language Processing",
    "sklearn": "Scikit-learn",
    "scikit learn": "Scikit-learn",
    "scikit-learn": "Scikit-learn",

    # Cloud / DevOps
    "aws": "AWS",
    "amazon web services": "AWS",
    "gcp": "Google Cloud Platform",
    "google cloud": "Google Cloud Platform",
    "docker": "Docker",
    "k8s": "Kubernetes",
    "kubernetes": "Kubernetes",
}


def normalize_skill_key(value: str | None) -> str:
    """Return a comparable key for a skill name."""
    if not value:
        return ""

    value = value.strip().casefold()
    value = re.sub(r"\s+", " ", value)

    compact = re.sub(r"[\s._-]+", "", value)

    canonical = SKILL_ALIASES.get(
        value,
        SKILL_ALIASES.get(compact, value),
    )

    return canonical.casefold()


def canonical_skill_name(value: str | None) -> str:
    """Return the preferred display name for a known skill."""
    if not value:
        return ""

    value = value.strip()
    key = normalize_skill_key(value)

    for canonical in set(SKILL_ALIASES.values()):
        if canonical.casefold() == key:
            return canonical

    return value