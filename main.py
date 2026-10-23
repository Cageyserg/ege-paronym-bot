"""
Главный файл бота для подготовки к ЕГЭ по паронимам.
Запускает бота и регистрирует все обработчики.
Использует библиотеку pyTelegramBotAPI (telebot).
"""

import telebot
from config import BOT_TOKEN
from handlers.start import cmd_start, cmd_top, cmd_count
from handlers.callbacks import (
    show_main_menu, start_training,
    show_stats, show_leaderboard, handle_answer
)
from handlers.text_handler import handle_text_check

# Создаём экземпляр бота
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

# Регистрируем обработчики команд
@bot.message_handler(commands=['start'])
def start_handler(message):
    cmd_start(message, bot)

@bot.message_handler(commands=['top'])
def top_handler(message):
    cmd_top(message, bot)

@bot.message_handler(commands=['count'])
def count_handler(message):
    cmd_count(message, bot)

# Обработчик текстовых сообщений (проверка текста и тренировка)
@bot.message_handler(func=lambda message: True, content_types=['text'])
def text_handler(message):
    # Если это не команда, обрабатываем
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
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    print("Бот запущен!", flush=True)
    try:
        bot.infinity_polling()
    except Exception as e:
        print(f"Ошибка: {e}", flush=True)
