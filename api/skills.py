from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from db.database import get_db
from db.models.skill import Skill
from schemas.skill import SkillCreate, SkillResponse, SkillUpdate


router = APIRouter(prefix="/skills", tags=["Skills"])


@router.post(
    "",
    response_model=SkillResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_skill(
    payload: SkillCreate,
    db: Session = Depends(get_db),
):
    name = payload.name.strip()

    if not name:
        raise HTTPException(
            status_code=422,
            detail="Skill name cannot be empty.",
        )

    existing = (
        db.query(Skill)
        .filter(Skill.name.ilike(name))
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=409,
            detail="A skill with this name already exists.",
        )

    skill = Skill(
        name=name,
        category=payload.category.strip() if payload.category else None,
    )

    db.add(skill)

    try:
        db.commit()
        db.refresh(skill)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A skill with this name already exists.",
        )

    return skill


@router.get("", response_model=list[SkillResponse])
def list_skills(
    db: Session = Depends(get_db),
):
    return db.query(Skill).order_by(Skill.name.asc()).all()


@router.get("/{skill_id}", response_model=SkillResponse)
def get_skill(
    skill_id: int,
    db: Session = Depends(get_db),
):
    skill = db.query(Skill).filter(Skill.id == skill_id).first()

    if not skill:
        raise HTTPException(
            status_code=404,
            detail="Skill not found.",
        )

    return skill


@router.patch("/{skill_id}", response_model=SkillResponse)
def update_skill(
    skill_id: int,
    payload: SkillUpdate,
    db: Session = Depends(get_db),
):
    skill = db.query(Skill).filter(Skill.id == skill_id).first()

    if not skill:
        raise HTTPException(
            status_code=404,
            detail="Skill not found.",
        )

    updates = payload.model_dump(exclude_unset=True)

    if not updates:
        raise HTTPException(
            status_code=400,
            detail="Provide at least one field to update.",
        )

    if "name" in updates:
        name = updates["name"]

        if name is None or not name.strip():
            raise HTTPException(
                status_code=422,
                detail="Skill name cannot be empty.",
            )

        name = name.strip()

        duplicate = (
            db.query(Skill)
            .filter(
                Skill.name.ilike(name),
                Skill.id != skill_id,
            )
            .first()
        )

        if duplicate:
            raise HTTPException(
                status_code=409,
                detail="Another skill with this name already exists.",
            )

        updates["name"] = name

    if "category" in updates and updates["category"] is not None:
        updates["category"] = updates["category"].strip() or None

    for field, value in updates.items():
        setattr(skill, field, value)

    try:
        db.commit()
        db.refresh(skill)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="The skill could not be updated because of a database conflict.",
        )

    return skill


@router.delete("/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_skill(
    skill_id: int,
    db: Session = Depends(get_db),
):
    skill = db.query(Skill).filter(Skill.id == skill_id).first()

    if not skill:
        raise HTTPException(
            status_code=404,
            detail="Skill not found.",
        )

    if skill.resume_skills or skill.job_skills:
        raise HTTPException(
            status_code=409,
            detail=(
                "This skill is assigned to resumes or jobs. "
                "Remove its associations before deleting it."
            ),
        )

    db.delete(skill)
    db.commit()
    return None