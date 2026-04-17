import typer
import uuid
import os
from typing import List, Optional
from rich.console import Console
from rich.table import Table
from .client import Client
from .auth import save_token, delete_token, load_token

app = typer.Typer(help="CLI утилита")
console = Console()


def get_client():
    return Client()


@app.command()
def login(
    email: str = typer.Option(..., prompt="Email"),
    password: str = typer.Option(..., prompt="Пароль", hide_input=True),
):
    client = get_client()
    with console.status("[bold green]Авторизация..."):
        token = client.login(email, password)

    if token:
        save_token(token)
        console.print("[bold green]Вы успешно вошли![/bold green]")
    else:
        console.print(
            "[bold red]Ошибка входа. Пожалуйста, проверьте свои данные.[/bold red]"
        )


@app.command()
def logout():
    delete_token()
    console.print("[bold yellow]Вы успешно вышли.[/bold yellow]")


@app.command()
def submit(
    task_id: str = typer.Argument(..., help="Код задачи (JOIN_CODE)"),
    files: List[str] = typer.Argument(..., help="Пути к файлам решения"),
):
    if not load_token():
        console.print(
            "[bold red]Ошибка: Вы должны войти в систему. Используйте 'cli login'.[/bold red]"
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
        None, "--task", help="Фильтр по коду задачи (JOIN_CODE)"
    ),
):
    if not load_token():
        console.print(
            "[bold red]Ошибка: Вы должны войти в систему. Используйте 'cli login'.[/bold red]"
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

            score = s.get("ai_score")
            score_str = f"{score / 10.0:.1f}" if score is not None else "N/A"

            table.add_row(
                str(s["id"])[:8],
                s.get("task_group_name", "N/A"),
                s.get("task_name", s["task_id"]),
                f"[{status_color}]{status_text}[/{status_color}]",
                score_str,
                s["timestamp"][:19].replace("T", " "),
            )

        console.print(table)
    except Exception as e:
        console.print(f"[bold red]Ошибка: {str(e)}[/bold red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
