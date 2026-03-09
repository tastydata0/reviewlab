from fasthtml.common import *  # type: ignore
from app.base import rt


@rt("/")
def get():
    return Titled(
        "VKR",
        Main(H1("Hello!"), A("API", href="/api/hello")),
    )
