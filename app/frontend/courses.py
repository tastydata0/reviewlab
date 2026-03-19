import uuid
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

        course_items = [
            Li(
                A(f"{c.name}", href=f"/courses/{c.id}"),
                f" - {c.description[:50] if c.description else ''}",
            )
            for c in courses
        ]

        content = [
            Titled("Мои курсы"),
            Ul(*course_items) if course_items else P("Курсов пока нет."),
        ]

        if role in (UserRole.teacher.value, UserRole.admin.value):
            content.extend(
                [
                    Hr(),
                    H3("Создать новый курс"),
                    Form(
                        Input(name="name", placeholder="Название курса", required=True),
                        Input(name="description", placeholder="Описание"),
                        Button("Создать"),
                        method="post",
                        action="/courses",
                    ),
                ]
            )

        content.append(Hr())
        content.append(A("Назад в профиль", href="/me"))
        return content


@rt("/courses", methods=["POST"])
async def post_create_course(session, name: str, description: str = ""):
    require_roles(session, [UserRole.teacher.value, UserRole.admin.value])
    user_id = uuid.UUID(session["user_id"])
    async with async_session_maker() as db_session:
        await CourseService(db_session).create_course(
            name=name, teacher_id=user_id, description=description
        )
        return RedirectResponse("/courses", status_code=303)


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

        content = [
            P(f"Описание: {course.description or 'Нет описания'}"),
            Hr(),
            H3("Лабораторные работы"),
        ]

        if not task_groups:
            content.append(P("Лабораторных работ пока нет."))
        else:
            lab_links = [
                Li(A(tg.name, href=f"/courses/{cid}/labs/{tg.id}"))
                for tg in task_groups
            ]
            content.append(Ul(*lab_links))

        if role in (UserRole.teacher.value, UserRole.admin.value):
            content.extend(
                [
                    Hr(),
                    H3("Создать лабораторную работу"),
                    Form(
                        Input(
                            name="name",
                            placeholder="Название лабы (например, ЛР №1)",
                            required=True,
                        ),
                        Input(name="description", placeholder="Описание"),
                        Button("Создать"),
                        method="post",
                        action=f"/courses/{cid}/labs",
                    ),
                    Hr(),
                    A("Редактировать курс", href=f"/courses/{cid}/edit"),
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
                        )
                    ),
                )
                for u in users
            ]

            content.append(
                Table(
                    Thead(Tr(Th("Имя"), Th("Email"), Th("Действие"))),
                    Tbody(*user_rows),
                    border="1",
                )
            )

            groups_result = await db_session.execute(select(StudyGroup))
            groups = groups_result.scalars().all()
            group_options = [Option(g.name, value=str(g.id)) for g in groups]

            content.extend(
                [
                    Hr(),
                    H4("Добавить студента (по email)"),
                    Form(
                        Input(
                            name="email", placeholder="Email студента", required=True
                        ),
                        Button("Добавить"),
                        method="post",
                        action=f"/courses/{cid}/add-user",
                    ),
                    Hr(),
                    H4("Добавить учебную группу"),
                    Form(
                        Select(*group_options, name="group_id", required=True),
                        Button("Добавить группу"),
                        method="post",
                        action=f"/courses/{cid}/add-group",
                    ),
                ]
            )
        else:
            content.append(Hr())
            content.append(H3("Преподаватель"))
            teacher = await db_session.get(User, course.teacher_id)
            content.append(P(teacher.full_name if teacher else "Неизвестен"))

        content.append(Hr())
        content.append(A("Назад к списку курсов", href="/courses"))

        return Titled(f"Курс: {course.name}", Div(*content))


@rt("/courses/{course_id}/labs/{lab_id}", methods=["GET"])
async def get_lab_detail(session, course_id: str, lab_id: str):
    require_roles(
        session, [UserRole.student.value, UserRole.teacher.value, UserRole.admin.value]
    )
    cid = uuid.UUID(course_id)
    lid = uuid.UUID(lab_id)
    role = session["role"]

    async with async_session_maker() as db_session:
        task_service = TaskService(db_session)
        lab = await task_service.get_task_group(lid)

        content = [
            P(f"Описание: {lab.description or 'Нет описания'}"),
            Hr(),
            H3("Задачи"),
        ]

        if not lab.tasks:
            content.append(P("Задач в этой лабораторной работе пока нет."))
        else:
            task_items = []
            for t in lab.tasks:
                task_items.append(
                    Li(
                        B(t.name),
                        P(t.description) if t.description else "",
                        P(f"Код для сдачи: ", Code(t.join_code)),
                    )
                )
            content.append(Ul(*task_items))

        if role in (UserRole.teacher.value, UserRole.admin.value):
            content.extend(
                [
                    Hr(),
                    H3("Добавить задачу"),
                    Form(
                        Input(
                            name="name", placeholder="Название задачи", required=True
                        ),
                        Textarea(
                            name="description",
                            placeholder="Содержание задачи (что нужно сделать)",
                            rows="5",
                        ),
                        Button("Создать задачу"),
                        method="post",
                        action=f"/courses/{cid}/labs/{lid}/tasks",
                    ),
                ]
            )

        content.append(Hr())
        content.append(A("Назад к курсу", href=f"/courses/{cid}"))

        return Titled(f"Лабораторная работа: {lab.name}", Div(*content))


@rt("/courses/{course_id}/labs", methods=["POST"])
async def post_create_lab(session, course_id: str, name: str, description: str = ""):
    require_roles(session, [UserRole.teacher.value, UserRole.admin.value])
    cid = uuid.UUID(course_id)
    async with async_session_maker() as db_session:
        await TaskService(db_session).create_task_group(cid, name, description)
        return RedirectResponse(f"/courses/{cid}", status_code=303)


@rt("/courses/{course_id}/labs/{lab_id}/tasks", methods=["POST"])
async def post_create_task(
    session, course_id: str, lab_id: str, name: str, description: str = ""
):
    require_roles(session, [UserRole.teacher.value, UserRole.admin.value])
    lid = uuid.UUID(lab_id)
    async with async_session_maker() as db_session:
        await TaskService(db_session).create_task(lid, name, description=description)
        return RedirectResponse(f"/courses/{course_id}/labs/{lab_id}", status_code=303)


@rt("/courses/{course_id}/edit", methods=["GET"])
async def get_edit_course(session, course_id: str):
    require_roles(session, [UserRole.teacher.value, UserRole.admin.value])
    cid = uuid.UUID(course_id)
    async with async_session_maker() as db_session:
        course = await CourseService(db_session).get_course(cid)
        return Titled(
            f"Редактирование: {course.name}",
            Form(
                Label("Название", Input(name="name", value=course.name)),
                Label(
                    "Описание",
                    Input(name="description", value=course.description or ""),
                ),
                Button("Сохранить"),
                method="post",
                action=f"/courses/{cid}/edit",
            ),
            A("Отмена", href=f"/courses/{cid}"),
        )


@rt("/courses/{course_id}/edit", methods=["POST"])
async def post_edit_course(session, course_id: str, name: str, description: str):
    require_roles(session, [UserRole.teacher.value, UserRole.admin.value])
    cid = uuid.UUID(course_id)
    async with async_session_maker() as db_session:
        await CourseService(db_session).update_course(
            cid, name=name, description=description
        )
        return RedirectResponse(f"/courses/{cid}", status_code=303)


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


@rt("/courses/{course_id}/remove-user/{user_id}", methods=["POST"])
async def post_remove_user(session, course_id: str, user_id: str):
    require_roles(session, [UserRole.teacher.value, UserRole.admin.value])
    cid = uuid.UUID(course_id)
    uid = uuid.UUID(user_id)
    async with async_session_maker() as db_session:
        await CourseService(db_session).remove_user_from_course(cid, uid)
        return ""
