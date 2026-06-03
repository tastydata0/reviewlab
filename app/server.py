from fasthtml.common import serve
from fastapi import FastAPI
from ratelimit import RateLimitMiddleware, Rule
from ratelimit.backends.simple import MemoryBackend

from app.base import app
from app.api.submissions import router as api_submissions_router
from app.api.users import router as api_users_router
from app.api.tasks import router as api_tasks_router
from app.settings import SETTINGS

# регистрация роутов фронтенда
if 1:
    from app.frontend import users, courses, landing, labs, settings, submissions

api_app = FastAPI()
api_app.include_router(api_submissions_router)
api_app.include_router(api_users_router)
api_app.include_router(api_tasks_router)

app.mount("/api", api_app)


# Функция идентификации пользователя для лимитирования
async def authenticate(scope):
    # возвращаем (identity, group)
    return scope.get("client", ["unknown"])[0], "default"


# Оборачиваем приложение для лимитирования запросов
app = RateLimitMiddleware(
    app,
    authenticate,
    MemoryBackend(),
    {
        r"^/.*": [Rule(second=SETTINGS.RATE_LIMIT_RPS)],
    },
)


if __name__ == "__main__":
    serve()
