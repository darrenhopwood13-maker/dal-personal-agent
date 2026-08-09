import os
import time
from collections import defaultdict, deque

import requests
from openai import OpenAI


TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

if not TELEGRAM_TOKEN:
    raise RuntimeError("Missing TELEGRAM_TOKEN environment variable")

if not DEEPSEEK_API_KEY:
    raise RuntimeError("Missing DEEPSEEK_API_KEY environment variable")


client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com",
)

MODEL = "deepseek-v4-flash"

TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"


SYSTEM_PROMPT = """
You are Dal's personal AI agent.

You are being built as a long-term personal agent for Dal.

Your job is to be:
- intelligent
- practical
- direct
- honest
- proactive when you have the tools to act
- willing to challenge bad ideas

Do not give empty praise.

If something is a bad idea, say so and explain why.

You will eventually have tools for:
- GitHub
- web research
- Chrome/browser automation
- Supabase
- Lovable
- app and UI review
- competitor research
- coding and development
- file analysis

For now, you only have conversation access.

Never claim that you have accessed a service or completed an action
unless you actually have a tool that allows you to do it.

Keep normal replies reasonably concise unless Dal asks for detail.
"""


history = defaultdict(lambda: deque(maxlen=20))


def telegram_request(method, **kwargs):
    response = requests.post(
        f"{TELEGRAM_API}/{method}",
        json=kwargs,
        timeout=40,
    )

    response.raise_for_status()

    data = response.json()

    if not data.get("ok"):
        raise RuntimeError(f"Telegram API error: {data}")

    return data


def send_message(chat_id, text):
    if not text:
        text = "I couldn't generate a response."

    # Telegram has a message size limit.
    for start in range(0, len(text), 4000):
        telegram_request(
            "sendMessage",
            chat_id=chat_id,
            text=text[start:start + 4000],
        )


def ask_ai(chat_id, message):

    history[chat_id].append(
        {
            "role": "user",
            "content": message,
        }
    )

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        }
    ]

    messages.extend(history[chat_id])

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.4,
    )

    reply = response.choices[0].message.content

    if not reply:
        reply = "I didn't get a usable response."

    history[chat_id].append(
        {
            "role": "assistant",
            "content": reply,
        }
    )

    return reply


def main():

    print(f"Dal Agent starting with {MODEL}...")

    offset = None

    while True:

        try:

            response = requests.get(
                f"{TELEGRAM_API}/getUpdates",
                params={
                    "timeout": 30,
                    "offset": offset,
                },
                timeout=40,
            )

            response.raise_for_status()

            data = response.json()

            for update in data.get("result", []):

                offset = update["update_id"] + 1

                message = update.get("message")

                if not message:
                    continue

                chat_id = message["chat"]["id"]

                text = (message.get("text") or "").strip()

                if not text:
                    continue

                print(
                    f"Telegram message from {chat_id}: "
                    f"{text[:200]}"
                )

                try:

                    reply = ask_ai(chat_id, text)

                    send_message(
                        chat_id,
                        reply,
                    )

                except Exception as exc:

                    print(f"Agent error: {exc}")

                    send_message(
                        chat_id,
                        "I hit an error while processing that. "
                        "Check the Railway logs and try again.",
                    )

        except requests.RequestException as exc:

            print(f"Telegram connection error: {exc}")

            time.sleep(5)

        except Exception as exc:

            print(f"Unexpected error: {exc}")

            time.sleep(5)


if __name__ == "__main__":
    main()