"""
Главный файл бота для подготовки к ЕГЭ по паронимам.
Запускает бота и регистрирует все обработчики.
Использует библиотеку pyTelegramBotAPI (telebot).
"""

import telebot
from config import BOT_TOKEN
from handlers.start import cmd_start
from handlers.callbacks import (
    show_main_menu, start_training, handle_answer, next_question,
    show_dictionary, dict_prev_page, dict_next_page, show_stats,
    show_check_text_instruction, show_leaderboard
)
from handlers.text_handler import handle_text_check

# Создаём экземпляр бота
bot = telebot.TeleBot(BOT_TOKEN)

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

if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    print("Бот запущен!", flush=True)
    try:
        bot.infinity_polling()
    except Exception as e:
        print(f"Ошибка: {e}", flush=True)
