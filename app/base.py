from contextlib import asynccontextmanager

from fasthtml.common import fast_app, Style

from app.services.mq import broker
from app.frontend.deps.auth import access_denied_handler
from app.storage.postgres import create_db_and_tables


@asynccontextmanager
async def lifespan(app):
    await create_db_and_tables()
    await broker.connect()
    yield
    await broker.stop()


app, rt = fast_app(
    exception_handlers={403: access_denied_handler},
    lifespan=lifespan,
    hdrs=(
        Style(
            """
            .progress-container { width: 300px; height: 10px; background-color: #f3f3f3; border: 1px solid #ccc; border-radius: 5px; position: relative; overflow: hidden; margin-top: 5px; margin-bottom: 5px; }
            .progress-bar { height: 100%; transition: width 0.3s ease; }
            .score-bar { background-color: #28a745; }
            .plagiarism-bar { background-color: #dc3545; }
            .submission-card { border: 1px solid #eee; padding: 20px; border-radius: 10px; margin-bottom: 30px; display: flex; gap: 40px; }
            .submission-info { flex: 1; }
            .submission-code { flex: 1; background: #fff; border: 1px solid #ccc; border-radius: 8px; overflow: auto; padding: 10px; min-width: 300px; font-family: monospace; white-space: pre-wrap; font-size: 0.9em; }
            .badge { padding: 5px 15px; border-radius: 10px; font-weight: bold; border: 2px solid; text-decoration: none; display: inline-block; margin-right: 10px; }
            .badge-plagiarism { border-color: #dc3545; color: #dc3545; }
            .badge-not-plagiarism { border-color: #28a745; color: #28a745; }
            """
        ),
    ),
)
