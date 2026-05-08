import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import telebot
from telebot import types
from dotenv import load_dotenv
import sqlite3
import datetime

# Завантажуємо змінні з .env (для локального запуску)
load_dotenv()

# Отримуємо токен
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Захист: якщо токен не знайдено, програма видасть зрозумілу помилку
if not BOT_TOKEN:
    raise ValueError("Помилка: BOT_TOKEN не знайдено у змінних оточення!")

# Створюємо бота ПРАВИЛЬНО через telebot
bot = telebot.TeleBot(BOT_TOKEN)

# Назва файлу бази даних
DB_NAME = 'finance_v2.db'


# 1. Створення бази з колонкою дати
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL,
            category TEXT,
            date TEXT
        )
    ''')
    conn.commit()
    conn.close()


init_db()


# --- ДОПОМІЖНА ФУНКЦІЯ: КЛАВІАТУРА ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_stats = types.KeyboardButton("📊 Статистика")
    btn_help = types.KeyboardButton("ℹ️ Інструкція")
    btn_reset = types.KeyboardButton("🗑 Скинути все")

    markup.add(btn_stats, btn_help)
    markup.add(btn_reset)
    return markup


# --- КОМАНДИ ---

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id,
                     "Привіт! Я совість :D 🚀\n"
                     "Я вмію рахувати витрати за поточний місяць.\n\n"
                     "Щоб записати витрату, просто напиши: `100 їжа`",
                     reply_markup=main_menu())


# Обробка кнопки "Інструкція"
@bot.message_handler(func=lambda message: message.text == "ℹ️ Інструкція")
def show_help(message):
    bot.send_message(message.chat.id,
                     "Як користуватися:\n"
                     "1. Напиши суму і категорію: `50 кава` або `200 таксі`\n"
                     "2. Тисни '📊 Статистика', щоб побачити підсумок.\n"
                     "3. Тисни '🗑 Скинути все', щоб очистити базу.",
                     parse_mode="Markdown")


# 2. Статистика
@bot.message_handler(commands=['stats'])
@bot.message_handler(func=lambda message: message.text == "📊 Статистика")
def get_month_stats(message):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    current_month = datetime.datetime.now().strftime("%Y-%m")

    cursor.execute('''
        SELECT category, SUM(amount) 
        FROM expenses 
        WHERE date LIKE ? 
        GROUP BY category
    ''', (f'{current_month}%',))

    results = cursor.fetchall()
    conn.close()

    if not results:
        bot.send_message(message.chat.id, "У цьому місяці витрат ще не було. 🤷‍♂️")
        return

    text = f"📅 **Витрати за {current_month}:**\n\n"
    total_month = 0

    for row in results:
        category = row[0].capitalize()
        sum_amount = row[1]
        text += f"▫️ {category}: {sum_amount:.2f} грн\n"
        total_month += sum_amount

    text += f"\n💰 **Всього за місяць: {total_month:.2f} грн**"

    bot.send_message(message.chat.id, text, parse_mode="Markdown")


# Обробка скидання
@bot.message_handler(commands=['reset'])
@bot.message_handler(func=lambda message: message.text == "🗑 Скинути все")
def reset_db(message):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM expenses')
    conn.commit()
    conn.close()
    bot.send_message(message.chat.id, "🗑 Базу очищено! Починаємо з чистого аркуша.")


# 3. Додавання витрати
@bot.message_handler(content_types=['text'])
def add_expense(message):
    if message.text in ["📊 Статистика", "ℹ️ Інструкція", "🗑 Скинути все"]:
        return

    try:
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            bot.send_message(message.chat.id, "⚠️ Не зрозумів. Пиши так: `сума категорія`\nНаприклад: `150 продукти`",
                             parse_mode="Markdown")
            return

        amount = float(parts[0])
        category = parts[1].lower()

        today = datetime.datetime.now().strftime("%Y-%m-%d")

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('INSERT INTO expenses (amount, category, date) VALUES (?, ?, ?)',
                       (amount, category, today))
        conn.commit()
        conn.close()

        bot.send_message(message.chat.id, f"✅ Записав: {amount} грн на '{category}'")

    except ValueError:
        bot.send_message(message.chat.id, "⚠️ Сума має бути числом! (наприклад: 100 або 10.50)")


# --- ФЕЙКОВИЙ СЕРВЕР ДЛЯ RENDER ---
def keep_alive():
    class SimpleHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Bot is running!")

        def log_message(self, format, *args):
            pass

    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('', port), SimpleHandler)
    server.serve_forever()


threading.Thread(target=keep_alive, daemon=True).start()

# Запуск бота
bot.polling(none_stop=True)