"""
Главный файл бота для запуска на Render (webhook mode).
Использует Flask для обработки вебхуков от Telegram.
Архитектура: все данные в RAM, SQLite только для персистентности.
"""

import os
import sys
import signal
import logging
import atexit
from flask import Flask, request
import telebot

from config import BOT_TOKEN, WEBHOOK_URL

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализация DataManager с кэшированием
# import из utils.data_manager даёт модуль; data_manager — глобальный экземпляр
from utils import data_manager
from utils.database import Database

db = Database()

# init_data_manager идемпотентен: переиспользует модульный экземпляр (paronyms.json грузится один раз)
data_manager.init_data_manager(db)

# Flush-поток стартует НА ТОМ ЖЕ экземпляре, что и handlers — статистика не теряется
data_manager.data_manager.start_flush_loop()
logger.info("Flush loop started on data_manager instance")

# При graceful-stop (gunicorn SIGTERM, sys.exit) — финальный flush
# Единственная регистрация flush — здесь (не дублировать в utils/data_manager.py)
def _signal_handler(signum, frame):
    raise SystemExit(0)

atexit.register(data_manager.data_manager.stop_flush_loop)
signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)

# Flask приложение
app = Flask(__name__)

# Бот
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

# Импорты хендлеров (после dm инициализации)
from handlers.start import cmd_start, cmd_top, cmd_count
from handlers.callbacks import (
    show_main_menu, start_training,
    show_stats, show_leaderboard, handle_answer
)
from handlers.text_handler import handle_text_check

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

@bot.message_handler(func=lambda message: True, content_types=['text'])
def text_handler(message):
    if not message.text.startswith('/'):
        handle_text_check(message, bot)

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


# ==================== Webhook Routes ====================

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        if request.headers.get('content-type') == 'application/json':
            json_string = request.get_data().decode('utf-8')
            logger.info(f"Webhook received: {json_string[:200]}...")
            update = telebot.types.Update.de_json(json_string)
            bot.process_new_updates([update])
            return '', 200
        else:
            logger.warning(f"Wrong content-type: {request.headers.get('content-type')}")
            return 'Bad Request', 400
    except Exception as e:
        logger.error(f"Webhook error: {e}", exc_info=True)
        return 'Internal Server Error', 500

@app.route('/')
def index():
    return 'Bot working! 🤖'

@app.route('/set-webhook', methods=['GET', 'POST'])
def set_webhook():
    webhook_url = f"{WEBHOOK_URL}/webhook"
    bot.remove_webhook()
    bot.set_webhook(url=webhook_url)
    return f'Webhook set to {webhook_url}'


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("Starting bot in webhook mode...", flush=True)
    app.run(host='0.0.0.0', port=port)
