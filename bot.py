import os
import telebot
import requests
import re
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import sys # Добавим sys для выхода, если нет токена

# --- Получение настроек из переменных окружения ---
BOT_TOKEN = os.environ.get('BOT_TOKEN')
API_URL = os.environ.get('API_URL') # Получаем URL API

# --- Проверка наличия токена ---
if not BOT_TOKEN:
    print("CRITICAL ERROR: BOT_TOKEN environment variable not found!")
    sys.exit(1) # Выходим из программы, если токен не найден

# --- Проверка наличия URL API ---
if not API_URL:
    print("WARNING: API_URL environment variable not found. Using default (if any) or requests might fail.")
    # Можно либо задать значение по умолчанию, либо просто предупредить
    # API_URL = 'https://default.api.example.com' # Пример значения по умолчанию

# --- Инициализация бота ---
bot = telebot.TeleBot(BOT_TOKEN)
print("Bot initialized successfully.") # Добавим сообщение для логов

# --- ДОБАВЬ ЭТОТ ОБРАБОТЧИК СЮДА ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    print(f"Received /start command from chat ID: {message.chat.id}") # Логирование
    try:
        bot.reply_to(message, "Привіт! Я бот для підтвердження.")
        print(f"Sent welcome message to chat ID: {message.chat.id}") # Логирование
    except Exception as e:
        print(f"Error sending welcome message: {e}") # Логирование ошибки
# --- КОНЕЦ ДОБАВЛЕННОГО ОБРАБОТЧИКА ---

# --- Обработчик сообщений с кодом подтверждения ---
@bot.message_handler(func=lambda m: isinstance(m.text, str) and "Код підтвердження:" in m.text)
def handle_code(m):
    print(f"Received potential code message from chat ID: {m.chat.id}") # Логирование
    phone_match = re.search(r"Телефон:\s*([+\d\s()-]+)", m.text) # Немного расширим рег. выражение для телефона
    phone = phone_match.group(1).strip() if phone_match else "невідомий"

    if phone == "невідомий":
        print("Could not parse phone number from message.") # Логирование

    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("✅ Так", callback_data=f"confirm_yes_{phone}"),
        InlineKeyboardButton("❌ Ні", callback_data=f"confirm_no_{phone}")
    )
    try:
        bot.send_message(m.chat.id, f"{m.text}\n\nПідтвердити ці дані?", reply_markup=markup)
        print(f"Sent confirmation request for phone: {phone}") # Логирование
    except Exception as e:
        print(f"Error sending confirmation message: {e}") # Логирование ошибки отправки

# --- Обработчик нажатий на кнопки ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_"))
def handle_callback(call):
    print(f"Received callback query: {call.data} from chat ID: {call.message.chat.id}") # Логирование
    status = "unknown"
    phone = "unknown"
    try:
        data = call.data
        if data.startswith("confirm_yes_"):
            phone = data.replace("confirm_yes_", "")
            status = "approved"
        elif data.startswith("confirm_no_"):
            phone = data.replace("confirm_no_", "")
            status = "rejected"
        else:
            print(f"Invalid callback data format: {data}") # Логирование
            bot.answer_callback_query(call.id, "⚠️ Некоректний формат даних")
            bot.edit_message_text("⚠️ Некоректний формат даних.", call.message.chat.id, call.message.message_id)
            return

        # --- Отправка данных на бэкенд ---
        if not API_URL:
             print("ERROR: API_URL is not set. Cannot send data to backend.")
             bot.answer_callback_query(call.id, "Помилка: Не налаштовано URL сервера.")
             bot.edit_message_text("⚠️ Помилка конфігурації сервера.", call.message.chat.id, call.message.message_id)
             return

        backend_url = f"{API_URL}/user-request" # Собираем полный URL
        payload = {"phone": phone, "result": status}
        print(f"Sending data to backend: {backend_url} with payload: {payload}") # Логирование

        try:
            response = requests.post(backend_url, json=payload, timeout=10) # Добавим таймаут
            response.raise_for_status() # Проверяем на ошибки HTTP (4xx, 5xx)

            # Если запрос успешен
            print(f"Backend request successful. Status code: {response.status_code}") # Логирование
            confirmation_text = f"✅ Дані прийняті: {status}\nТелефон: {phone}"
            bot.answer_callback_query(call.id, f"Дані для {phone} прийняті.") # Ответ на колбэк
            bot.edit_message_text(confirmation_text, call.message.chat.id, call.message.message_id, reply_markup=None) # Убираем кнопки

        except requests.exceptions.RequestException as e:
            # Ошибка сети, таймаут, DNS или HTTP ошибка
            print(f"ERROR sending data to backend: {e}") # Логирование
            error_text = f"⚠️ Помилка зв'язку з сервером.\nСпробуйте пізніше."
            bot.answer_callback_query(call.id, "Помилка сервера.")
            # Не редактируем сообщение, чтобы пользователь мог попробовать еще раз? Или редактируем с ошибкой.
            bot.edit_message_text(error_text, call.message.chat.id, call.message.message_id)

    except Exception as e:
        # Другие непредвиденные ошибки
        print(f"UNEXPECTED ERROR in callback handler: {e}") # Логирование
        error_text = f"⚠️ Невідома помилка обробки."
        bot.answer_callback_query(call.id, "Невідома помилка.")
        try:
            # Попытаемся отредактировать сообщение с ошибкой
             bot.edit_message_text(error_text, call.message.chat.id, call.message.message_id)
        except Exception as edit_e:
             print(f"Could not edit message after error: {edit_e}") # Логирование, если даже редактирование не удалось

# --- Запуск бота ---
if __name__ == '__main__': # Хорошая практика для запуска основного кода
    print("Starting bot polling...")
    try:
        bot.infinity_polling(skip_pending=True) # skip_pending=True - чтобы не обрабатывать старые сообщения после перезапуска
    except Exception as e:
        print(f"ERROR during bot polling: {e}") # Логирование критической ошибки поллинга
        # Здесь можно добавить логику перезапуска или уведомления
        sys.exit(1) # Выходим с ошибкой, чтобы система (Railway) могла его перезапустить
