import uuid
from fasthtml.common import *
from fastapi import HTTPException
from fastapi.responses import RedirectResponse

from app.base import rt
from app.services.user import UserService
from app.services.auth import AuthService
from app.storage.postgres import async_session_maker
from app.models.user import UserRole
from app.frontend.deps.auth import require_roles
from app.frontend.shared import render_header


@rt("/register", methods=["GET"])
async def get_register(session):
    header = await render_header(session, [("Регистрация", "/register")])

    validation_script = """
    function validatePassword() {
        const pwd = document.getElementById('password').value;
        const btn = document.getElementById('reg-btn');
        const reqList = document.getElementById('password-requirements');
        
        if (pwd.length > 0) {
            reqList.style.display = 'block';
        } else {
            reqList.style.display = 'none';
        }
        
        const reqs = {
            len: pwd.length >= 8,
            low: /[a-z]/.test(pwd),
            up: /[A-Z]/.test(pwd),
            spec: /[\\d\\W_]/.test(pwd)
        };
        
        document.getElementById('req-len').style.color = reqs.len ? '#28a745' : '#dc3545';
        document.getElementById('req-low').style.color = reqs.low ? '#28a745' : '#dc3545';
        document.getElementById('req-up').style.color = reqs.up ? '#28a745' : '#dc3545';
        document.getElementById('req-spec').style.color = reqs.spec ? '#28a745' : '#dc3545';
        
        btn.disabled = !(reqs.len && reqs.low && reqs.up && reqs.spec);
    }
    """

    return (
        Title("Регистрация"),
        header,
        Main(
            Div(
                H1("Регистрация"),
                Form(
                    Input(
                        name="email", placeholder="Email", required=True, type="email"
                    ),
                    Input(
                        type="password",
                        name="password",
                        id="password",
                        placeholder="Пароль",
                        required=True,
                        oninput="validatePassword()",
                    ),
                    Div(
                        Ul(
                            Li("Минимум 8 символов", id="req-len"),
                            Li("Хотя бы одна строчная буква (a-z)", id="req-low"),
                            Li("Хотя бы одна заглавная буква (A-Z)", id="req-up"),
                            Li("Цифра или спец. символ (@, #, 1...)", id="req-spec"),
                            style="font-size: 0.8em; color: #dc3545; list-style-type: none; padding-left: 0;",
                        ),
                        id="password-requirements",
                        style="display: none; margin-bottom: 15px;",
                    ),
                    Input(name="full_name", placeholder="Полное имя", required=True),
                    Button(
                        "Зарегистрироваться",
                        type="submit",
                        id="reg-btn",
                        disabled=True,
                        _class="btn-custom btn-primary",
                    ),
                    method="post",
                    action="/register",
                ),
                A("Уже есть аккаунт? Войти", href="/login"),
                Script(NotStr(validation_script)),
                _class="container",
            ),
        ),
    )


@rt("/register", methods=["POST"])
async def post_register(session, email: str, password: str, full_name: str):
    async with async_session_maker() as db_session:
        user_service = UserService(db_session)
        try:
            user = await user_service.register_user(
                email=email, password=password, full_name=full_name
            )
            return RedirectResponse("/login", status_code=303)
        except HTTPException as e:
            header = await render_header(session, [("Регистрация", "/register")])
            return (
                Title("Ошибка регистрации"),
                header,
                Main(
                    Div(
                        Div(P(e.detail), A("Назад", href="/register")),
                        _class="container",
                    ),
                ),
            )
        except Exception as e:
            header = await render_header(session, [("Регистрация", "/register")])
            return (
                Title("Ошибка"),
                header,
                Main(
                    Div(
                        Div(
                            P("Произошла непредвиденная ошибка"),
                            A("Назад", href="/register"),
                        ),
                        _class="container",
                    ),
                ),
            )


@rt("/login", methods=["GET"])
async def get_login(session):
    header = await render_header(session, [("Вход", "/login")])
    return (
        Title("Вход"),
        header,
        Main(
            Div(
                H1("Вход"),
                Form(
                    Input(name="email", placeholder="Email", required=True),
                    Input(
                        type="password",
                        name="password",
                        placeholder="Пароль",
                        required=True,
                    ),
                    Button("Войти", type="submit"),
                    method="post",
                    action="/login",
                ),
                A("Нет аккаунта? Зарегистрироваться", href="/register"),
                _class="container",
            ),
        ),
    )


@rt("/login", methods=["POST"])
async def post_login(session, email: str, password: str):
    async with async_session_maker() as db_session:
        user_service = UserService(db_session)
        try:
            token = await user_service.authenticate_user(
                email=email, password=password, expires_in=30.0
            )
            payload = AuthService.decode_token(token)
            session["user_id"] = payload["sub"]
            session["role"] = payload["role"]
            return RedirectResponse("/me", status_code=303)
        except HTTPException as e:
            header = await render_header(session, [("Вход", "/login")])
            return (
                Title("Ошибка входа"),
                header,
                Main(
                    Div(
                        Div(P(e.detail), A("Назад", href="/login")), _class="container"
                    ),
                ),
            )


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
                group = await user_service.get_study_group(user.group_id)
                group_name = group.name if group else "Неизвестная группа"

            header = await render_header(session, breadcrumbs=[("Профиль", "/me")])
            return (
                Title("Профиль"),
                header,
                Main(
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
                            Button("Сохранить", _class="btn-custom btn-primary"),
                            method="post",
                            action="/me",
                        ),
                        Div(id="modal-container"),
                    ),
                    _class="container",
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
        role = session.get("role")
        header = await render_header(
            session, breadcrumbs=[("Администрирование", "/groups")]
        )

        admin_section = ""
        if role == UserRole.admin.value:
            teachers = await user_service.get_users_by_role(UserRole.teacher)
            teacher_rows = [
                Tr(
                    Td(t.full_name),
                    Td(t.email),
                    Td(
                        Button(
                            "Понизить до студента",
                            hx_post=f"/users/{t.id}/demote",
                            hx_target="/groups",
                            hx_select="main",
                            hx_swap="outerHTML",
                            _class="btn-custom btn-danger",
                        )
                    ),
                )
                for t in teachers
            ]

            admin_section = Div(
                H3("Управление правами доступа"),
                H4("Список преподавателей"),
                Div(
                    Table(
                        Thead(Tr(Th("Имя"), Th("Email"), Th("Действие"))),
                        Tbody(*teacher_rows),
                        _class="custom-table",
                    ),
                    _class="custom-table-container",
                    style="margin-bottom: 20px;",
                ),
                Hr(),
                H4("Повысить студента до уровня преподавателя (по email):"),
                Form(
                    Input(
                        name="email",
                        placeholder="email@university.edu",
                        required=True,
                        type="email",
                    ),
                    Button(
                        "Повысить до преподавателя", _class="btn-custom btn-primary"
                    ),
                    method="post",
                    action="/users/promote",
                ),
                style="margin-top: 40px; padding: 20px; border: 1px solid #eee; border-radius: 8px; background: #fafafa;",
            )

        return (
            Title("Группы"),
            header,
            Main(
                Div(
                    H1("Группы"),
                    (
                        Ul(
                            *[
                                Li(A(f"{g.name}", href=f"/groups/{g.id}"))
                                for g in groups
                            ]
                        )
                        if groups
                        else P("Групп пока нет.")
                    ),
                    Hr(),
                    H3("Создать группу"),
                    Form(
                        Input(
                            name="name", placeholder="Название группы", required=True
                        ),
                        Button("Создать", _class="btn-custom btn-primary"),
                        method="post",
                        action="/groups",
                    ),
                    admin_section,
                    Div(id="modal-container"),
                ),
                _class="container",
            ),
        )


@rt("/users/{user_id}/demote", methods=["POST"])
async def demote_user(session, user_id: str):
    require_roles(session, [UserRole.admin.value])
    async with async_session_maker() as db_session:
        user_service = UserService(db_session)
        try:
            await user_service.demote_to_student(user_id=uuid.UUID(user_id))
            return RedirectResponse("/groups", status_code=303)
        except HTTPException as e:
            return Titled("Ошибка", Div(P(e.detail), A("Назад", href="/groups")))


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


@rt("/groups/{group_id}", methods=["GET"])
async def get_group_detail(session, group_id: str):
    require_roles(session, [UserRole.teacher.value, UserRole.admin.value])
    gid = uuid.UUID(group_id)
    async with async_session_maker() as db_session:
        user_service = UserService(db_session)
        group = await user_service.get_study_group(gid)
        users = await user_service.get_group_users(gid)

        user_rows = [
            Tr(
                Td(u.full_name),
                Td(u.email),
                Td(
                    Button(
                        "Удалить из группы",
                        hx_post=f"/groups/{gid}/remove/{u.id}",
                        hx_target="closest tr",
                        hx_swap="outerHTML",
                        _class="btn-custom btn-danger",
                    )
                ),
            )
            for u in users
        ]

        header = await render_header(
            session,
            breadcrumbs=[
                ("Администрирование", "/groups"),
                (group.name, f"/groups/{gid}"),
            ],
        )
        return (
            Title(f"Группа: {group.name}"),
            header,
            Main(
                Div(
                    H1(f"Группа: {group.name}"),
                    H3("Участники"),
                    Div(
                        Table(
                            Thead(Tr(Th("Имя"), Th("Email"), Th("Действие"))),
                            Tbody(*user_rows),
                            _class="custom-table",
                        ),
                        _class="custom-table-container",
                    ),
                    Hr(),
                    H4("Пригласить студента (по email)"),
                    Form(
                        Input(
                            name="email", placeholder="Email студента", required=True
                        ),
                        Button("Пригласить", _class="btn-custom btn-primary"),
                        method="post",
                        action=f"/groups/{gid}/invite",
                    ),
                    Div(id="modal-container"),
                ),
                _class="container",
            ),
        )


@rt("/groups/{group_id}/invite", methods=["POST"])
async def post_invite_to_group(session, group_id: str, email: str):
    require_roles(session, [UserRole.teacher.value, UserRole.admin.value])
    gid = uuid.UUID(group_id)
    async with async_session_maker() as db_session:
        user_service = UserService(db_session)
        try:
            user = await user_service.get_user_by_email(email)
            await user_service.add_user_to_group(user.id, gid)
            return RedirectResponse(f"/groups/{group_id}", status_code=303)
        except HTTPException as e:
            return Titled(
                "Ошибка", Div(P(e.detail), A("Назад", href=f"/groups/{group_id}"))
            )


@rt("/groups/{group_id}/remove/{user_id}", methods=["POST"])
async def post_remove_from_group(session, group_id: str, user_id: str):
    require_roles(session, [UserRole.teacher.value, UserRole.admin.value])
    uid = uuid.UUID(user_id)
    async with async_session_maker() as db_session:
        user_service = UserService(db_session)
        await user_service.remove_user_from_group(uid)
        return ""  # HTMX target swap


@rt("/users/promote", methods=["POST"])
async def promote_user_by_email(session, email: str):
    require_roles(session, [UserRole.admin.value])
    async with async_session_maker() as db_session:
        user_service = UserService(db_session)
        try:
            user = await user_service.get_user_by_email(email)
            await user_service.promote_to_teacher(user_id=user.id)
            return RedirectResponse("/groups", status_code=303)
        except HTTPException as e:
            return Titled("Ошибка", Div(P(e.detail), A("Назад", href="/groups")))


@rt("/users/{target_user_id}/promote", methods=["POST"])
async def promote_user(session, target_user_id: str):
    require_roles(session, [UserRole.admin.value])
    async with async_session_maker() as db_session:
        user_service = UserService(db_session)
        try:
            await user_service.promote_to_teacher(user_id=uuid.UUID(target_user_id))
            return RedirectResponse("/groups", status_code=303)
        except HTTPException as e:
            return Titled("Ошибка", Div(P(e.detail), A("Назад", href="/me")))
