import uuid
from typing import Optional
from fasthtml.common import *
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.base import rt

from app.services.course import CourseService
from app.services.task import TaskService
from app.storage.postgres import async_session_maker
from app.models.user import UserRole, User
from app.models.group import StudyGroup
from app.frontend.deps.auth import require_roles
from app.frontend.shared import (
    render_header,
    render_modal,
    render_card,
    render_add_card,
    render_emoji_select,
)
from app.utils.emojis import get_all_course_emojis


@rt("/courses/modal", methods=["GET"])
async def get_create_course_modal(session):
    require_roles(session, [UserRole.teacher.value, UserRole.admin.value])
    form_content = Form(
        Label(
            "Название курса",
            Input(name="name", placeholder="Название курса", required=True),
        ),
        Label("Эмоджи", render_emoji_select(None, get_all_course_emojis())),
        Label("Описание", Input(name="description", placeholder="Описание")),
        Button("Создать", _class="btn-custom btn-primary"),
        method="post",
        action="/courses",
    )
    return render_modal("Создать новый курс", form_content, "create-course-modal")


@rt("/courses", methods=["GET"])
async def get_courses_list(session):
    require_roles(
        session, [UserRole.student.value, UserRole.teacher.value, UserRole.admin.value]
    )
    user_id = uuid.UUID(session["user_id"])
    role = session["role"]

    async with async_session_maker() as db_session:
        course_service = CourseService(db_session)
        if role in (UserRole.teacher.value, UserRole.admin.value):
            courses = await course_service.get_teacher_courses(user_id)
        else:
            statement = (
                select(User)
                .options(selectinload(User.courses))
                .where(User.id == user_id)
            )
            result = await db_session.execute(statement)
            user = result.scalars().first()
            courses = user.courses if user else []

        course_cards = [
            render_card(c.name, c.emoji or "📚", f"/courses/{c.id}", c.description)
            for c in courses
        ]

        if role in (UserRole.teacher.value, UserRole.admin.value):
            course_cards.append(render_add_card("/courses/modal"))

        content = [
            H1("Мои курсы", style="text-align: center;"),
            (
                Div(*course_cards, _class="card-grid")
                if course_cards
                else P("Курсов пока нет.")
            ),
        ]

        content.append(Div(id="modal-container"))

        header = await render_header(session, [("Мои курсы", "/courses")])
        return Title("Мои курсы"), header, Main(*content, _class="container")


@rt("/courses", methods=["POST"])
async def post_create_course(
    session, name: str, description: str = "", emoji: Optional[str] = None
):
    require_roles(session, [UserRole.teacher.value, UserRole.admin.value])
    user_id = uuid.UUID(session["user_id"])
    async with async_session_maker() as db_session:
        await CourseService(db_session).create_course(
            name=name, teacher_id=user_id, description=description, emoji=emoji
        )
        return RedirectResponse("/courses", status_code=303)


@rt("/courses/{course_id}/edit/modal", methods=["GET"])
async def get_edit_course_modal(session, course_id: str):
    require_roles(session, [UserRole.teacher.value, UserRole.admin.value])
    cid = uuid.UUID(course_id)
    async with async_session_maker() as db_session:
        course = await CourseService(db_session).get_course(cid)
        form_content = Form(
            Label(
                "Название курса", Input(name="name", value=course.name, required=True)
            ),
            Label("Эмоджи", render_emoji_select(course.emoji, get_all_course_emojis())),
            Label(
                "Описание",
                Textarea(course.description or "", name="description", rows="5"),
            ),
            Button("Сохранить", _class="btn-custom btn-primary"),
            method="post",
            action=f"/courses/{course_id}/edit",
        )
        return render_modal("Редактировать курс", form_content, "edit-course-modal")


@rt("/courses/{course_id}/edit", methods=["POST"])
async def post_edit_course(
    session,
    course_id: str,
    name: str,
    description: str,
    emoji: Optional[str] = "🦄",
):
    require_roles(session, [UserRole.teacher.value, UserRole.admin.value])
    cid = uuid.UUID(course_id)
    async with async_session_maker() as db_session:
        await CourseService(db_session).update_course(
            cid, name=name, description=description, emoji=emoji
        )
        return RedirectResponse(f"/courses/{cid}", status_code=303)


@rt("/courses/{course_id}/add-user/modal", methods=["GET"])
async def get_add_user_modal(session, course_id: str):
    require_roles(session, [UserRole.teacher.value, UserRole.admin.value])
    form_content = Form(
        Input(name="email", placeholder="Email студента", required=True, type="email"),
        Button("Добавить", _class="btn-custom btn-primary"),
        method="post",
        action=f"/courses/{course_id}/add-user",
    )
    return render_modal("Добавить студента", form_content, "add-user-modal")


@rt("/courses/{course_id}/add-group/modal", methods=["GET"])
async def get_add_group_modal(session, course_id: str):
    require_roles(session, [UserRole.teacher.value, UserRole.admin.value])
    async with async_session_maker() as db_session:
        groups_result = await db_session.execute(select(StudyGroup))
        groups = groups_result.scalars().all()
        group_options = [Option(g.name, value=str(g.id)) for g in groups]
        form_content = Form(
            Select(*group_options, name="group_id", required=True),
            Button("Добавить группу", _class="btn-custom btn-primary"),
            method="post",
            action=f"/courses/{course_id}/add-group",
        )
        return render_modal("Добавить учебную группу", form_content, "add-group-modal")


@rt("/courses/{course_id}/add-user", methods=["POST"])
async def post_add_user_to_course(session, course_id: str, email: str):
    require_roles(session, [UserRole.teacher.value, UserRole.admin.value])
    cid = uuid.UUID(course_id)
    async with async_session_maker() as db_session:
        result = await db_session.execute(select(User).where(User.email == email))
        user = result.scalars().first()
        if not user:
            return Titled(
                "Ошибка",
                P(f"Пользователь с email {email} не найден"),
                A("Назад", href=f"/courses/{cid}"),
            )
        await CourseService(db_session).add_user_to_course(cid, user.id)
        return RedirectResponse(f"/courses/{cid}", status_code=303)


@rt("/courses/{course_id}/add-group", methods=["POST"])
async def post_add_group_to_course(session, course_id: str, group_id: str):
    require_roles(session, [UserRole.teacher.value, UserRole.admin.value])
    cid = uuid.UUID(course_id)
    gid = uuid.UUID(group_id)
    async with async_session_maker() as db_session:
        await CourseService(db_session).add_group_to_course(cid, gid)
        return RedirectResponse(f"/courses/{cid}", status_code=303)


@rt("/courses/{course_id}", methods=["GET"])
async def get_course_detail(session, course_id: str):
    require_roles(
        session, [UserRole.student.value, UserRole.teacher.value, UserRole.admin.value]
    )
    cid = uuid.UUID(course_id)
    user_id = uuid.UUID(session["user_id"])
    role = session["role"]

    async with async_session_maker() as db_session:
        course_service = CourseService(db_session)
        task_service = TaskService(db_session)

        course = await course_service.get_course(cid)
        users = await course_service.get_course_users(cid)
        task_groups = await task_service.get_course_task_groups(cid)

        if role == UserRole.student.value:
            enrolled = any(u.id == user_id for u in users)
            if not enrolled:
                return Titled(
                    "Доступ запрещен",
                    P("Вы не записаны на этот курс"),
                    A("Назад", href="/courses"),
                )

        # Заголовок с кнопкой редактирования курса
        course_title_elements = []
        if course.emoji:
            course_title_elements.append(Span(f"{course.emoji} "))
        course_title_elements.append(Span(f"Курс: {course.name}"))

        if role in (UserRole.teacher.value, UserRole.admin.value):
            course_title_elements.append(
                A(
                    "✏️",
                    hx_get=f"/courses/{cid}/edit/modal",
                    hx_target="#modal-container",
                    style="text-decoration: none; cursor: pointer; font-size: 0.6em; margin-left: 8px;",
                    title="Редактировать курс",
                )
            )
            course_title_elements.append(
                A(
                    "⚙️",
                    href=f"/courses/{cid}/settings",
                    style="text-decoration: none; cursor: pointer; font-size: 0.6em; margin-left: 8px;",
                    title="Настройки анализа",
                )
            )

        # Секция лабораторных работ с кнопкой добавления
        lab_header_elements = [Span("Лабораторные работы")]

        content = [
            P(f"Описание: {course.description or 'Нет описания'}"),
            Hr(),
            H3(*lab_header_elements),
        ]

        if not task_groups:
            if role in (UserRole.teacher.value, UserRole.admin.value):
                content.append(
                    Div(
                        render_add_card(f"/courses/{cid}/labs/modal"),
                        _class="card-grid",
                    )
                )
            else:
                content.append(P("Лабораторных работ пока нет."))
        else:
            lab_cards = [
                render_card(
                    tg.name,
                    tg.emoji or "🧪",
                    f"/courses/{cid}/labs/{tg.id}",
                    tg.description,
                )
                for tg in task_groups
            ]
            if role in (UserRole.teacher.value, UserRole.admin.value):
                lab_cards.append(render_add_card(f"/courses/{cid}/labs/modal"))
            content.append(Div(*lab_cards, _class="card-grid"))

        if role in (UserRole.teacher.value, UserRole.admin.value):
            content.extend(
                [
                    Hr(),
                    H3("Участники курса"),
                ]
            )

            user_rows = [
                Tr(
                    Td(u.full_name),
                    Td(u.email),
                    Td(
                        Button(
                            "Удалить",
                            hx_post=f"/courses/{cid}/remove-user/{u.id}",
                            hx_target="closest tr",
                            hx_swap="outerHTML",
                            _class="btn-custom btn-danger",
                        )
                    ),
                )
                for u in users
            ]

            content.append(
                Div(
                    Table(
                        Thead(Tr(Th("Имя"), Th("Email"), Th("Действие"))),
                        Tbody(*user_rows),
                        _class="custom-table",
                    ),
                    _class="custom-table-container",
                )
            )

            content.extend(
                [
                    Div(
                        Button(
                            "Добавить студента",
                            hx_get=f"/courses/{cid}/add-user/modal",
                            hx_target="#modal-container",
                            _class="btn-custom btn-primary",
                        ),
                        Button(
                            "Добавить группу",
                            hx_get=f"/courses/{cid}/add-group/modal",
                            hx_target="#modal-container",
                            _class="btn-custom btn-primary",
                            style="margin-left: 10px;",
                        ),
                        style="margin-top: 20px;",
                    ),
                ]
            )
        else:
            content.append(Hr())
            content.append(H3("Преподаватель"))
            teacher = await db_session.get(User, course.teacher_id)
            content.append(P(teacher.full_name if teacher else "Неизвестен"))

        # Modal target
        content.append(Div(id="modal-container"))

        header = await render_header(
            session,
            breadcrumbs=[
                ("Мои курсы", "/courses"),
                (course.name_with_emoji, f"/courses/{cid}"),
            ],
        )
        return (
            Title(f"Курс: {course.name}"),
            header,
            Main(H1(Span(*course_title_elements)), Div(*content), _class="container"),
        )
