import uuid
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import Optional

from app.storage.postgres import get_session
from app.services.submission import SubmissionService
from app.api.deps.auth import get_current_user_id
from app.api.deps.mq import get_mq_service, RabbitMQService
from app.models.submission import Submission, SubmissionRead, CorrectnessSource


router = APIRouter(prefix="/submissions", tags=["submissions"])


@router.post("/", response_model=Submission, status_code=status.HTTP_201_CREATED)
async def create_submission(
    task_id: str = Form(...),
    files: list[UploadFile] = File(...),
    language: str = Form("python"),
    correctness: Optional[int] = Form(None),
    correctness_source: Optional[CorrectnessSource] = Form(None),
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
    mq_service: RabbitMQService = Depends(get_mq_service),
):
    source_code: dict[str, str] = {}
    for file in files:
        if not file.filename:
            continue
        content = await file.read()
        try:
            source_code[file.filename] = content.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File {file.filename} is not a valid text file",
            )

    service = SubmissionService(session, mq_service=mq_service)
    return await service.create_submission(
        user_id=user_id,
        task_id=task_id,
        source_code=source_code,
        language=language,
        correctness=correctness,
        correctness_source=correctness_source,
    )


@router.get("/my", response_model=list[SubmissionRead])
async def get_my_submissions(
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    service = SubmissionService(session)
    return await service.get_user_submissions(user_id)


@router.get("/{submission_id}", response_model=Submission)
async def get_submission(
    submission_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    service = SubmissionService(session)
    return await service.get_submission(submission_id)
