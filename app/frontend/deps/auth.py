import uuid
from fasthtml.common import *
from starlette.exceptions import HTTPException
from app.storage.postgres import async_session_maker
from app.services.course import CourseService

class AccessDenied(Exception):
    pass


def access_denied_handler(req, exc):
    return (
        Titled(
            "Доступ запрещен",
            Div(
                H1("Ошибка 403", style="color: red;"),
                P("У вас нет прав для выполнения этого действия."),
                A("Вернуться на главную", href="/"),
            ),
        ),
    )


def require_roles(session: dict, allowed_roles: list[str]):
    user_role = session.get("role")
    if not user_role or user_role not in allowed_roles:
        raise HTTPException(403, "Доступ запрещен")


async def require_course_access(session: dict, course_id: str):
    user_id = session.get("user_id")
    role = session.get("role")
    if not user_id or not role:
        raise HTTPException(401, "Необходима авторизация")
        
    async with async_session_maker() as db_session:
        await CourseService(db_session).check_course_access(uuid.UUID(course_id), uuid.UUID(user_id), role)
