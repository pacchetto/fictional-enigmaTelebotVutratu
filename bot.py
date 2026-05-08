import os

from aiogram import Bot
from dotenv import load_dotenv
from telebot import types  # Додали для кнопок
import sqlite3
import datetime

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)

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
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)  # resize=True робить кнопки меншими
    btn_stats = types.KeyboardButton("📊 Статистика")
    btn_help = types.KeyboardButton("ℹ️ Інструкція")
    btn_reset = types.KeyboardButton("🗑 Скинути все")

    # Додаємо кнопки: Статистика та Інструкція в один ряд, Скинути - в другий
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
                     reply_markup=main_menu())  # Додаємо клавіатуру


# Обробка кнопки "Інструкція"
@bot.message_handler(func=lambda message: message.text == "ℹ️ Інструкція")
def show_help(message):
    bot.send_message(message.chat.id,
                     "Як користуватися:\n"
                     "1. Напиши суму і категорію: `50 кава` або `200 таксі`\n"
                     "2. Тисни '📊 Статистика', щоб побачити підсумок.\n"
                     "3. Тисни '🗑 Скинути все', щоб очистити базу.",
                     parse_mode="Markdown")


# 2. Статистика (спрацьовує і на команду, і на кнопку)
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
        category = row[0].capitalize()  # Робимо першу літеру великою для краси
        sum_amount = row[1]
        text += f"▫️ {category}: {sum_amount:.2f} грн\n"
        total_month += sum_amount

    text += f"\n💰 **Всього за місяць: {total_month:.2f} грн**"

    bot.send_message(message.chat.id, text, parse_mode="Markdown")


# Обробка скидання (команда і кнопка)
@bot.message_handler(commands=['reset'])
@bot.message_handler(func=lambda message: message.text == "🗑 Скинути все")
def reset_db(message):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM expenses')
    conn.commit()
    conn.close()
    bot.send_message(message.chat.id, "🗑 Базу очищено! Починаємо з чистого аркуша.")


# 3. Додавання витрати (ловле весь інший текст)
@bot.message_handler(content_types=['text'])
def add_expense(message):
    # Перевірка, щоб випадково не обробляти текст кнопок, якщо нові додаси
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


bot.polling(none_stop=True)