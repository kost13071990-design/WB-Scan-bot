import telebot
import requests
import json
import time
import schedule
import threading
import os

TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

DATA_FILE = "prices.json"


def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)


def extract_nm_id(url):
    try:
        return url.split("/catalog/")[1].split("/")[0]
    except:
        return None


def get_price(nm_id):
    url = f"https://card.wb.ru/cards/v1/detail?nm={nm_id}"
    r = requests.get(url, timeout=10)
    product = r.json()["data"]["products"][0]
    return product["salePriceU"] // 100


@bot.message_handler(commands=["start"])
def start(msg):
    bot.send_message(
        msg.chat.id,
        "👋 Отправь ссылку на товар Wildberries — я буду следить за ценой."
    )


@bot.message_handler(func=lambda m: "wildberries.ru/catalog" in m.text)
def add_product(msg):
    nm_id = extract_nm_id(msg.text)
    if not nm_id:
        bot.send_message(msg.chat.id, "❌ Не смог распознать ссылку.")
        return

    price = get_price(nm_id)
    data = load_data()

    data[nm_id] = {
        "chat_id": msg.chat.id,
        "price": price,
        "url": msg.text
    }

    save_data(data)

    bot.send_message(
        msg.chat.id,
        f"✅ Товар добавлен\n💰 Текущая цена: {price} ₽"
    )


def check_prices():
    data = load_data()

    for nm_id, item in data.items():
        try:
            new_price = get_price(nm_id)
            old_price = item["price"]

            if new_price < old_price:
                bot.send_message(
                    item["chat_id"],
                    f"🔥 Цена снизилась!\n"
                    f"Было: {old_price} ₽\n"
                    f"Стало: {new_price} ₽\n"
                    f"{item['url']}"
                )

            item["price"] = new_price

        except Exception as e:
            print(e)

    save_data(data)


def scheduler():
    schedule.every(30).minutes.do(check_prices)
    while True:
        schedule.run_pending()
        time.sleep(1)


threading.Thread(target=scheduler).start()
bot.infinity_polling()
