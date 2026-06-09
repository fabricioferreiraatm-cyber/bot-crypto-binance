import os
import time
import requests

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

while True:
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

        requests.post(
            url,
            data={
                "chat_id": CHAT_ID,
                "text": "🚀 Bot funcionando!"
            }
        )

        print("Mensagem enviada")

    except Exception as erro:
        print("ERRO:", erro)

    time.sleep(900)