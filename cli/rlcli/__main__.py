import typer
import os
from datetime import datetime
from typing import List, Optional
from rich.console import Console
from rich.table import Table
from .client import Client
from .config import save_token, delete_token, load_token, save_url, load_url

app = typer.Typer(
    help="ReviewLab CLI — инструмент для автоматизированной проверки кода и взаимодействия с ИИ-ментором.",
    rich_markup_mode="rich",
)
console = Console()


def get_client():
    return Client()


def format_date(iso_str: str) -> str:
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.strftime("%d.%m.%Y %H:%M:%S")
    except Exception:
        return iso_str


def get_score_style(score: Optional[float]) -> str:
    if score is None:
        return "dim"
    if score < 4.0:
        return "bold red"
    if score < 7.0:
        return "yellow"
    if score < 9.0:
        return "green"
    return "bold green"


@app.command()
def login(
    email: str = typer.Option(
        ..., "--email", "-e", prompt="Email", help="Email вашей учетной записи"
    ),
    password: str = typer.Option(
        ...,
        "--password",
        "-p",
        prompt="Пароль",
        hide_input=True,
        help="Пароль от учетной записи",
    ),
    token_ttl_minutes: int = typer.Option(
        120,
        "--ttl",
        prompt="Срок действия сессии (в минутах)",
        help="Время жизни токена в минутах до автоматического выхода",
    ),
):
    """
    [bold green]Авторизация[/bold green] в системе ReviewLab.
    Получает персональный токен доступа и сохраняет его локально.
    """
    client = get_client()
    with console.status("[bold green]Авторизация..."):
        token = client.login(email, password, token_ttl_minutes)

    if token:
        save_token(token)
        console.print("[bold green]Вы успешно вошли![/bold green]")
    else:
        console.print(
            "[bold red]Ошибка входа. Пожалуйста, проверьте свои данные.[/bold red]"
        )


@app.command()
def logout():
    """
    [bold yellow]Выход[/bold yellow] из системы.
    Удаляет локально сохраненный токен доступа.
    """
    delete_token()
    console.print("[bold yellow]Вы успешно вышли.[/bold yellow]")


@app.command()
def config(
    url: Optional[str] = typer.Option(
        None,
        "--url",
        help="Установить новый URL бэкенда (например, http://localhost:8080/api)",
    ),
):
    """
    Просмотр и редактирование [bold cyan]настроек[/bold cyan] подключения.
    Позволяет изменить адрес сервера, к которому обращается CLI.
    """
    if url:
        save_url(url)
        console.print(f"[bold green]URL бэкенда успешно изменен на: {url}[/bold green]")
    else:
        current_url = load_url()
        console.print(f"Текущий URL бэкенда: [bold cyan]{current_url}[/bold cyan]")
        console.print(
            "Чтобы изменить URL, используйте: [dim]rlcli config --url http://your-api.com/api[/dim]"
        )


@app.command()
def submit(
    task_id: str = typer.Argument(
        ..., help="Короткий код задачи (JOIN_CODE), например 'ABC12'"
    ),
    files: List[str] = typer.Argument(..., help="Список путей к файлам вашего решения"),
):
    """
    [bold green]Отправка решения[/bold green] на проверку.
    Система проверит код линтерами, проанализирует на плагиат и отправит ИИ-ментору.
    """
    if not load_token():
        console.print(
            "[bold red]Ошибка: Вы должны войти в систему. Используйте 'rlcli login'.[/bold red]"
        )
        raise typer.Exit(1)

    client = get_client()
    try:
        for f in files:
            if not os.path.exists(f):
                console.print(f"[bold red]Ошибка: Файл не найден: {f}[/bold red]")
                raise typer.Exit(1)

        with console.status(
            f"[bold green]Отправка {len(files)} файл(ов) для задачи {task_id}..."
        ):
            result = client.submit_task(task_id, files)
        console.print(f"[bold green]✓ Решение успешно отправлено![/bold green]")
        console.print(f"ID отправки: {result.get('id')}")
    except Exception as e:
        console.print(f"[bold red]Ошибка: {str(e)}[/bold red]")
        raise typer.Exit(1)


@app.command()
def view(
    task_id: Optional[str] = typer.Option(
        None, "--task", "-t", help="Фильтр по коду задачи (JOIN_CODE)"
    ),
):
    """
    Просмотр [bold blue]истории отправок[/bold blue] и результатов проверки.
    Выводит таблицу с вашими попытками, статусами и оценками.
    """
    if not load_token():
        console.print(
            "[bold red]Ошибка: Вы должны войти в систему. Используйте 'rlcli login'.[/bold red]"
        )
        raise typer.Exit(1)

    client = get_client()
    try:
        with console.status("[bold green]Получение списка отправок..."):
            submissions = client.get_my_submissions()

        if task_id:
            submissions = [
                s for s in submissions if s["task_id"].upper() == task_id.upper()
            ]

        if not submissions:
            console.print("[yellow]Отправки не найдены.[/yellow]")
            return

        submissions.sort(key=lambda x: x["timestamp"], reverse=True)

        table = Table(title="Мои отправки")
        table.add_column("ID", style="dim")
        table.add_column("Лаба", style="magenta")
        table.add_column("Задача", style="cyan")
        table.add_column("Код", style="blue")
        table.add_column("Статус", style="bold")
        table.add_column("Оценка", justify="right")
        table.add_column("Дата", style="blue")

        status_map = {
            "CREATED": "Создано",
            "PROCESSING": "В обработке",
            "PROCESSED": "Оценено",
            "FAILED": "Ошибка",
        }

        for s in submissions:
            raw_status = s.get("status", "UNKNOWN")
            status_text = status_map.get(raw_status, raw_status)
            status_color = "green" if raw_status == "PROCESSED" else "yellow"
            if raw_status == "FAILED":
                status_color = "red"

            score_val = s.get("ai_score")
            score_num = score_val / 10.0 if score_val is not None else None
            score_style = get_score_style(score_num)
            score_str = (
                f"[{score_style}]{score_num:.1f}[/{score_style}]"
                if score_num is not None
                else "N/A"
            )

            table.add_row(
                str(s["id"])[:8],
                s.get("task_group_name", "N/A"),
                s.get("task_name", s["task_id"]),
                s["task_id"],
                f"[{status_color}]{status_text}[/{status_color}]",
                score_str,
                format_date(s["timestamp"]),
            )

        console.print(table)
    except Exception as e:
        console.print(f"[bold red]Ошибка: {str(e)}[/bold red]")
        raise typer.Exit(1)


@app.command()
def tasks():
    """
    Получение списка [bold magenta]доступных задач[/bold magenta].
    Отображает курсы, лабораторные работы и коды для сдачи.
    """
    if not load_token():
        console.print(
            "[bold red]Ошибка: Вы должны войти в систему. Используйте 'rlcli login'.[/bold red]"
        )
        raise typer.Exit(1)

    client = get_client()
    try:
        with console.status("[bold green]Загрузка списка задач..."):
            all_tasks = client.get_tasks()

        if not all_tasks:
            console.print("[yellow]Доступные задачи не найдены.[/yellow]")
            return

        table = Table(title="Доступные задачи")
        table.add_column("Курс", style="magenta")
        table.add_column("Лабораторная", style="cyan")
        table.add_column("Название", style="bold")
        table.add_column("Код для сдачи", style="green")

        for t in all_tasks:
            table.add_row(
                t.get("course_name", "N/A"),
                t.get("task_group_name", "N/A"),
                t.get("name", "N/A"),
                t.get("join_code", "N/A"),
            )

        console.print(table)
    except Exception as e:
        console.print(f"[bold red]Ошибка: {str(e)}[/bold red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
