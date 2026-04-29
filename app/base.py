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
            .correctness-bar { background-color: #007bff; }
            .plagiarism-bar { background-color: #dc3545; }
            .submission-card { border: 1px solid #eee; padding: 20px; border-radius: 10px; margin-bottom: 30px; display: flex; gap: 40px; }
            .submission-info { flex: 1; }
            .submission-code { flex: 1; background: #fff; border: 1px solid #ccc; border-radius: 8px; overflow: auto; padding: 10px; min-width: 300px; font-family: monospace; white-space: pre-wrap; font-size: 0.9em; }
            .badge { padding: 5px 15px; border-radius: 10px; font-weight: bold; border: 2px solid; text-decoration: none; display: inline-block; margin-right: 10px; }
            .badge-plagiarism { border-color: #dc3545; color: #dc3545; }
            .badge-not-plagiarism { border-color: #28a745; color: #28a745; }
            .badge-best { border-color: #ffd700; color: #b8860b; background-color: #fff9e6; margin-bottom: 10px; }
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
            .custom-card-add { 
                width: 300px; border: 2px dashed #ccc; border-radius: 12px; 
                display: flex; align-items: center; justify-content: center; font-size: 40px; 
                color: #ccc; cursor: pointer; transition: all 0.2s; background: transparent;
            }
            .custom-card-add:hover { border-color: #007bff; color: #007bff; background: rgba(0,123,255,0.05); }
            
            .custom-header { display: flex; justify-content: space-between; align-items: center; padding: 10px 0; margin-bottom: 20px; border-bottom: 1px solid #eee; }
            .custom-breadcrumbs { display: flex; align-items: center; gap: 5px; }
            .custom-breadcrumb-item { padding: 5px 10px; border-radius: 5px; transition: background 0.2s; color: #555; text-decoration: none; display: flex; align-items: center; gap: 5px; }
            .custom-breadcrumb-item:hover { background: #f0f0f0; color: #000; }
            .custom-breadcrumb-separator { color: #ccc; display: flex; align-items: center; }
            .custom-user-nav { display: flex; align-items: center; gap: 5px; }
            .custom-user-link { padding: 5px 10px; border-radius: 5px; transition: background 0.2s; color: #888; text-decoration: none; }
            .custom-user-link:hover { background: #f0f0f0; color: #555; }
            
            /* Стили для выпадающего списка (бургер-меню) */
            .custom-nav-dropdown { position: relative; display: flex; align-items: center; margin-right: 5px; height: 34px; width: 40px; box-sizing: border-box; }
            .custom-nav-dropdown details { margin: 0; border: none; padding: 0; display: flex; align-items: center; height: 34px; width: 40px; }
            .custom-nav-dropdown details[open] summary { margin-bottom: 0; }
            .custom-nav-dropdown summary { 
                list-style: none; padding: 0; border-radius: 5px; cursor: pointer; color: #555; 
                font-size: 1.2rem; transition: background 0.2s; display: flex; align-items: center; justify-content: center;
                height: 34px; width: 40px; line-height: 1; outline: none;
            }
            .custom-nav-dropdown summary:hover { background: #f0f0f0; color: #000; }
            .custom-nav-dropdown summary::-webkit-details-marker { display: none; }
            .custom-nav-dropdown ul { 
                position: absolute; left: 0; top: 34px; background: white; border: 1px solid #eee; 
                border-radius: 8px; box-shadow: 0 8px 25px rgba(0,0,0,0.1); list-style: none; 
                padding: 10px 0; margin: 5px 0 0 0; min-width: 200px; z-index: 1000; 
            }
            .custom-nav-dropdown li { padding: 0; margin: 0; list-style: none; }
            .custom-nav-dropdown li::before { content: none; }
            .custom-nav-dropdown li a { 
                display: block; padding: 8px 20px; color: #333; text-decoration: none; transition: background 0.2s; 
            }
            .custom-nav-dropdown li a:hover { background: #f8f9fa; color: #007bff; }
            
            .custom-nav-spacer { width: 45px; display: inline-block; }

            /* Стили для таблиц */
            .custom-table-container { background: white; border-radius: 12px; border: 1px solid #eee; overflow: hidden; margin: 20px 0; }
            .custom-table { width: 100%; border-collapse: collapse; margin: 0; }
            .custom-table th { background: #f8f9fa; color: #7f8c8d; font-weight: 600; text-transform: uppercase; font-size: 0.8rem; letter-spacing: 0.5px; padding: 15px 20px; text-align: left; border-bottom: 1px solid #eee; }
            .custom-table td { padding: 15px 20px; border-bottom: 1px solid #eee; vertical-align: middle; }
            .custom-table tr:last-child td { border-bottom: none; }
            .custom-table tr:hover td { background-color: #fafafa; }
            
            /* Кнопки в едином стиле */
            button:not(.fab), .button:not(.fab), .btn-custom { 
                padding: 8px 16px; border-radius: 8px; background: transparent; 
                border: 1px solid #007bff; color: #007bff; cursor: pointer; 
                transition: all 0.2s; font-size: 0.9rem; font-weight: 500;
                display: inline-flex; align-items: center; justify-content: center; text-decoration: none;
            }
            button:not(.fab):hover, .button:not(.fab):hover, .btn-custom:hover { background: #007bff; color: white; }
            
            .btn-primary { border-color: #007bff; color: #007bff; }
            .btn-primary:hover { background: #007bff; color: white; }
            
            .btn-danger { border-color: #dc3545 !important; color: #dc3545 !important; }
            .btn-danger:hover { background: #dc3545 !important; color: white !important; }
            
            .btn-secondary { border-color: #6c757d !important; color: #6c757d !important; }
            .btn-secondary:hover { background: #6c757d !important; color: white !important; }
            """
        ),
    ),
)
