from types import SimpleNamespace

from services.skill_normalizer import normalize_skill_key
from services.matching_service import (
    calculate_skill_score,
    semantic_similarity,
)


def make_skill(name, years=None, proficiency=None):
    return SimpleNamespace(
        skill=SimpleNamespace(name=name),
        years_experience=years,
        proficiency=proficiency,
    )


def make_requirement(name, years=None, weight=None, req_type="required"):
    return SimpleNamespace(
        skill=SimpleNamespace(name=name),
        minimum_years=years,
        importance_weight=weight,
        requirement_type=req_type,
    )


def test_skill_alias_normalization():
    assert normalize_skill_key("React.js") == normalize_skill_key("React")
    assert normalize_skill_key("JS") == normalize_skill_key("JavaScript")


def test_skill_experience_requirement():
    requirements = [make_requirement("Python", years=2)]
    candidate = [make_skill("Python", years=1)]

    score, matched, missing = calculate_skill_score(
        requirements, candidate
    )

    assert score == 50.0
    assert matched == ["Python"]
    assert missing == []


def test_unknown_experience_is_not_penalized():
    requirements = [make_requirement("Python", years=2)]
    candidate = [make_skill("Python")]

    score, _, _ = calculate_skill_score(requirements, candidate)

    assert score == 100.0


def test_missing_required_skill():
    requirements = [make_requirement("Python")]

    score, matched, missing = calculate_skill_score(
        requirements, []
    )

    assert score == 0.0
    assert matched == []
    assert missing == ["Python"]


def test_preferred_skill_has_lower_weight():
    requirements = [
        make_requirement("Python", weight=1.0),
        make_requirement("Docker", weight=0.5, req_type="preferred"),
    ]

    candidate = [make_skill("Python")]

    score, _, missing = calculate_skill_score(
        requirements, candidate
    )

    assert round(score, 2) == 66.67
    assert missing == ["Docker"]


def test_embedding_similarity():
    job = "Python developer with machine learning experience."
    relevant = "Software engineer skilled in Python and ML."
    unrelated = "Frontend developer skilled in React and CSS."

    relevant_score = semantic_similarity(job, relevant)
    unrelated_score = semantic_similarity(job, unrelated)

    assert 0 <= relevant_score <= 100
    assert 0 <= unrelated_score <= 100
    assert relevant_score > unrelated_score