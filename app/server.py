from fasthtml.common import serve
from fastapi import FastAPI
from app.base import app
from app.api.submissions import router as api_submissions_router
from app.api.users import router as api_users_router
from app.api.tasks import router as api_tasks_router

# регистрация роутов фронтенда
if 1:
    from app.frontend import users, courses, landing, labs, settings, submissions

api_app = FastAPI()
api_app.include_router(api_submissions_router)
api_app.include_router(api_users_router)
api_app.include_router(api_tasks_router)

app.mount("/api", api_app)


if __name__ == "__main__":
    serve()
