import uuid
from fasthtml.common import *
from fastapi import HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from app.base import rt
from app.services.user import UserService
from app.services.auth import AuthService
from app.storage.postgres import async_session_maker
from app.models.user import UserRole
from app.models.group import StudyGroup
from app.frontend.deps.auth import require_roles


@rt("/register", methods=["GET"])
def get_register():
    return Titled(
        "Регистрация",
        Form(
            Input(name="email", placeholder="Email", required=True),
            Input(
                type="password", name="password", placeholder="Пароль", required=True
            ),
            Input(name="full_name", placeholder="Полное имя", required=True),
            Button("Зарегистрироваться", type="submit"),
            method="post",
            action="/register",
        ),
        A("Уже есть аккаунт? Войти", href="/login"),
    )


@rt("/register", methods=["POST"])
async def post_register(email: str, password: str, full_name: str):
    print(f"DEBUG: Attempting to register user: {email}")
    async with async_session_maker() as db_session:
        user_service = UserService(db_session)
        try:
            user = await user_service.register_user(
                email=email, password=password, full_name=full_name
            )
            print(f"DEBUG: User created: {user.id}")
            return RedirectResponse("/login", status_code=303)
        except HTTPException as e:
            print(f"DEBUG: Registration error: {e.detail}")
            return Titled(
                "Ошибка регистрации", Div(P(e.detail), A("Назад", href="/register"))
            )
        except Exception as e:
            print(f"DEBUG: Unexpected error: {str(e)}")
            return Titled(
                "Ошибка",
                Div(P("Произошла непредвиденная ошибка"), A("Назад", href="/register")),
            )


@rt("/login", methods=["GET"])
def get_login():
    return Titled(
        "Вход",
        Form(
            Input(name="email", placeholder="Email", required=True),
            Input(
                type="password", name="password", placeholder="Пароль", required=True
            ),
            Button("Войти", type="submit"),
            method="post",
            action="/login",
        ),
        A("Нет аккаунта? Зарегистрироваться", href="/register"),
    )


@rt("/login", methods=["POST"])
async def post_login(session, email: str, password: str):
    print(f"DEBUG: Login attempt: {email}")
    async with async_session_maker() as db_session:
        user_service = UserService(db_session)
        try:
            token = await user_service.authenticate_user(
                email=email, password=password, expires_in=30.0
            )
            payload = AuthService.decode_token(token)
            session["user_id"] = payload["sub"]
            session["role"] = payload["role"]
            print(f"DEBUG: Login success for {email}")
            return RedirectResponse("/me", status_code=303)
        except HTTPException as e:
            print(f"DEBUG: Login fail: {e.detail}")
            return Titled("Ошибка входа", Div(P(e.detail), A("Назад", href="/login")))


@rt("/logout")
def logout(session):
    session.clear()
    return RedirectResponse("/", status_code=303)


@rt("/me", methods=["GET"])
async def get_me(session):
    require_roles(
        session, [UserRole.student.value, UserRole.teacher.value, UserRole.admin.value]
    )
    user_id = uuid.UUID(session["user_id"])
    async with async_session_maker() as db_session:
        user_service = UserService(db_session)
        try:
            user = await user_service.get_user_by_id(user_id)

            group_name = "Нет группы"
            if user.group_id:
                group = await db_session.get(StudyGroup, user.group_id)
                group_name = group.name if group else "Неизвестная группа"

            return Titled(
                "Профиль",
                Div(
                    P(f"Имя: {user.full_name}"),
                    P(f"Email: {user.email}"),
                    P(f"Роль: {user.role.value}"),
                    P(f"Группа: {group_name}"),
                    Hr(),
                    H3("Изменить данные"),
                    Form(
                        Input(name="full_name", value=user.full_name),
                        Input(name="email", value=user.email),
                        Button("Сохранить"),
                        method="post",
                        action="/me",
                    ),
                    Hr(),
                    (
                        A("Управление группами", href="/groups")
                        if user.role in (UserRole.teacher, UserRole.admin)
                        else ""
                    ),
                    Br(),
                    (
                        A("Управление курсами", href="/courses")
                        if user.role in (UserRole.teacher, UserRole.admin)
                        else ""
                    ),
                    Br(),
                    A("Выйти", href="/logout"),
                ),
            )
        except HTTPException:
            session.clear()
            return RedirectResponse("/login", status_code=303)


@rt("/me", methods=["POST"])
async def post_me(session, full_name: str, email: str):
    require_roles(
        session, [UserRole.student.value, UserRole.teacher.value, UserRole.admin.value]
    )
    user_id = uuid.UUID(session["user_id"])
    async with async_session_maker() as db_session:
        user_service = UserService(db_session)
        try:
            await user_service.update_user(
                user_id=user_id, full_name=full_name, email=email
            )
            return RedirectResponse("/me", status_code=303)
        except HTTPException as e:
            return Titled("Ошибка", Div(P(e.detail), A("Назад", href="/me")))


@rt("/groups", methods=["GET"])
async def get_groups(session):
    require_roles(session, [UserRole.teacher.value, UserRole.admin.value])
    async with async_session_maker() as db_session:
        user_service = UserService(db_session)
        groups = await user_service.get_all_study_groups()
        return Titled(
            "Группы",
            (
                Ul(*[Li(f"{g.name} (ID: {g.id})") for g in groups])
                if groups
                else P("Групп пока нет.")
            ),
            Hr(),
            H3("Создать группу"),
            Form(
                Input(name="name", placeholder="Название группы", required=True),
                Button("Создать"),
                method="post",
                action="/groups",
            ),
            A("Назад в профиль", href="/me"),
        )


@rt("/groups", methods=["POST"])
async def post_groups(session, name: str):
    require_roles(session, [UserRole.teacher.value, UserRole.admin.value])
    async with async_session_maker() as db_session:
        user_service = UserService(db_session)
        try:
            await user_service.create_study_group(name=name)
            return RedirectResponse("/groups", status_code=303)
        except HTTPException as e:
            return Titled("Ошибка", Div(P(e.detail), A("Назад", href="/groups")))


@rt("/users/{target_user_id}/group", methods=["POST"])
async def post_user_group(session, target_user_id: str, group_id: str):
    require_roles(session, [UserRole.teacher.value, UserRole.admin.value])
    async with async_session_maker() as db_session:
        user_service = UserService(db_session)
        try:
            await user_service.add_user_to_group(
                user_id=uuid.UUID(target_user_id), group_id=uuid.UUID(group_id)
            )
            return RedirectResponse("/me", status_code=303)
        except HTTPException as e:
            return Titled("Ошибка", Div(P(e.detail), A("Назад", href="/me")))


@rt("/users/{target_user_id}/promote", methods=["POST"])
async def promote_user(session, target_user_id: str):
    require_roles(session, [UserRole.admin.value])
    async with async_session_maker() as db_session:
        user_service = UserService(db_session)
        try:
            await user_service.promote_to_teacher(user_id=uuid.UUID(target_user_id))
            return RedirectResponse("/me", status_code=303)
        except HTTPException as e:
            return Titled("Ошибка", Div(P(e.detail), A("Назад", href="/me")))
