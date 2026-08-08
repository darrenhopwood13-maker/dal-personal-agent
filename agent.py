import os
import requests
from openai import OpenAI

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

client = OpenAI(api_key=OPENAI_API_KEY)

TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"


def send_message(chat_id, text):
    requests.post(
        f"{TELEGRAM_API}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": text
        }
    )


def ask_ai(message):
    response = client.responses.create(
        model="gpt-5",
        input=message
    )

    return response.output_text


def main():
    print("Dal Agent is starting...")

    offset = None

    while True:
        response = requests.get(
            f"{TELEGRAM_API}/getUpdates",
            params={
                "timeout": 30,
                "offset": offset
            }
        ).json()

        for update in response.get("result", []):
            offset = update["update_id"] + 1

            message = update.get("message")

            if not message:
                continue

            chat_id = message["chat"]["id"]
            text = message.get("text", "")

            if not text:
                continue

            print(f"Dal said: {text}")

            reply = ask_ai(text)

            send_message(chat_id, reply)


if __name__ == "__main__":
    main()
