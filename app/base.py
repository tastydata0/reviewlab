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
            .badge-plagiarism { border-color: #dc3545; color: #dc3545; color: #dc3545; }
            .badge-not-plagiarism { border-color: #28a745; color: #28a745; }
            .fab { position: fixed; bottom: 30px; right: 30px; width: 60px; height: 60px; border-radius: 50%; background-color: #007bff; color: white; display: flex; align-items: center; justify-content: center; font-size: 30px; box-shadow: 0 4px 10px rgba(0,0,0,0.3); cursor: pointer; text-decoration: none; border: none; }
            .fab:hover { background-color: #0056b3; color: white; }
            
            .card-grid { display: flex; flex-wrap: wrap; gap: 20px; margin-top: 20px; }
            .custom-card { 
                width: 300px; border: 1px solid #e0e0e0; border-radius: 12px; overflow: hidden; 
                transition: transform 0.2s, box-shadow 0.2s; cursor: pointer; text-decoration: none; color: inherit;
                display: flex; flex-direction: column; background: white;
            }
            .custom-card:hover { transform: translateY(-5px); box-shadow: 0 8px 25px rgba(0,0,0,0.1); color: inherit; border-color: #007bff; }
            .custom-card-top { 
                height: 100px; background-color: #f0f2f5; display: flex; align-items: center; 
                justify-content: flex-start; font-size: 50px; border-bottom: 1px solid #eee; padding-left: 20px;
            }
            .custom-card-body { padding: 15px; flex-grow: 1; display: flex; flex-direction: column; justify-content: space-between; }
            .custom-card-title { font-weight: bold; font-size: 1.1em; margin-bottom: 5px; color: #2c3e50; }
            .custom-card-desc { font-size: 0.9em; color: #7f8c8d; line-height: 1.4; }
            """
        ),
    ),
)
