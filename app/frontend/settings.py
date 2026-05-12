import uuid
import json
import datetime as dt
from fasthtml.common import *
from fastapi.responses import RedirectResponse

from app.base import rt
from app.storage.postgres import async_session_maker
from app.models.user import UserRole
from app.models.course import Course
from app.models.task import Task
from app.models.task_group import TaskGroup
from app.schemas.settings import CascadingSettings
from app.services.course import CourseService
from app.services.task import TaskService
from app.services.settings import get_effective_settings
from app.frontend.deps.auth import require_roles
from app.frontend.shared import render_header, render_modal
from app.utils.mentor_presets import MENTOR_PROMPTS


def render_settings_form(effective: CascadingSettings, inherited: CascadingSettings, explicit: dict, action_url: str, parent_name: Optional[str] = None):
    presets_json = json.dumps(MENTOR_PROMPTS, ensure_ascii=False)
    
    inherited_values = {
        "plag_max_z": inherited.plagiarism.max_z,
        "plag_use_semantic": inherited.plagiarism.use_semantic,
        "plag_use_lexical": inherited.plagiarism.use_lexical,
        "plag_min_threshold": inherited.plagiarism.min_similarity_threshold,
        "linter_timeout": inherited.linter.timeout_seconds,
        "linter_preset": inherited.linter.linter_preset_id,
        "llm_strictness": inherited.llm.strictness_level,
        "llm_mode": inherited.llm.review_mode,
        "llm_inst_1": inherited.llm.custom_instruction_1 or "",
        "llm_inst_2": inherited.llm.custom_instruction_2 or "",
        "llm_inst_3": inherited.llm.custom_instruction_3 or "",
        "submission_limit": inherited.submission_limit,
        "view_results_after": inherited.view_results_after.isoformat()[:16] if inherited.view_results_after else ""
    }
    inherited_json = json.dumps(inherited_values, ensure_ascii=False)
    
    js_script = f"""
    const presets = {presets_json};
    const inherited_vals = {inherited_json};
    
    function updateStrictness(val) {{
        let el = document.getElementById('strictness-val');
        if(el) el.innerText = val;
        let desc = document.getElementById('strictness-desc');
        if(desc) desc.innerText = presets[val] || '';
    }}
    
    function updateValue(id, val) {{
        let el = document.getElementById(id);
        if(el) el.innerText = val;
    }}
    
    function toggleInherit(name, isChecked, isGroup) {{
        if (isGroup) {{
            let els = document.querySelectorAll('.' + name + '_group');
            els.forEach((e, idx) => {{
                e.disabled = isChecked;
                if (isChecked) {{
                    e.value = inherited_vals[e.name];
                }}
            }});
        }} else {{
            let el = document.getElementById(name + '_input');
            if (el) {{
                el.disabled = isChecked;
                if (isChecked) {{
                    if (el.type === 'checkbox') {{
                        el.checked = inherited_vals[name];
                    }} else {{
                        el.value = inherited_vals[name];
                        // trigger oninput manually if we have specific updaters
                        if (name === 'llm_strictness') {{
                            updateStrictness(el.value);
                        }} else if (name === 'plag_max_z') {{
                            updateValue('plag-z-val', el.value);
                        }} else if (name === 'plag_min_threshold') {{
                            updateValue('plag-min-val', el.value);
                        }} else if (name === 'linter_timeout') {{
                            updateValue('linter-timeout-val', el.value);
                        }} else if (name === 'submission_limit') {{
                            updateValue('submission-limit-val', el.value == 0 ? 'Без лимита' : el.value);
                        }}
                    }}
                }}
            }}
        }}
    }}
    """

    plag_explicit = explicit.get("plagiarism", {})
    lint_explicit = explicit.get("linter", {})
    llm_explicit = explicit.get("llm", {})

    def fld(name, label_text, input_el, exp_val, val_disp=None, is_group=False):
        is_inherited = (exp_val is None) and (parent_name is not None)
        toggle = ""
        if parent_name:
            js_action = f"toggleInherit('{name}', this.checked, {'true' if is_group else 'false'});"
            toggle = Label(
                Input(type="checkbox", name=f"inherit_{name}", checked=is_inherited, onchange=js_action),
                f"Унаследовать от {parent_name}",
                style="font-size: 0.85em; color: #007bff; font-weight: normal; cursor: pointer; display: flex; align-items: center; gap: 5px; margin:0;"
            )
        
        if not is_group:
            input_el.id = f"{name}_input"
            if is_inherited:
                input_el.disabled = True
        
        return Div(
            Div(B(label_text), toggle, style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; border-bottom: 1px solid #eee; padding-bottom: 5px;"),
            input_el,
            val_disp if val_disp else "",
            style="padding: 15px; background: white; border: 1px solid #ddd; border-radius: 8px; margin-bottom: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.02);"
        )

    return Form(
        Script(NotStr(js_script)),
        
        H3("Антиплагиат", style="margin-top: 20px; border-bottom: 2px solid #333; padding-bottom: 5px;"),
        fld("plag_max_z", "Порог Z-score (max_z) - чем меньше, тем строже", 
            Input(name="plag_max_z", value=effective.plagiarism.max_z, type="range", step="0.1", min="0.5", max="5.0", oninput="updateValue('plag-z-val', this.value);", style="width: 100%;"),
            plag_explicit.get("max_z"),
            P(B("Текущий порог Z-score: "), Span(effective.plagiarism.max_z, id="plag-z-val"), style="margin-top: 5px; font-size: 0.9em; color: #555;")
        ),
        fld("plag_use_semantic", "Семантический анализ (векторы)",
            Input(name="plag_use_semantic", type="checkbox", checked=effective.plagiarism.use_semantic),
            plag_explicit.get("use_semantic")
        ),
        fld("plag_use_lexical", "Лексический анализ (текст)",
            Input(name="plag_use_lexical", type="checkbox", checked=effective.plagiarism.use_lexical),
            plag_explicit.get("use_lexical")
        ),
        fld("plag_min_threshold", "Минимальное сходство для отображения",
            Input(name="plag_min_threshold", value=effective.plagiarism.min_similarity_threshold, type="range", step="0.05", min="0.0", max="1.0", oninput="updateValue('plag-min-val', this.value);", style="width: 100%;"),
            plag_explicit.get("min_similarity_threshold"),
            P(B("Текущий минимум: "), Span(effective.plagiarism.min_similarity_threshold, id="plag-min-val"), style="margin-top: 5px; font-size: 0.9em; color: #555;")
        ),

        H3("Линтер", style="margin-top: 30px; border-bottom: 2px solid #333; padding-bottom: 5px;"),
        fld("linter_timeout", "Таймаут выполнения (сек)",
            Input(name="linter_timeout", value=effective.linter.timeout_seconds, type="range", min="5", max="120", step="5", oninput="updateValue('linter-timeout-val', this.value);", style="width: 100%;"),
            lint_explicit.get("timeout_seconds"),
            P(B("Текущий таймаут: "), Span(effective.linter.timeout_seconds, id="linter-timeout-val"), " сек", style="margin-top: 5px; font-size: 0.9em; color: #555;")
        ),
        fld("linter_preset", "Пресет аргументов",
            Select(
                Option("Стандартный", value="1", selected=(effective.linter.linter_preset_id == 1)),
                Option("Строгий", value="2", selected=(effective.linter.linter_preset_id == 2)),
                Option("Google Style", value="3", selected=(effective.linter.linter_preset_id == 3)),
                Option("Академический", value="4", selected=(effective.linter.linter_preset_id == 4)),
                name="linter_preset",
            ),
            lint_explicit.get("linter_preset_id")
        ),

        H3("ИИ-Ментор", style="margin-top: 30px; border-bottom: 2px solid #333; padding-bottom: 5px;"),
        fld("llm_strictness", "Уровень строгости ИИ (1-10)",
            Input(type="range", name="llm_strictness", min="1", max="10", value=effective.llm.strictness_level, oninput="updateStrictness(this.value);", style="width: 100%;"),
            llm_explicit.get("strictness_level"),
            Div(
                P(B("Текущий уровень: "), Span(effective.llm.strictness_level, id="strictness-val"), style="margin-top: 5px; margin-bottom: 5px; font-size: 0.9em; color: #555;"),
                Div(MENTOR_PROMPTS.get(effective.llm.strictness_level, ""), id="strictness-desc", style="font-style: italic; color: #666; min-height: 3em; background: #f9f9f9; padding: 10px; border-radius: 5px;")
            )
        ),
        fld("llm_mode", "Режим общения",
            Select(
                Option("Сократический (намеки)", value="socratic", selected=(effective.llm.review_mode == "socratic")),
                Option("Прямой (объяснение ошибок)", value="direct", selected=(effective.llm.review_mode == "direct")),
                name="llm_mode",
            ),
            llm_explicit.get("review_mode")
        ),
        fld("llm_inst_1", "Дополнительная инструкция 1",
            Textarea(effective.llm.custom_instruction_1 or "", name="llm_inst_1", rows="2", style="width: 100%;", placeholder="Слот 1 (например, для всего курса)"),
            llm_explicit.get("custom_instruction_1")
        ),
        fld("llm_inst_2", "Дополнительная инструкция 2",
            Textarea(effective.llm.custom_instruction_2 or "", name="llm_inst_2", rows="2", style="width: 100%;", placeholder="Слот 2 (например, для лабы)"),
            llm_explicit.get("custom_instruction_2")
        ),
        fld("llm_inst_3", "Дополнительная инструкция 3",
            Textarea(effective.llm.custom_instruction_3 or "", name="llm_inst_3", rows="2", style="width: 100%;", placeholder="Слот 3 (например, для конкретной задачи)"),
            llm_explicit.get("custom_instruction_3")
        ),

        H3("Общие настройки", style="margin-top: 30px; border-bottom: 2px solid #333; padding-bottom: 5px;"),
        fld("submission_limit", "Лимит попыток (0 - без лимита)",
            Input(name="submission_limit", value=effective.submission_limit, type="range", min="0", max="20", step="1", oninput="updateValue('submission-limit-val', this.value == 0 ? 'Без лимита' : this.value);", style="width: 100%;"),
            explicit.get("submission_limit"),
            P(B("Текущий лимит: "), Span("Без лимита" if effective.submission_limit == 0 else effective.submission_limit, id="submission-limit-val"), style="margin-top: 5px; font-size: 0.9em; color: #555;")
        ),
        fld("view_results_after", "Скрыть результаты до (дата публикации)",
            Input(name="view_results_after", value=(effective.view_results_after.isoformat()[:16] if effective.view_results_after else ""), type="datetime-local", style="width: 100%;"),
            explicit.get("view_results_after")
        ),
        
        Button("Сохранить изменения", _class="btn-custom btn-primary", style="margin-top: 20px; width: 100%; font-size: 1.1em; padding: 12px;"),
        method="post",
        action=action_url,
        style="max-width: 700px; margin-bottom: 50px; background: #fdfdfd; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);"
    )


def parse_settings_form(d: dict, is_course: bool) -> dict:
    def get_val(key, parser):
        if not is_course and d.get(f"inherit_{key}"):
            return None
        val = d.get(key)
        if val is None or val == "":
            return None
        try:
            return parser(val)
        except ValueError:
            return None

    def get_bool(key):
        if not is_course and d.get(f"inherit_{key}"):
            return None
        return key in d

    view_results_after = None
    if not is_course and d.get("inherit_view_results_after"):
        pass
    else:
        vra = d.get("view_results_after")
        if vra:
            try:
                view_results_after = dt.datetime.fromisoformat(vra).isoformat()
            except ValueError:
                pass

    res = {
        "plagiarism": {
            "max_z": get_val("plag_max_z", float),
            "use_semantic": get_bool("plag_use_semantic"),
            "use_lexical": get_bool("plag_use_lexical"),
            "min_similarity_threshold": get_val("plag_min_threshold", float),
        },
        "linter": {
            "timeout_seconds": get_val("linter_timeout", int),
            "linter_preset_id": get_val("linter_preset", int),
        },
        "llm": {
            "strictness_level": get_val("llm_strictness", int),
            "review_mode": get_val("llm_mode", str),
            "custom_instruction_1": get_val("llm_inst_1", str),
            "custom_instruction_2": get_val("llm_inst_2", str),
            "custom_instruction_3": get_val("llm_inst_3", str),
        },
        "submission_limit": get_val("submission_limit", int),
        "view_results_after": view_results_after,
    }

    def clean_dict(target):
        cleaned = {}
        for k, v in target.items():
            if isinstance(v, dict):
                cv = clean_dict(v)
                if cv:
                    cleaned[k] = cv
            elif v is not None:
                cleaned[k] = v
        return cleaned

    return clean_dict(res)


@rt("/courses/{course_id}/settings", methods=["GET"])
async def get_course_settings(session, course_id: str):
    require_roles(session, [UserRole.teacher.value, UserRole.admin.value])
    cid = uuid.UUID(course_id)
    async with async_session_maker() as db_session:
        course = await CourseService(db_session).get_course(cid)
        settings = CascadingSettings.model_validate(course.settings or {})

        header = await render_header(
            session,
            breadcrumbs=[
                ("Мои курсы", "/courses"),
                (course.name_with_emoji, f"/courses/{cid}"),
                ("Настройки анализа", f"/courses/{cid}/settings"),
            ],
        )

        return Titled(
            f"Настройки курса: {course.name}",
            header,
            Main(
                H1(f"Настройки анализа: {course.name}"),
                render_settings_form(settings, settings, course.settings or {}, f"/courses/{course_id}/settings", parent_name=None),
                _class="container",
            ),
        )


@rt("/courses/{course_id}/settings", methods=["POST"])
async def post_course_settings(session, course_id: str, d: dict):
    require_roles(session, [UserRole.teacher.value, UserRole.admin.value])
    cid = uuid.UUID(course_id)
    new_settings_dict = parse_settings_form(d, is_course=True)

    async with async_session_maker() as db_session:
        course = await CourseService(db_session).get_course(cid)
        course.settings = new_settings_dict
        db_session.add(course)
        await db_session.commit()
        return RedirectResponse(f"/courses/{course_id}", status_code=303)


@rt("/courses/{course_id}/labs/{lab_id}/settings", methods=["GET"])
async def get_lab_settings(session, course_id: str, lab_id: str):
    require_roles(session, [UserRole.teacher.value, UserRole.admin.value])
    lid = uuid.UUID(lab_id)
    cid = uuid.UUID(course_id)
    async with async_session_maker() as db_session:
        lab = await TaskService(db_session).get_task_group(lid)
        course = await CourseService(db_session).get_course(cid)

        current_settings = lab.settings or {}
        course_settings = CascadingSettings.model_validate(course.settings or {})
        effective = CascadingSettings.merge(course_settings, current_settings)

        header = await render_header(
            session,
            breadcrumbs=[
                ("Мои курсы", "/courses"),
                (course.name_with_emoji, f"/courses/{cid}"),
                (lab.name_with_emoji, f"/courses/{cid}/labs/{lid}"),
                ("Настройки анализа", f"/courses/{cid}/labs/{lid}/settings"),
            ],
        )

        return Titled(
            f"Настройки лабы: {lab.name}",
            header,
            Main(
                H1(f"Настройки анализа: {lab.name}"),
                P(
                    "Вы можете переопределить настройки курса для всех задач в этой лабе или унаследовать их.",
                    style="color: #666;",
                ),
                render_settings_form(
                    effective, course_settings, current_settings, f"/courses/{course_id}/labs/{lab_id}/settings", parent_name="Курса"
                ),
                _class="container",
            ),
        )


@rt("/courses/{course_id}/labs/{lab_id}/settings", methods=["POST"])
async def post_lab_settings(session, course_id: str, lab_id: str, d: dict):
    require_roles(session, [UserRole.teacher.value, UserRole.admin.value])
    lid = uuid.UUID(lab_id)
    new_settings_dict = parse_settings_form(d, is_course=False)

    async with async_session_maker() as db_session:
        lab = await TaskService(db_session).get_task_group(lid)
        lab.settings = new_settings_dict
        db_session.add(lab)
        await db_session.commit()
        return RedirectResponse(f"/courses/{course_id}/labs/{lab_id}", status_code=303)


@rt("/courses/{course_id}/labs/{lab_id}/tasks/{task_id}/settings", methods=["GET"])
async def get_task_settings(session, course_id: str, lab_id: str, task_id: str):
    require_roles(session, [UserRole.teacher.value, UserRole.admin.value])
    tid = uuid.UUID(task_id)
    lid = uuid.UUID(lab_id)
    cid = uuid.UUID(course_id)
    async with async_session_maker() as db_session:
        task = await TaskService(db_session).get_task(tid)
        lab = await TaskService(db_session).get_task_group(lid)
        course = await CourseService(db_session).get_course(cid)

        effective = await get_effective_settings(db_session, tid)
        current_settings = task.settings or {}
        
        course_settings = CascadingSettings.model_validate(course.settings or {})
        lab_effective = CascadingSettings.merge(course_settings, lab.settings or {})

        header = await render_header(
            session,
            breadcrumbs=[
                ("Мои курсы", "/courses"),
                (course.name_with_emoji, f"/courses/{cid}"),
                (lab.name_with_emoji, f"/courses/{cid}/labs/{lid}"),
                (task.name, f"/courses/{cid}/labs/{lid}/tasks/{task.join_code}/my"),
                (
                    "Настройки анализа",
                    f"/courses/{cid}/labs/{lid}/tasks/{task_id}/settings",
                ),
            ],
        )

        return Titled(
            f"Настройки задачи: {task.name}",
            header,
            Main(
                H1(f"Настройки анализа: {task.name}"),
                P(
                    "Вы можете переопределить настройки лабы для этой задачи или оставить их унаследованными.",
                    style="color: #666;",
                ),
                render_settings_form(
                    effective,
                    lab_effective,
                    current_settings,
                    f"/courses/{course_id}/labs/{lab_id}/tasks/{task_id}/settings",
                    parent_name="Лабораторной работы"
                ),
                _class="container",
            ),
        )


@rt("/courses/{course_id}/labs/{lab_id}/tasks/{task_id}/settings", methods=["POST"])
async def post_task_settings(
    session, course_id: str, lab_id: str, task_id: str, d: dict
):
    require_roles(session, [UserRole.teacher.value, UserRole.admin.value])
    tid = uuid.UUID(task_id)
    new_settings_dict = parse_settings_form(d, is_course=False)

    async with async_session_maker() as db_session:
        task = await TaskService(db_session).get_task(tid)
        task.settings = new_settings_dict
        db_session.add(task)
        await db_session.commit()
        return RedirectResponse(f"/courses/{course_id}/labs/{lab_id}", status_code=303)
