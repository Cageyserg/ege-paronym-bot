"""
Совместимость с деплоем на Render.

Исторически сервис запускался командой `gunicorn render_main:app`. Start Command
задан в дашборде Render и перекрывает `render.yaml`, поэтому удаление файла
ломало деплой (`ModuleNotFoundError: No module named 'render_main'`).

Здесь остаётся только алиас на настоящее приложение из web_app.py: логика
живёт в одном месте, а старая команда запуска продолжает работать.
"""

from web_app import app

__all__ = ["app"]
