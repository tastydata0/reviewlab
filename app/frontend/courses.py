import uuid
import markdown
from fasthtml.common import *
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.base import rt
from app.services.course import CourseService
from app.services.task import TaskService
from app.services.submission import SubmissionService
from app.api.deps.mq import get_mq_service
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


def render_task_item(t, cid, lid, role):
    # Рендеринг Markdown для описания задачи
    rendered_description = NotStr(
        markdown.markdown(
            t.description or "",
            extensions=["extra", "codehilite", "sane_lists"],
        )
    )

    title_elements = [B(t.name)]
    if role in (UserRole.teacher.value, UserRole.admin.value):
        title_elements.append(
            A(
                " ✏️",
                hx_get=f"/courses/{cid}/labs/{lid}/tasks/{t.id}/edit",
                hx_target=f"#task-{t.id}",
                hx_swap="outerHTML",
                style="text-decoration: none; cursor: pointer;",
            )
        )

    return Li(
        Div(*title_elements),
        Div(
            rendered_description,
            style="margin-top: 10px; margin-bottom: 10px; border-left: 3px solid #ccc; padding-left: 10px;",
        ),
        P(f"Код для сдачи: ", Code(t.join_code)),
        Form(
            Input(type="hidden", name="task_id", value=t.join_code),
            Input(type="file", name="files", multiple=True, required=True),
            Button("Сдать решение", type="submit"),
            method="post",
            action=f"/courses/{cid}/labs/{lid}/tasks/{t.join_code}/submit",
            enctype="multipart/form-data",
            style="margin-top: 5px;",
        ),
        id=f"task-{t.id}",
    )


@rt("/courses/{course_id}/labs/{lab_id}/tasks/{task_id}/edit", methods=["GET"])
async def get_edit_task(session, course_id: str, lab_id: str, task_id: str):
    require_roles(session, [UserRole.teacher.value, UserRole.admin.value])
    tid = uuid.UUID(task_id)
    async with async_session_maker() as db_session:
        task = await TaskService(db_session).get_task(tid)
        return Form(
            Label(
                "Название задачи", Input(name="name", value=task.name, required=True)
            ),
            Label(
                "Описание (Markdown)",
                Textarea(
                    task.description or "",
                    name="description",
                    rows="10",
                    placeholder="Описание (Markdown)",
                ),
            ),
            Div(
                Button("Сохранить"),
                A(
                    "Отмена",
                    hx_get=f"/courses/{course_id}/labs/{lab_id}/tasks/{task_id}/cancel",
                    hx_target=f"#task-{task_id}",
                    hx_swap="outerHTML",
                    style="margin-left: 10px; cursor: pointer;",
                ),
                style="margin-top: 10px;",
            ),
            hx_post=f"/courses/{course_id}/labs/{lab_id}/tasks/{task_id}/edit",
            hx_target=f"#task-{task_id}",
            hx_swap="outerHTML",
            id=f"task-{task_id}",
        )


@rt("/courses/{course_id}/labs/{lab_id}/tasks/{task_id}/cancel", methods=["GET"])
async def get_cancel_edit_task(session, course_id: str, lab_id: str, task_id: str):
    require_roles(session, [UserRole.teacher.value, UserRole.admin.value])
    tid = uuid.UUID(task_id)
    role = session["role"]
    async with async_session_maker() as db_session:
        task = await TaskService(db_session).get_task(tid)
        return render_task_item(task, course_id, lab_id, role)


@rt("/courses/{course_id}/labs/{lab_id}/tasks/{task_id}/edit", methods=["POST"])
async def post_edit_task(
    session,
    course_id: str,
    lab_id: str,
    task_id: str,
    name: str,
    description: str = "",
):
    require_roles(session, [UserRole.teacher.value, UserRole.admin.value])
    tid = uuid.UUID(task_id)
    role = session["role"]
    async with async_session_maker() as db_session:
        task = await TaskService(db_session).update_task(tid, name, description)
        return render_task_item(task, course_id, lab_id, role)


@rt("/courses/{course_id}/labs/{lab_id}", methods=["GET"])
async def get_lab_detail(session, course_id: str, lab_id: str):
    require_roles(
        session, [UserRole.student.value, UserRole.teacher.value, UserRole.admin.value]
    )
    cid = uuid.UUID(course_id)
    lid = uuid.UUID(lab_id)
    user_id = uuid.UUID(session["user_id"])
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
            task_items = [render_task_item(t, cid, lid, role) for t in lab.tasks]
            content.append(Ul(*task_items))

        if role == UserRole.student.value:
            async with async_session_maker() as db_session:
                sub_service = SubmissionService(db_session)
                user_subs = await sub_service.get_user_submissions(user_id)
                task_codes = [t.join_code for t in lab.tasks]
                lab_subs = [s for s in user_subs if s.task_id in task_codes]

                if lab_subs:
                    content.extend(
                        [
                            Hr(),
                            H3("Ваши отправки"),
                            Ul(
                                *[
                                    Li(
                                        f"{s.timestamp.strftime('%Y-%m-%d %H:%M:%S')} - Статус: {s.status}"
                                    )
                                    for s in lab_subs
                                ]
                            ),
                        ]
                    )

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
                            placeholder="Содержание задачи (Markdown поддерживается)",
                            rows="10",
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


@rt("/courses/{course_id}/labs/{lab_id}/tasks/{task_id}/submit", methods=["POST"])
async def post_submit_task(
    session, course_id: str, lab_id: str, task_id: str, files: list[UploadFile]
):
    require_roles(session, [UserRole.student.value])
    user_id = uuid.UUID(session["user_id"])

    source_code = {}
    for f in files:
        content = await f.read()
        try:
            source_code[f.filename] = content.decode("utf-8")
        except UnicodeDecodeError:
            return Titled(
                "Ошибка",
                P(f"Файл {f.filename} не является текстовым файлом"),
                A("Назад", href=f"/courses/{course_id}/labs/{lab_id}"),
            )

    async with async_session_maker() as db_session:
        mq_service = await get_mq_service()
        service = SubmissionService(db_session, mq_service=mq_service)
        await service.create_submission(
            user_id=user_id, task_id=task_id, source_code=source_code
        )
        return RedirectResponse(f"/courses/{course_id}/labs/{lab_id}", status_code=303)


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
