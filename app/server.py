from fasthtml.common import serve
from fastapi import FastAPI
from app.base import app
from app.api.hello import router as api_hello_router

# регистрация роутов фронтенда
if 1:
    from app.frontend import hello

api_app = FastAPI(title="VKR API")
api_app.include_router(api_hello_router)

app.mount("/api", api_app)

if __name__ == "__main__":
    serve()
