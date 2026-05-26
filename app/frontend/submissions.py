import uuid
import markdown
import datetime as dt
from fasthtml.common import *
from sqlalchemy import select

from app.base import rt
from app.services.course import CourseService
from app.services.user import UserService
from app.storage.postgres import async_session_maker
from app.models.user import UserRole, User
from app.models.submission import PlagiarismVerdict, Submission
from app.models.task import Task
from app.models.task_stats import TaskPlagiarismStats
from app.services.submission import SubmissionService
from app.services.task import TaskService
from app.services.settings import get_effective_settings
from app.frontend.deps.auth import require_roles
from app.frontend.shared import render_header, render_modal
from worker.utils.normalization.zscore import normalize_zscore_value


def render_verdict_badge(verdict: PlagiarismVerdict):
    if verdict == PlagiarismVerdict.CONFIRMED:
        return Span("⚠️ Подтвержден", _class="badge badge-plagiarism")
    elif verdict == PlagiarismVerdict.DECLINED:
        return Span("✅ Опровергнут", _class="badge badge-not-plagiarism")
    else:
        return Span("⏳ Ожидает вердикта", style="color: gray; font-style: italic;")


def render_submission_card(
    s, is_best=False, is_teacher=False, hide_results=False, view_results_after=None
):
    score = s.ai_score or 0
    score_percent = min(100, score)

    correctness = s.correctness or 0
    correctness_percent = min(100, correctness)

    plag_prob = s.plagiarism_score_z

    linter_lines = []
    if s.linter_report:
        linter_lines = s.linter_report.strip().split("\n")

    code_content = ""
    for filename, content in s.source_code.items():
        code_content += f"--- {filename} ---\n{content}\n\n"

    best_badge = ""
    if is_best:
        best_badge = Span("🌟 Лучшее решение", _class="badge badge-best")

    verdict_info = ""
    if s.plagiarism_verdict != PlagiarismVerdict.UNSET:
        verdict_info = Div(
            P(
                B("Вердикт преподавателя:"),
                style="margin-top: 10px; margin-bottom: 5px;",
            ),
            render_verdict_badge(s.plagiarism_verdict),
        )

    plagiarism_details_btn = ""
    if is_teacher:
        plagiarism_details_btn = Button(
            "🔍 Детали заимствований",
            hx_get=f"/submissions/{s.id}/plagiarism-details",
            hx_target="#modal-container",
            _class="btn-custom btn-primary",
            style="margin-top: 10px;",
        )

    if hide_results:
        pub_date = (
            view_results_after.strftime("%d.%m.%Y %H:%M")
            if view_results_after
            else "скоро"
        )
        info_column = [
            best_badge,
            H3("Анализ выполняется..."),
            P(
                "Результаты будут доступны после завершения приема работ.",
                style="color: #666;",
            ),
            P(
                f"Дата публикации: {pub_date}",
                style="font-size: 0.8em; color: #999;",
            ),
        ]
    else:
        info_column = [
            best_badge,
            P(
                B(f"Общая оценка - {score / 10.0 if score else 0.0}"),
                style="color: #28a745; margin-bottom: 0;",
            ),
            Div(
                Div(
                    style=f"width: {score_percent}%;",
                    _class="progress-bar score-bar",
                ),
                _class="progress-container",
            ),
            P(
                B(
                    f"Функциональная правильность - {correctness / 10.0 if correctness else 0.0}"
                ),
                style="color: #28a745; margin-top: 10px; margin-bottom: 0;",
            ),
            Div(
                Div(
                    style=f"width: {correctness_percent}%;",
                    _class="progress-bar score-bar",
                ),
                _class="progress-container",
            ),
            P(
                B("ИИ-рецензия"),
                style="margin-top: 20px; margin-bottom: 5px;",
            ),
            Div(
                NotStr(
                    markdown.markdown(
                        s.ai_review or "Рецензия еще не готова.",
                        extensions=["extra", "codehilite", "sane_lists"],
                    )
                ),
                style="font-size: 0.9em; line-height: 1.4; border-left: 3px solid #007bff; padding-left: 15px; background: #f0f7ff; padding: 10px; border-radius: 5px;",
            ),
            P(B("Плагиат:"), style="margin-top: 20px; margin-bottom: 5px;"),
            P(f"Вероятность - {plag_prob:.0f}%", style="margin-bottom: 5px;"),
            Div(
                Div(
                    style=f"width: {plag_prob}%;",
                    _class="progress-bar plagiarism-bar",
                ),
                _class="progress-container",
            ),
            verdict_info,
            plagiarism_details_btn,
            P(
                B("Статический анализ:"),
                style="margin-top: 20px; margin-bottom: 5px;",
            ),
            (
                Div(
                    *[
                        P(
                            line,
                            style="margin: 0; font-size: 0.85em; font-family: monospace;",
                        )
                        for line in linter_lines
                    ]
                )
                if linter_lines
                else P("Ошибок не найдено.", style="font-size: 0.85em;")
            ),
        ]

    return Div(
        Div(
            Div(*info_column, _class="submission-info"),
            # Right side: Code
            Div(code_content, _class="submission-code"),
            _class="submission-card",
        ),
        id=f"submission-{s.id}",
    )


@rt("/courses/{course_id}/labs/{lab_id}/tasks/{task_id}/my", methods=["GET"])
async def get_my_submissions_for_task(
    session, course_id: str, lab_id: str, task_id: str
):
    require_roles(
        session, [UserRole.student.value, UserRole.teacher.value, UserRole.admin.value]
    )
    user_id = uuid.UUID(session["user_id"])

    async with async_session_maker() as db_session:
        user = await UserService(db_session).get_user_by_id(user_id)
        task = await TaskService(db_session).get_task_by_join_code(task_id)
        lab = await TaskService(db_session).get_task_group(uuid.UUID(lab_id))
        course = await CourseService(db_session).get_course(uuid.UUID(course_id))

        settings = await get_effective_settings(db_session, task.id)

        # Check if results should be hidden for students
        role = session["role"]
        is_teacher = role in (UserRole.teacher.value, UserRole.admin.value)

        hide_results = False
        if not is_teacher and settings.view_results_after:
            if dt.datetime.now() < settings.view_results_after:
                hide_results = True

        sub_service = SubmissionService(db_session)
        best_sub = await sub_service.get_best_user_submission(user_id, task_id)
        all_subs = await sub_service.get_user_submissions(user_id)

        task_submissions = [s for s in all_subs if s.task_id == task_id]
        task_submissions.sort(key=lambda x: x.timestamp, reverse=True)

        cards = []
        if best_sub:
            cards.append(
                render_submission_card(
                    best_sub,
                    is_best=True,
                    is_teacher=is_teacher,
                    hide_results=hide_results,
                    view_results_after=settings.view_results_after,
                )
            )
            task_submissions = [s for s in task_submissions if s.id != best_sub.id]

        cards.extend(
            [
                render_submission_card(
                    s,
                    is_teacher=is_teacher,
                    hide_results=hide_results,
                    view_results_after=settings.view_results_after,
                )
                for s in task_submissions
            ]
        )

        header = await render_header(
            session,
            breadcrumbs=[
                ("Мои курсы", "/courses"),
                (course.name_with_emoji, f"/courses/{course_id}"),
                (lab.name_with_emoji, f"/courses/{course_id}/labs/{lab_id}"),
                (
                    task.name,
                    f"/courses/{course_id}/labs/{lab_id}/tasks/{task_id}/my",
                ),
            ],
        )

        return (
            Title(f"{user.full_name} - {task.name}"),
            header,
            Main(
                H1(f"История моих попыток: {task.name}"),
                Hr(),
                (
                    Div(*cards)
                    if cards
                    else P("Вы еще не отправляли решений по этой задаче.")
                ),
                Div(id="modal-container"),
                _class="container",
            ),
        )


@rt("/submissions/{submission_id}/verdict/{verdict}", methods=["POST"])
async def post_update_verdict(session, submission_id: str, verdict: str):
    require_roles(session, [UserRole.teacher.value, UserRole.admin.value])
    sid = uuid.UUID(submission_id)
    new_verdict = PlagiarismVerdict(verdict)

    async with async_session_maker() as db_session:
        submission = await db_session.get(Submission, sid)
        if submission:
            submission.plagiarism_verdict = new_verdict
            db_session.add(submission)
            await db_session.commit()

            # Возвращаем обновленный блок вердикта и кнопок управления
            verdict_badge = render_verdict_badge(new_verdict)
            plagiarism_actions = Div(
                Button(
                    "🔍",
                    hx_get=f"/submissions/{sid}/plagiarism-details",
                    hx_target="#modal-container",
                    _class="btn-custom btn-primary",
                    style="padding: 2px 5px; margin-right: 2px;",
                    title="Детали заимствований",
                ),
                Button(
                    "📝",
                    hx_get=f"/submissions/{sid}/preview",
                    hx_target="#modal-container",
                    _class="btn-custom btn-secondary",
                    style="padding: 2px 5px; margin-right: 2px;",
                    title="Быстрый просмотр кода",
                ),
                Button(
                    "✅",
                    hx_post=f"/submissions/{sid}/verdict/CONFIRMED",
                    hx_target=f"#verdict-{sid}",
                    _class="btn-custom btn-success",
                    style="padding: 2px 5px; margin-right: 2px;",
                    title="Подтвердить плагиат",
                ),
                Button(
                    "❌",
                    hx_post=f"/submissions/{sid}/verdict/DECLINED",
                    hx_target=f"#verdict-{sid}",
                    _class="btn-custom btn-danger",
                    style="padding: 2px 5px;",
                    title="Опровергнуть плагиат",
                ),
                style="display: flex; align-items: center;",
            )
            return verdict_badge, plagiarism_actions
    return "Error"


@rt("/submissions/{submission_id}/preview", methods=["GET"])
async def get_submission_preview(session, submission_id: str):
    require_roles(session, [UserRole.teacher.value, UserRole.admin.value])
    sid = uuid.UUID(submission_id)
    async with async_session_maker() as db_session:
        submission = await db_session.get(Submission, sid)
        if not submission:
            return "Not found"

        code_content = ""
        for filename, content in submission.source_code.items():
            code_content += f"--- {filename} ---\n{content}\n\n"

        content = Div(
            Pre(
                code_content,
                style="background: #f8f9fa; padding: 15px; border-radius: 8px; font-size: 0.85em; max-height: 60vh; overflow-y: auto;",
            ),
            style="margin-top: 10px;",
        )
        return render_modal(
            f"Просмотр кода: {submission.language}", content, "code-preview-modal"
        )


@rt("/submissions/{submission_id}/plagiarism-details", methods=["GET"])
async def get_plagiarism_details(session, submission_id: str):
    require_roles(session, [UserRole.teacher.value, UserRole.admin.value])
    sid = uuid.UUID(submission_id)

    async with async_session_maker() as db_session:
        submission = await db_session.get(Submission, sid)
        if not submission:
            return "Submission not found"

        # Находим реальный UUID задачи по join_code из посылки
        task_stmt = select(Task).where(Task.join_code == submission.task_id.upper())
        task_res = await db_session.execute(task_stmt)
        task = task_res.scalars().first()
        task_id_uuid = task.id if task else None

        # Получаем статистику для динамической нормализации по UUID
        mean, std_dev = 0.0, 0.0
        if task_id_uuid:
            stats = await db_session.get(TaskPlagiarismStats, task_id_uuid)
            mean = stats.mean if stats else 0.0
            std_dev = stats.std_dev if stats else 0.0

        matches = submission.plagiarism_matches or {}
        if not matches:
            return render_modal(
                "Детали заимствований",
                P("Совпадений не найдено."),
                "plag-details-modal",
            )

        match_rows = []
        for other_id, raw_score in matches.items():
            other_sid = uuid.UUID(other_id)
            other_sub = await db_session.get(Submission, other_sid)
            if other_sub:
                other_user = await db_session.get(User, other_sub.user_id)
                user_name = other_user.full_name if other_user else "Неизвестен"

                # Нормализуем сырой балл динамически
                norm_score = normalize_zscore_value(raw_score, mean, std_dev)

                match_rows.append(
                    Tr(
                        Td(
                            A(
                                user_name,
                                href=f"/submissions/{other_sub.id}",
                                target="_blank",
                            )
                        ),
                        Td(f"{norm_score:.1f}%"),
                        Td(other_sub.timestamp.strftime("%d.%m.%Y %H:%M")),
                        Td(other_sub.language),
                    )
                )

        content = Div(
            Table(
                Thead(Tr(Th("У кого списал"), Th("Схожесть"), Th("Дата"), Th("Язык"))),
                Tbody(*match_rows),
                _class="custom-table",
            ),
            _class="custom-table-container",
        )
        return render_modal("Детали заимствований", content, "plag-details-modal")


@rt("/submissions/{submission_id}", methods=["GET"])
async def get_submission_view(session, submission_id: str):
    require_roles(session, [UserRole.teacher.value, UserRole.admin.value])
    sid = uuid.UUID(submission_id)

    async with async_session_maker() as db_session:
        submission = await db_session.get(Submission, sid)
        if not submission:
            return Titled("Ошибка", P("Посылка не найдена"))

        user = await db_session.get(User, submission.user_id)
        task = await TaskService(db_session).get_task_by_join_code(submission.task_id)

        header = await render_header(
            session, [("Просмотр посылки", f"/submissions/{sid}")]
        )

        card = render_submission_card(submission, is_teacher=True)

        return (
            Title(f"Посылка: {user.full_name if user else sid}"),
            header,
            Main(
                H1(f"Посылка {user.full_name if user else sid}"),
                P(B("Задача: "), task.name if task else "Неизвестна"),
                Hr(),
                card,
                Div(id="modal-container"),
                _class="container",
            ),
        )
