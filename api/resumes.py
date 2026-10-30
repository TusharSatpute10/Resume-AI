from pathlib import Path
import uuid

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
)

from sqlalchemy.orm import Session

from constants.roles import UserRole
from core.dependencies import require_role
from db.database import get_db
from db.models.resume import Resume
from db.models.student import Student
from db.models.user import User

from schemas.resume import ResumeResponse, ResumeListItem

from services.resume_parser import extract_resume_content
from services.resume_ai_parser import parse_resume_with_ai
from services.resume_storage import store_parsed_resume


router = APIRouter(prefix="/resumes", tags=["Resumes"])

UPLOAD_DIR = Path("uploads/resumes")
ALLOWED_EXTENSIONS = {".pdf", ".docx"}


@router.post("/upload", response_model=ResumeResponse)
async def upload_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(
        require_role(UserRole.STUDENT.value)
    ),
    db: Session = Depends(get_db),
):
    # ---------------------------------------------------------
    # 1. Validate file type
    # ---------------------------------------------------------
    allowed_extensions = {".pdf", ".docx"}

    original_name = file.filename or ""
    extension = Path(original_name).suffix.lower()

    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail="Only PDF and DOCX files are supported",
        )

    # ---------------------------------------------------------
    # 2. Find the logged-in student's profile
    # ---------------------------------------------------------
    student = (
        db.query(Student)
        .filter(Student.user_id == current_user.id)
        .first()
    )

    if not student:
        raise HTTPException(
            status_code=404,
            detail="Student profile not found",
        )

    # ---------------------------------------------------------
    # 3. Generate unique file name
    # ---------------------------------------------------------
    unique_filename = (
        f"{uuid.uuid4().hex}{extension}"
    )

    upload_dir = Path("uploads/resumes")
    upload_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    file_path = upload_dir / unique_filename

    # ---------------------------------------------------------
    # 4. Save uploaded file
    # ---------------------------------------------------------
    content = await file.read()

    with open(file_path, "wb") as buffer:
        buffer.write(content)

    # ---------------------------------------------------------
    # 5. Create resume database record
    # ---------------------------------------------------------
    resume = Resume(
        student_id=student.id,
        file_name=original_name,
        file_path=str(file_path),
        is_primary=False,
    )

    db.add(resume)
    db.flush()

    # ---------------------------------------------------------
    # 6. Extract resume text + hyperlinks
    # ---------------------------------------------------------
    try:
        print("STEP 1: Starting resume text extraction...")

        extracted_content = extract_resume_content(
            str(file_path)
        )

        print("STEP 1: Resume text extraction completed.")

        resume_text = extracted_content["text"]
        extracted_urls = extracted_content["urls"]

    except Exception as exc:
        db.rollback()

        if file_path.exists():
            file_path.unlink()

        raise HTTPException(
            status_code=400,
            detail=f"Resume extraction failed: {exc}",
        )

    if not resume_text.strip():
        db.rollback()

        if file_path.exists():
            file_path.unlink()

        raise HTTPException(
            status_code=400,
            detail="Could not extract text from the resume",
        )

    # ---------------------------------------------------------
    # 7. Store raw extracted text
    # ---------------------------------------------------------
    resume.raw_text = resume_text

    # ---------------------------------------------------------
    # 8. Send resume to AI parser
    # ---------------------------------------------------------
    urls_text = "\n".join(extracted_urls)

    ai_input = f"""
RESUME TEXT:
--------------------
{resume_text}
--------------------

EXTRACTED HYPERLINKS:
--------------------
{urls_text}
--------------------
"""

    try:
        print("STEP 2: Sending resume to Mistral...")

        parsed_data = parse_resume_with_ai(
            ai_input
        )

        print("STEP 2: Mistral parsing completed.")
        print("AI parsed keys:", list(parsed_data.keys()))

    except Exception as exc:
        import traceback

        print("\n========== AI PARSER ERROR ==========")
        print(str(exc))
        traceback.print_exc()
        print("=====================================\n")

        db.rollback()

        if file_path.exists():
            file_path.unlink()

        raise HTTPException(
            status_code=500,
            detail=f"AI resume parsing failed: {exc}",
        )

    # ---------------------------------------------------------
    # 9. Store AI-parsed information
    # ---------------------------------------------------------
    try:
        print("STEP 3: Storing parsed resume in PostgreSQL...")

        resume = store_parsed_resume(
            db=db,
            resume=resume,
            parsed_data=parsed_data,
        )

    except Exception as exc:
        import traceback

        print("\n========== STORAGE ERROR ==========")
        print(str(exc))
        traceback.print_exc()
        print("===================================\n")

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Failed to store parsed resume: {exc}",
        )

        print("STEP 3: PostgreSQL storage completed.")

    # ---------------------------------------------------------
    # 10. Automatically make first resume primary
    # ---------------------------------------------------------
    existing_primary = (
        db.query(Resume)
        .filter(
            Resume.student_id == student.id,
            Resume.is_primary.is_(True),
            Resume.id != resume.id,
        )
        .first()
    )

    if not existing_primary:
        resume.is_primary = True
        db.commit()
        db.refresh(resume)

    return resume

@router.get(
    "/me",
    response_model=list[ResumeListItem],
)
def get_my_resumes(
    current_user: User = Depends(require_role(UserRole.STUDENT.value)),
    db: Session = Depends(get_db),
):
    student = (
        db.query(Student)
        .filter(Student.user_id == current_user.id)
        .first()
    )

    if not student:
        raise HTTPException(
            status_code=404,
            detail="Student profile not found",
        )

    resumes = (
        db.query(Resume)
        .filter(Resume.student_id == student.id)
        .order_by(Resume.created_at.desc())
        .all()
    )

    return resumes

@router.patch(
    "/{resume_id}/primary",
    response_model=ResumeResponse,
)
def set_primary_resume(
    resume_id: int,
    current_user: User = Depends(
        require_role(UserRole.STUDENT.value)
    ),
    db: Session = Depends(get_db),
):
    # 1. Find the logged-in student's profile
    student = (
        db.query(Student)
        .filter(Student.user_id == current_user.id)
        .first()
    )

    if not student:
        raise HTTPException(
            status_code=404,
            detail="Student profile not found",
        )

    # 2. Find the resume and verify ownership
    resume = (
        db.query(Resume)
        .filter(
            Resume.id == resume_id,
            Resume.student_id == student.id,
        )
        .first()
    )

    if not resume:
        raise HTTPException(
            status_code=404,
            detail="Resume not found",
        )

    # 3. Update the primary resume inside a transaction
    try:
        # Remove primary status from other resumes
        db.query(Resume).filter(
            Resume.student_id == student.id,
            Resume.id != resume.id,
        ).update(
            {Resume.is_primary: False},
            synchronize_session=False,
        )

        # Set the selected resume as primary
        resume.is_primary = True

        db.commit()
        db.refresh(resume)

    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Failed to update primary resume",
        )

    # 4. Return the updated resume
    return resume

@router.get(
    "/{resume_id}",
    response_model=ResumeResponse,
)
def get_resume(
    resume_id: int,
    current_user: User = Depends(
        require_role(UserRole.STUDENT.value)
    ),
    db: Session = Depends(get_db),
):
    student = (
        db.query(Student)
        .filter(Student.user_id == current_user.id)
        .first()
    )

    if not student:
        raise HTTPException(
            status_code=404,
            detail="Student profile not found",
        )

    resume = (
        db.query(Resume)
        .filter(
            Resume.id == resume_id,
            Resume.student_id == student.id,
        )
        .first()
    )

    if not resume:
        raise HTTPException(
            status_code=404,
            detail="Resume not found",
        )

    return resume

@router.delete("/{resume_id}")
def delete_resume(
    resume_id: int,
    current_user: User = Depends(
        require_role(UserRole.STUDENT.value)
    ),
    db: Session = Depends(get_db),
):
    student = (
        db.query(Student)
        .filter(Student.user_id == current_user.id)
        .first()
    )

    if not student:
        raise HTTPException(
            status_code=404,
            detail="Student profile not found",
        )

    resume = (
        db.query(Resume)
        .filter(
            Resume.id == resume_id,
            Resume.student_id == student.id,
        )
        .first()
    )

    if not resume:
        raise HTTPException(
            status_code=404,
            detail="Resume not found",
        )

    # Do not delete a resume that is referenced by applications.
    if resume.applications:
        raise HTTPException(
            status_code=409,
            detail=(
                "This resume is associated with applications "
                "and cannot be deleted."
            ),
        )

    file_path = Path(resume.file_path)

    try:
        # SQLAlchemy relationship cascades delete the associated
        # parsed resume data configured on the Resume model.
        db.delete(resume)
        db.commit()

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to delete resume",
        )

    # Remove the physical file only after the database commit.
    try:
        if file_path.is_file():
            file_path.unlink()
    except OSError:
        # The database record is already deleted. A leftover file
        # can be cleaned up separately.
        pass

    return {
        "message": "Resume deleted successfully",
        "resume_id": resume_id,
    }
