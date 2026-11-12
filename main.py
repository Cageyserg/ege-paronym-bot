"""
Главный файл бота для подготовки к ЕГЭ по паронимам.
Использует pyTelegramBotAPI (telebot).
Архитектура: все данные в RAM, SQLite только для персистентности.
"""

import sys
import signal
import telebot
import logging

from config import BOT_TOKEN
import atexit

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)

from utils.data_manager import init_data_manager, data_manager
from utils.database import Database
from handlers.start import cmd_start, cmd_top, cmd_count
from handlers.callbacks import (
    show_main_menu, start_training,
    show_stats, show_leaderboard, handle_answer
)
from handlers.text_handler import handle_text_check

# Создаём экземпляр бота
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

# Инициализация DataManager с БД (кэширует user_stats в RAM)
from config import MONGODB_URI
if MONGODB_URI:
    from utils.mongo_database import MongoDatabase
    db = MongoDatabase(MONGODB_URI)
else:
    db = Database()
init_data_manager(db)
data_manager.start_flush_loop()

# Graceful shutdown: atexit вызовет stop_flush_loop, signal handler просто ставит выход
def _signal_handler(signum, frame):
    raise SystemExit(0)

signal.signal(signal.SIGTERM, _signal_handler)
signal.signal(signal.SIGINT, _signal_handler)

# Единственная регистрация flush-а — здесь (не дублировать в utils/data_manager.py)
atexit.register(data_manager.stop_flush_loop)
atexit.register(bot.close_polling)
# ==================== Handlers ====================

@bot.message_handler(commands=['start'])
def start_handler(message):
    cmd_start(message, bot)

@bot.message_handler(commands=['top'])
def top_handler(message):
    cmd_top(message, bot)

@bot.message_handler(commands=['count'])
def count_handler(message):
    cmd_count(message, bot)

# Обработчик текстовых сообщений (не используется — ответы через кнопки)
@bot.message_handler(func=lambda message: True, content_types=['text'])
def text_handler(message):
    if not message.text.startswith('/'):
        handle_text_check(message, bot)

# Callback обработчики
@bot.callback_query_handler(func=lambda call: call.data == "main_menu")
def main_menu_handler(call):
    show_main_menu(call, bot)

@bot.callback_query_handler(func=lambda call: call.data == "training_start")
def training_start_handler(call):
    start_training(call, bot)

@bot.callback_query_handler(func=lambda call: call.data == "stats")
def stats_handler(call):
    show_stats(call, bot)

@bot.callback_query_handler(func=lambda call: call.data == "leaderboard")
def leaderboard_handler(call):
    show_leaderboard(call, bot)

@bot.callback_query_handler(func=lambda call: call.data.startswith("answer_"))
def answer_handler(call):
    handle_answer(call, bot)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8')
    print("Бот запущен! (кэширование активно, flush каждые 10с)", flush=True)
    try:
        bot.infinity_polling()
    except Exception as e:
        print(f"Ошибка: {e}", flush=True)
