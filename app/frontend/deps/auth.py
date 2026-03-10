from fasthtml.common import *
from starlette.exceptions import HTTPException


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
