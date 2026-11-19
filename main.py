"""
Запуск бота в режиме long polling (локально, VPS).

В памяти живёт только состояние текущей тренировки; статистика пишется
напрямую в MongoDB.
"""

import atexit
import logging
import signal
import sys

from config import is_configured, is_storage_configured
from core.bot_core import build_bot, init_storage, shutdown_storage
from utils.mongo_database import StorageUnavailable

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

bot = build_bot()
storage = None
if is_storage_configured():
    try:
        storage = init_storage()
    except StorageUnavailable as e:
        logger.error("MongoDB недоступна: %s", e)

# Единственная регистрация остановки: atexit сработает и на SIGTERM/SIGINT.
if storage is not None:
    atexit.register(shutdown_storage, storage)
atexit.register(bot.stop_polling)


def _signal_handler(signum, frame):
    raise SystemExit(0)


signal.signal(signal.SIGTERM, _signal_handler)
signal.signal(signal.SIGINT, _signal_handler)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if not is_configured():
        logger.error("BOT_TOKEN не задан. Скопируйте .env.example в .env и укажите токен.")
        raise SystemExit(1)
    if storage is None:
        logger.error(
            "MONGODB_URI не задан или MongoDB недоступна. Статистика хранится "
            "только в MongoDB — без неё бот не запускается."
        )
        raise SystemExit(1)
    logger.info("Бот запущен (long polling, статистика в MongoDB)")
    try:
        bot.infinity_polling(skip_pending=True)
    except Exception as e:
        logger.error("Ошибка polling: %s", e, exc_info=True)
        raise SystemExit(1) from e
