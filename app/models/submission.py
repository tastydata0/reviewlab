import uuid
import datetime as dt
from enum import Enum
from typing import Optional
from sqlmodel import SQLModel, Field, JSON


class SubmissionStatus(str, Enum):
    CREATED = "CREATED"
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"


class PlagiarismVerdict(str, Enum):
    UNSET = "UNSET"
    DECLINED = "DECLINED"
    CONFIRMED = "CONFIRMED"


class CorrectnessSource(str, Enum):
    MANUAL = "MANUAL"
    AI = "AI"
    EXTERNAL_TESTING_SYSTEM = "EXTERNAL_TESTING_SYSTEM"  # cf, acmp


class SubmissionBase(SQLModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", index=True)
    task_id: str = Field(index=True)  # JOIN_CODE
    timestamp: dt.datetime = Field(default_factory=dt.datetime.now)
    source_code: dict[str, str] = Field(
        default_factory=dict, sa_type=JSON
    )  # filename -> content
    language: str = Field(default="python")
    correctness: Optional[int] = Field(None, ge=0, le=100)
    correctness_source: Optional[CorrectnessSource] = Field(default=None)

    status: SubmissionStatus = Field(default=SubmissionStatus.CREATED)
    metrics: Optional[dict] = Field(default=None, sa_type=JSON)
    linter_report: Optional[str] = Field(default=None)

    ai_review: Optional[str] = Field(default=None)
    ai_score: Optional[int] = Field(default=None)

    plagiarism_checked: bool = Field(default=False)
    lexical_similarity: float = Field(default=0.0)
    semantic_similarity: float = Field(default=0.0)
    plagiarism_score: float = Field(default=0.0)
    plagiarism_verdict: PlagiarismVerdict = Field(default=PlagiarismVerdict.UNSET)


class Submission(SubmissionBase, table=True):
    pass


class SubmissionRead(SubmissionBase):
    task_name: Optional[str] = None
    task_group_name: Optional[str] = None
