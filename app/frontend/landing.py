from fasthtml.common import *
from app.base import rt
from app.frontend.shared import render_header


@rt("/", methods=["GET"])
async def get_landing(session):
    header = await render_header(session, [("Главная", "/")])
    hero = Div(
        Div(
            H1("ReviewLab", style="font-size: 3.5rem; margin-bottom: 10px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;"),
            P("Умная система проверки кода и выявления плагиата в студенческих работах", style="font-size: 1.4rem; color: #555; margin-bottom: 30px;"),
            style="text-align: center; margin-bottom: 60px;",
        ),
        Div(
            Div(Div("🔍", style="font-size: 3rem; margin-bottom: 15px;"), H3("Автоматический анализ кода"), P("Мгновенная проверка стиля, качества и безопасности вашего кода с помощью ИИ", style="color: #666;"), style="text-align: center; padding: 30px;"),
            Div(Div("🛡️", style="font-size: 3rem; margin-bottom: 15px;"), H3("Обнаружение плагиата"), P("Проверка от лексического до семантического сходства кода", style="color: #666;"), style="text-align: center; padding: 30px;"),
            Div(Div("📊", style="font-size: 3rem; margin-bottom: 15px;"), H3("Конструктивная обратная связь"), P("Подробные рекомендации по улучшению кода вместо простых оценок", style="color: #666;"), style="text-align: center; padding: 30px;"),
            style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 30px; margin-bottom: 60px;",
        ),
        Div(A("Начать работу", href="/login", style="display: inline-block; padding: 15px 40px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 10px; text-decoration: none; font-size: 1.2rem; font-weight: 600;"), style="text-align: center;"),
        style="max-width: 1000px; margin: 0 auto; padding: 80px 20px;",
    )
    step3_text = "Используйте рекомендации для исправления ошибок"
    how_it_works = Div(
        H2("Как это работает", style="text-align: center; margin-bottom: 40px;"),
        Div(
            Div(Div("1", style="background: #667eea; color: white; width: 40px; height: 40px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; margin: 0 auto 15px;"), H3("Сдайте работу"), P("Загрузите исходный код через удобную форму", style="color: #666;"), style="text-align: center;"),
            Div(Div("2", style="background: #667eea; color: white; width: 40px; height: 40px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; margin: 0 auto 15px;"), H3("Получите анализ"), P("ИИ проверит стиль, качество и уникальность кода", style="color: #666;"), style="text-align: center;"),
            Div(Div("3", style="background: #667eea; color: white; width: 40px; height: 40px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; margin: 0 auto 15px;"), H3("Улучшайтесь"), P(step3_text, style="color: #666;"), style="text-align: center;"),
            style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 30px;",
        ),
        style="background: #f8f9fa; padding: 60px 20px;",
    )
    footer = Div(P("2026 ReviewLab. Умный анализ кода для образования.", style="text-align: center; color: #888;"), style="padding: 40px 20px;")
    main = Main(Div(hero, how_it_works, footer, style="min-height: 100vh;"))
    return Title("ReviewLab - Умный код-ревью и проверка на плагиат"), header, main