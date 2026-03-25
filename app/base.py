from contextlib import asynccontextmanager

from fasthtml.common import fast_app

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
)
