from fasthtml.common import serve
from fastapi import FastAPI
from app.base import app
from app.api.hello import router as api_hello_router
from app.api.submissions import router as api_submissions_router
from app.api.users import router as api_users_router

# регистрация роутов фронтенда
if 1:
    from app.frontend import hello, users, courses

api_app = FastAPI(title="VKR API")
api_app.include_router(api_hello_router)
api_app.include_router(api_submissions_router)
api_app.include_router(api_users_router)

app.mount("/api", api_app)


if __name__ == "__main__":
    serve()
