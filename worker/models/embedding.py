import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column
from sqlmodel import Field, SQLModel


class Embedding768(SQLModel, table=True):
    __tablename__ = "embedding_768"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    chunk_hash: str = Field(index=True)
    task_id: str = Field(default=None, index=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", index=True)
    submission_id: uuid.UUID = Field(foreign_key="submission.id", index=True)
    embedding: list[float] = Field(sa_column=Column(Vector(768)))


class Embedding1536(SQLModel, table=True):
    __tablename__ = "embedding_1536"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    chunk_hash: str = Field(index=True)
    task_id: str = Field(default=None, index=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", index=True)
    submission_id: uuid.UUID = Field(foreign_key="submission.id", index=True)
    embedding: list[float] = Field(sa_column=Column(Vector(1536)))
