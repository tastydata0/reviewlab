import asyncio
import uuid
import markdown
from typing import Optional, Any
from fasthtml.common import *
from fastapi.responses import RedirectResponse

from app.base import rt
from app.models.user import UserRole
from app.services.course import CourseService
from app.services.task import TaskService
from app.services.submission import SubmissionService
from app.api.deps.mq import get_mq_service
from app.storage.postgres import async_session_maker
from app.frontend.deps.auth import require_roles
from app.frontend.shared import render_header, render_modal, render_emoji_select
from app.utils.emojis import get_all_lab_emojis
from app.frontend.submissions import render_verdict_badge


@rt("/courses/{course_id}/labs/modal", methods=["GET"])
async def get_create_lab_modal(session, course_id: str):
    require_roles(session, [UserRole.teacher.value, UserRole.admin.value])
    form_content = Form(
        Label(
            "Название лабы (например, ЛР №1)",
            Input(
                name="name",
                placeholder="Название лабы",
                required=True,
            ),
        ),
        Label("Эмоджи", render_emoji_select(None, get_all_lab_emojis())),
        Label("Описание", Input(name="description", placeholder="Описание")),
        Button("Создать", _class="btn-custom btn-primary"),
        method="post",
        action=f"/courses/{course_id}/labs",
    )
    return render_modal("Создать лабораторную работу", form_content, "create-lab-modal")


@rt("/courses/{course_id}/labs/{lab_id}/edit/modal", methods=["GET"])
async def get_edit_lab_modal(session, course_id: str, lab_id: str):
    require_roles(session, [UserRole.teacher.value, UserRole.admin.value])
    lid = uuid.UUID(lab_id)
    async with async_session_maker() as db_session:
        lab = await TaskService(db_session).get_task_group(lid)
        form_content = Form(
            Label("Название ЛР", Input(name="name", value=lab.name, required=True)),
            Label("Эмоджи", render_emoji_select(lab.emoji, get_all_lab_emojis())),
            Label(
                "Описание",
                Textarea(lab.description or "", name="description", rows="5"),
            ),
            Button("Сохранить", _class="btn-custom btn-primary"),
            method="post",
            action=f"/courses/{course_id}/labs/{lab_id}/edit",
        )
        return render_modal(
            "Редактировать лабораторную работу", form_content, "edit-lab-modal"
        )


@rt("/courses/{course_id}/labs/{lab_id}/edit", methods=["POST"])
async def post_edit_lab(
    session,
    course_id: str,
    lab_id: str,
    name: str,
    description: str,
    emoji: Optional[str] = "🌱",
):
    emoji = emoji or "🌱"
    require_roles(session, [UserRole.teacher.value, UserRole.admin.value])
    lid = uuid.UUID(lab_id)
    async with async_session_maker() as db_session:
        await TaskService(db_session).update_task_group(
            lid, name=name, description=description, emoji=emoji
        )
        return RedirectResponse(f"/courses/{course_id}/labs/{lab_id}", status_code=303)


def render_task_item(
    t,
    cid,
    lid,
    role,
    best_score: Optional[float] = None,
    best_correctness: Optional[float] = None,
):
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
                title="Редактировать задачу",
            )
        )
        title_elements.append(
            A(
                " ⚙️",
                href=f"/courses/{cid}/labs/{lid}/tasks/{t.id}/settings",
                style="text-decoration: none; cursor: pointer;",
                title="Настройки анализа для задачи",
            )
        )

    score_display = ""
    if best_score is not None:
        score_percent = min(100, best_score * 10)
        label = f"Ваш лучший результат: {best_score}"
        if best_correctness is not None:
            label += f" (правильность {best_correctness})"

        score_display = Div(
            P(
                B(label),
                style="margin-bottom: 5px; color: #28a745;",
            ),
            Div(
                Div(style=f"width: {score_percent}%;", _class="progress-bar score-bar"),
                _class="progress-container",
            ),
            style="margin-bottom: 15px;",
        )

    return Li(
        Div(*title_elements),
        Div(
            rendered_description,
            style="margin-top: 10px; margin-bottom: 10px; border-left: 3px solid #ccc; padding-left: 10px;",
        ),
        score_display,
        P(f"Код для сдачи: ", Code(t.join_code)),
        P(
            A(
                "История моих попыток",
                href=f"/courses/{cid}/labs/{lid}/tasks/{t.join_code}/my",
            )
        ),
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
                Button("Сохранить", _class="btn-custom btn-primary"),
                A(
                    "Отмена",
                    hx_get=f"/courses/{course_id}/labs/{lab_id}/tasks/{task_id}/cancel",
                    hx_target=f"#task-{task_id}",
                    hx_swap="outerHTML",
                    _class="btn-custom btn-secondary",
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
    user_id = uuid.UUID(session["user_id"])
    async with async_session_maker() as db_session:
        task = await TaskService(db_session).get_task(tid)
        best_score = None
        best_correctness = None
        if role == UserRole.student.value:
            sub_service = SubmissionService(db_session)
            best_sub = await sub_service.get_best_user_submission(
                user_id, task.join_code
            )
            if best_sub:
                best_correctness = (
                    best_sub.correctness / 10.0
                    if best_sub.correctness is not None
                    else None
                )
                best_score = (
                    best_sub.ai_score / 10.0 if best_sub.ai_score is not None else None
                )
        return render_task_item(
            task,
            course_id,
            lab_id,
            role,
            best_score=best_score,
            best_correctness=best_correctness,
        )


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
    user_id = uuid.UUID(session["user_id"])
    async with async_session_maker() as db_session:
        task = await TaskService(db_session).update_task(tid, name, description)
        best_score = None
        best_correctness = None
        if role == UserRole.student.value:
            sub_service = SubmissionService(db_session)
            best_sub = await sub_service.get_best_user_submission(
                user_id, task.join_code
            )
            if best_sub:
                best_correctness = (
                    best_sub.correctness / 10.0
                    if best_sub.correctness is not None
                    else None
                )
                best_score = (
                    best_sub.ai_score / 10.0 if best_sub.ai_score is not None else None
                )
        return render_task_item(
            task,
            course_id,
            lab_id,
            role,
            best_score=best_score,
            best_correctness=best_correctness,
        )


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
            if role == UserRole.student.value:
                sub_service = SubmissionService(db_session)
                task_items = []
                for t in lab.tasks:
                    best_sub = await sub_service.get_best_user_submission(
                        user_id, t.join_code
                    )
                    best_score = None
                    best_correctness = None
                    if best_sub:
                        best_correctness = (
                            best_sub.correctness / 10.0
                            if best_sub.correctness is not None
                            else None
                        )
                        best_score = (
                            best_sub.ai_score / 10.0
                            if best_sub.ai_score is not None
                            else None
                        )

                    task_items.append(
                        render_task_item(
                            t,
                            cid,
                            lid,
                            role,
                            best_score=best_score,
                            best_correctness=best_correctness,
                        )
                    )
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

        course = await CourseService(db_session).get_course(cid)
        header = await render_header(
            session,
            breadcrumbs=[
                ("Мои курсы", "/courses"),
                (course.name_with_emoji, f"/courses/{cid}"),
                (lab.name_with_emoji, f"/courses/{cid}/labs/{lid}"),
            ],
        )

        # Заголовок с кнопкой редактирования лабы
        lab_title_elements = []
        if lab.emoji:
            lab_title_elements.append(Span(f"{lab.emoji} "))
        lab_title_elements.append(Span(f"Лабораторная работа: {lab.name}"))

        if role in (UserRole.teacher.value, UserRole.admin.value):
            lab_title_elements.append(
                A(
                    "✏️",
                    hx_get=f"/courses/{cid}/labs/{lid}/edit/modal",
                    hx_target="#modal-container",
                    style="text-decoration: none; cursor: pointer; font-size: 0.6em; margin-left: 8px;",
                    title="Редактировать лабу",
                )
            )
            lab_title_elements.append(
                A(
                    "⚙️",
                    href=f"/courses/{cid}/labs/{lid}/settings",
                    style="text-decoration: none; cursor: pointer; font-size: 0.6em; margin-left: 8px;",
                    title="Настройки анализа для всей лабы",
                )
            )
            # Добавляем кнопку просмотра результатов
            content.insert(
                2,
                Div(
                    A(
                        "📊 Просмотреть результаты",
                        href=f"/courses/{cid}/labs/{lid}/results",
                        _class="btn-custom btn-primary",
                    ),
                    style="margin-bottom: 20px;",
                ),
            )

        content.append(Div(id="modal-container"))

        return (
            Title(f"ЛР: {lab.name}"),
            header,
            Main(H1(Span(*lab_title_elements)), Div(*content), _class="container"),
        )


@rt("/courses/{course_id}/labs/{lab_id}/tasks/{task_id}/submit", methods=["POST"])
async def post_submit_task(
    session, course_id: str, lab_id: str, task_id: str, files: Any = None
):
    require_roles(
        session, [UserRole.student.value, UserRole.teacher.value, UserRole.admin.value]
    )
    user_id = uuid.UUID(session["user_id"])

    if files is None:
        return Titled(
            "Ошибка",
            P("Файлы не выбраны"),
            A("Назад", href=f"/courses/{course_id}/labs/{lab_id}"),
        )

    # FastHTML может передать как один объект, так и список
    if not isinstance(files, list):
        files = [files]

    source_code = {}
    for f in files:
        # Проверяем, что это объект файла (имеет метод read и filename)
        if hasattr(f, "read") and hasattr(f, "filename"):
            content = f.read()
            # Если read вернул корутину (async), дожидаемся её
            if asyncio.iscoroutine(content):
                content = await content

            if not content:
                continue

            try:
                if isinstance(content, bytes):
                    source_code[f.filename] = content.decode("utf-8")
                else:
                    source_code[f.filename] = str(content)
            except UnicodeDecodeError:
                return Titled(
                    "Ошибка",
                    P(f"Файл {f.filename} не является текстовым файлом"),
                    A("Назад", href=f"/courses/{course_id}/labs/{lab_id}"),
                )

    if not source_code:
        return Titled(
            "Ошибка",
            P("Не загружено ни одного валидного текстового файла"),
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
async def post_create_lab(
    session,
    course_id: str,
    name: str,
    description: str = "",
    emoji: Optional[str] = None,
):
    require_roles(session, [UserRole.teacher.value, UserRole.admin.value])
    cid = uuid.UUID(course_id)
    async with async_session_maker() as db_session:
        await TaskService(db_session).create_task_group(
            cid, name, description, emoji=emoji
        )
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


@rt("/courses/{course_id}/labs/{lab_id}/results", methods=["GET"])
async def get_lab_results(session, course_id: str, lab_id: str):
    require_roles(session, [UserRole.teacher.value, UserRole.admin.value])
    cid = uuid.UUID(course_id)
    lid = uuid.UUID(lab_id)

    async with async_session_maker() as db_session:
        course_service = CourseService(db_session)
        task_service = TaskService(db_session)
        sub_service = SubmissionService(db_session)

        course = await course_service.get_course(cid)
        lab = await task_service.get_task_group(lid)
        users = await course_service.get_course_users(cid)
        # Filter only students for results
        students = [u for u in users if u.role == UserRole.student.value]

        rows = []
        for student in students:
            for task in lab.tasks:
                best_sub = await sub_service.get_best_user_submission(
                    student.id, task.join_code
                )
                if best_sub:
                    rows.append(
                        {"student": student, "task": task, "submission": best_sub}
                    )

        # Сортировка: сначала по дате создания задачи (старые задачи выше),
        # затем по времени отправки (свежие решения выше внутри каждой задачи)
        rows.sort(
            key=lambda x: (
                x["task"].created_at.timestamp() if x["task"].created_at else 0,
                -x["submission"].timestamp.timestamp(),
            )
        )

        header = await render_header(
            session,
            breadcrumbs=[
                ("Мои курсы", "/courses"),
                (course.name_with_emoji, f"/courses/{cid}"),
                (lab.name_with_emoji, f"/courses/{cid}/labs/{lid}"),
                ("Результаты", f"/courses/{cid}/labs/{lid}/results"),
            ],
        )

        table_rows = []
        for row in rows:
            s = row["submission"]
            u = row["student"]
            t = row["task"]

            score = (s.ai_score / 10.0) if s.ai_score is not None else "N/A"
            correctness = (s.correctness / 10.0) if s.correctness is not None else "N/A"
            plag_z = f"{s.plagiarism_score_z:.0f}%"

            verdict_badge = render_verdict_badge(s.plagiarism_verdict)

            plagiarism_actions = Div(
                Button(
                    "🔍",
                    hx_get=f"/submissions/{s.id}/plagiarism-details",
                    hx_target="#modal-container",
                    _class="btn-custom btn-primary",
                    style="padding: 2px 5px; margin-right: 2px;",
                    title="Детали заимствований",
                ),
                Button(
                    "📝",
                    hx_get=f"/submissions/{s.id}/preview",
                    hx_target="#modal-container",
                    _class="btn-custom btn-secondary",
                    style="padding: 2px 5px; margin-right: 2px;",
                    title="Быстрый просмотр кода",
                ),
                Button(
                    "✅",
                    hx_post=f"/submissions/{s.id}/verdict/CONFIRMED",
                    hx_target=f"#verdict-{s.id}",
                    _class="btn-custom btn-success",
                    style="padding: 2px 5px; margin-right: 2px;",
                    title="Подтвердить плагиат",
                ),
                Button(
                    "❌",
                    hx_post=f"/submissions/{s.id}/verdict/DECLINED",
                    hx_target=f"#verdict-{s.id}",
                    _class="btn-custom btn-danger",
                    style="padding: 2px 5px;",
                    title="Опровергнуть плагиат",
                ),
                style="display: flex; align-items: center;",
            )

            table_rows.append(
                Tr(
                    Td(u.full_name),
                    Td(t.name),
                    Td(score),
                    Td(correctness),
                    Td(s.language),
                    Td(s.timestamp.strftime("%d.%m.%Y %H:%M")),
                    Td(plag_z),
                    Td(
                        Div(
                            verdict_badge,
                            plagiarism_actions,
                            id=f"verdict-{s.id}",
                            style="display: flex; flex-direction: column; gap: 5px;",
                        )
                    ),
                    Td(
                        A(
                            "👁️",
                            href=f"/submissions/{s.id}",
                            _class="btn-custom btn-secondary",
                            style="padding: 5px 10px;",
                            title="Просмотреть попытку",
                        )
                    ),
                )
            )

        content = [
            H1(f"Результаты: {lab.name}"),
            Div(
                Table(
                    Thead(
                        Tr(
                            Th("Студент"),
                            Th("Задача"),
                            Th("ИИ"),
                            Th("Правильность"),
                            Th("Язык"),
                            Th("Дата"),
                            Th("Плагиат"),
                            Th("Вердикт и управление"),
                            Th("Обзор"),
                        )
                    ),
                    Tbody(*table_rows),
                    _class="custom-table",
                ),
                _class="custom-table-container",
            ),
            Div(id="modal-container"),
        ]

        return (
            Title(f"Результаты: {lab.name}"),
            header,
            Main(*content, _class="container"),
        )
