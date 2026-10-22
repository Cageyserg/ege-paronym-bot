"""
Главный файл бота для запуска на Render (webhook mode).
Использует Flask для обработки вебхуков от Telegram.
"""

import os
import logging
from flask import Flask, request
import telebot
from config import BOT_TOKEN, WEBHOOK_URL
from handlers.start import cmd_start
from handlers.callbacks import (
    show_main_menu, start_training, handle_answer, next_question,
    show_dictionary, dict_prev_page, dict_next_page, show_stats,
    show_check_text_instruction, show_leaderboard
)
from handlers.text_handler import handle_text_check

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Создаём Flask приложение
app = Flask(__name__)

# Создаём экземпляр бота
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

# Регистрируем обработчики
@bot.message_handler(commands=['start'])
def start_handler(message):
    cmd_start(message, bot)

# Обработчик текстовых сообщений (проверка текста)
@bot.message_handler(func=lambda message: True, content_types=['text'])
def text_handler(message):
    # Если это не команда, обрабатываем как проверку текста
    if not message.text.startswith('/'):
        handle_text_check(message, bot)

# Callback обработчики
@bot.callback_query_handler(func=lambda call: call.data == "main_menu")
def main_menu_handler(call):
    show_main_menu(call, bot)

@bot.callback_query_handler(func=lambda call: call.data == "training_start")
def training_start_handler(call):
    start_training(call, bot)

@bot.callback_query_handler(func=lambda call: call.data.startswith("answer_"))
def answer_handler(call):
    handle_answer(call, bot)

@bot.callback_query_handler(func=lambda call: call.data == "next_question")
def next_question_handler(call):
    next_question(call, bot)

@bot.callback_query_handler(func=lambda call: call.data == "dictionary")
def dictionary_handler(call):
    show_dictionary(call, bot)

@bot.callback_query_handler(func=lambda call: call.data.startswith("dict_prev_"))
def dict_prev_handler(call):
    dict_prev_page(call, bot)

@bot.callback_query_handler(func=lambda call: call.data.startswith("dict_next_"))
def dict_next_handler(call):
    dict_next_page(call, bot)

@bot.callback_query_handler(func=lambda call: call.data == "stats")
def stats_handler(call):
    show_stats(call, bot)

@bot.callback_query_handler(func=lambda call: call.data == "check_text")
def check_text_handler(call):
    show_check_text_instruction(call, bot)

@bot.callback_query_handler(func=lambda call: call.data == "leaderboard")
def leaderboard_handler(call):
    show_leaderboard(call, bot)


@app.route('/webhook', methods=['POST'])
def webhook():
    """Обработчик вебхуков от Telegram."""
    try:
        if request.headers.get('content-type') == 'application/json':
            json_string = request.get_data().decode('utf-8')
            logger.info(f"Получен webhook: {json_string[:200]}...")
            update = telebot.types.Update.de_json(json_string)
            bot.process_new_updates([update])
            logger.info("Webhook обработан успешно")
            return '', 200
        else:
            logger.warning(f"Неправильный content-type: {request.headers.get('content-type')}")
            return 'Bad Request', 400
    except Exception as e:
        logger.error(f"Ошибка при обработке webhook: {e}", exc_info=True)
        return 'Internal Server Error', 500


@app.route('/')
def index():
    """Главная страница для проверки работы сервиса."""
    return 'Бот работает! 🤖'


@app.route('/set-webhook', methods=['GET', 'POST'])
def set_webhook():
    """Устанавливает вебхук для бота."""
    webhook_url = f"{WEBHOOK_URL}/webhook"
    bot.remove_webhook()
    bot.set_webhook(url=webhook_url)
    return f'Webhook установлен на {webhook_url}'


if __name__ == '__main__':
    # Получаем порт из переменной окружения Render
    port = int(os.environ.get('PORT', 5000))
    
    # Запуск бота в режиме webhook
    logger.info("Запуск бота в режиме webhook...")
    logger.info(f"BOT_TOKEN: {BOT_TOKEN[:10]}...")
    logger.info(f"WEBHOOK_URL: {WEBHOOK_URL}")
    
    # Вебхук уже установлен через API, не устанавливаем повторно
    logger.info("Вебхук должен быть уже установлен через API")
    
    # Запускаем Flask приложение
    logger.info(f"Запуск Flask на порту {port}")
    app.run(host='0.0.0.0', port=port)
