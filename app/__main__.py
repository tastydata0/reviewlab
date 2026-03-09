import uvicorn

if 1:
    from app.settings import SETTINGS


def main():
    uvicorn.run("app.server:app", host="0.0.0.0", port=8080, reload=True)


if __name__ == "__main__":
    main()
