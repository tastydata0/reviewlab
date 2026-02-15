import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column
from sqlmodel import Field, SQLModel


class Embedding768(SQLModel, table=True):
    __tablename__ = "embedding_768"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    embedding: list[float] = Field(sa_column=Column(Vector(768)))


class Embedding1536(SQLModel, table=True):
    __tablename__ = "embedding_1536"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    embedding: list[float] = Field(sa_column=Column(Vector(1536)))
