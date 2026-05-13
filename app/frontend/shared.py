import uuid
from typing import Optional
from fasthtml.common import *
from app.storage.postgres import async_session_maker
from app.services.user import UserService
from app.models.user import UserRole
from app.utils.emojis import get_colors_for_emoji


async def render_header(session, breadcrumbs: list[tuple[str, str]] = None):
    has_session = "user_id" in session and session.get("user_id")
    logo_img = A(
        Img(src="/images/logo.png", alt="ReviewLab", style="height: 40px;"),
        href="/",
        style="text-decoration: none;",
    )

    if not has_session:
        return Header(
            Div(
                Div(logo_img),
                Div(
                    A("Вход", href="/login", _class="custom-user-link"),
                    A("Регистрация", href="/register", _class="custom-user-link"),
                ),
                style="display: flex; align-items: center; justify-content: space-between; padding: 20px 40px; border-bottom: 1px solid #eee;",
            ),
            style="background: white;",
        )

    user_id = uuid.UUID(session["user_id"])
    role = session.get("role")

    async with async_session_maker() as db_session:
        user = await UserService(db_session).get_user_by_id(user_id)

    nav_links = [
        Li(A("Главная", href="/")),
        Li(A("Мои курсы", href="/courses")),
        Li(A("Профиль", href="/me")),
    ]
    if role in (UserRole.teacher.value, UserRole.admin.value):
        nav_links.append(Li(A("Администрирование", href="/groups")))

    bc_elements = []
    if breadcrumbs:
        for i, (name, href) in enumerate(breadcrumbs):
            bc_elements.append(
                A(
                    B(name) if i == len(breadcrumbs) - 1 else name,
                    href=href,
                    _class="custom-breadcrumb-item",
                )
            )
            if i < len(breadcrumbs) - 1:
                bc_elements.append(Span(" / ", _class="custom-breadcrumb-separator"))

    return Header(
        Div(
            Div(
                Div(logo_img),
                Div(
                    Details(
                        Summary("☰"),
                        Ul(*nav_links),
                    ),
                    _class="custom-nav-dropdown",
                    style="margin-left: 20px;",
                ),
                Span(
                    "",
                    _class="custom-breadcrumb-separator",
                    style="margin-right: 5px;",
                ),
                (
                    Div(*bc_elements, _class="custom-breadcrumbs")
                    if bc_elements
                    else Div(style="flex: 1;")
                ),
                style="display: flex; align-items: center;",
            ),
            Div(
                A(user.full_name, href="/me", _class="custom-user-link"),
                A(
                    "Выход",
                    href="/logout",
                    _class="custom-user-link",
                ),
                _class="custom-user-nav",
            ),
            _class="custom-header",
        ),
        _class="container",
    )


def render_card(title, emoji, href, description=None):
    colors = get_colors_for_emoji(emoji)
    gradient = f"linear-gradient(135deg, {colors[0]} 0%, {colors[1]} 100%)"
    return A(
        Div(
            emoji,
            _class="custom-card-top",
            style=f"background: {gradient};",
        ),
        Div(
            Div(title, _class="custom-card-title"),
            Div(
                (
                    description[:100] + "..."
                    if description and len(description) > 100
                    else (description or "")
                ),
                _class="custom-card-desc",
            ),
            _class="custom-card-body",
        ),
        href=href,
        _class="custom-card",
    )


def render_add_card(href, target="#modal-container"):
    return A(
        "+",
        hx_get=href,
        hx_target=target,
        _class="custom-card-add",
        style="text-decoration: none;",
    )


def render_emoji_select(
    current_emoji: Optional[str], emoji_list: list[str], name: str = "emoji"
):
    options = [Option(e, value=e, selected=(e == current_emoji)) for e in emoji_list]
    return Select(*options, name=name)


def render_modal(title: str, content, modal_id: str):
    return Dialog(
        Article(
            A(
                href="#",
                aria_label="Закрыть",
                _class="close",
                onclick="this.closest('dialog').remove()",
                style="margin-top: 0;",
            ),
            H3(title),
            content,
        ),
        open=True,
        id=modal_id,
    )
