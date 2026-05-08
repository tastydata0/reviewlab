from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.settings import SETTINGS

# Убедимся, что модели зарегистрированы в SQLModel.metadata
if True:  # чтобы ruff и прочие не убрали
    from app.models.user import User  # noqa: F401
    from app.models.group import StudyGroup  # noqa: F401
    from app.models.submission import Submission  # noqa: F401
    from app.models.course import Course  # noqa: F401
    from app.models.links import CourseUserLink  # noqa: F401
    from app.models.task_group import TaskGroup  # noqa: F401
    from app.models.task import Task  # noqa: F401
    from app.models.task_stats import TaskPlagiarismStats  # noqa: F401


dsn = SETTINGS.POSTGRES_DSN.get_secret_value()
if dsn.startswith("postgresql://"):
    dsn = dsn.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(dsn, echo=False)
async_session_maker = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session


async def create_db_and_tables() -> None:
    async with engine.begin() as conn:
        # Расширение vector должно быть установлено до создания таблиц с типами Vector
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        await conn.run_sync(SQLModel.metadata.create_all)
