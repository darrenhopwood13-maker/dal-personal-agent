"""Delivery to Telegram, plus the episode counter.

State lives in one small JSON file next to the audio. It holds the last
episode number and the last date an episode went out, which is what stops the
hourly cron sending twice if it fires twice in the same hour.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

from config import DATA_DIR, SHOW_TITLE, TIMEZONE

STATE_FILE = "state.json"


def _data_dir():
    directory = Path(DATA_DIR)

    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError:
        directory = Path("./podcast-data")
        directory.mkdir(parents=True, exist_ok=True)

    return directory


def read_state():
    path = _data_dir() / STATE_FILE

    if not path.exists():
        return {"episode": 0, "last_sent_date": None}

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {"episode": 0, "last_sent_date": None}


def write_state(state):
    (_data_dir() / STATE_FILE).write_text(
        json.dumps(state, indent=2), encoding="utf-8"
    )
    return state


def today():
    return datetime.now(ZoneInfo(TIMEZONE)).date()


def already_sent_today():
    return read_state().get("last_sent_date") == today().isoformat()


def next_episode_number():
    return int(read_state().get("episode", 0)) + 1


def record_sent(episode_number):
    state = read_state()
    state["episode"] = int(episode_number)
    state["last_sent_date"] = today().isoformat()
    return write_state(state)


def _telegram(method, files=None, **data):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")

    response = requests.post(
        f"https://api.telegram.org/bot{token}/{method}",
        data={key: value for key, value in data.items() if value is not None},
        files=files,
        timeout=180,
    )

    payload = {}
    try:
        payload = response.json()
    except ValueError:
        pass

    if not payload.get("ok"):
        raise RuntimeError(
            f"Telegram {method} failed ({response.status_code}): "
            f"{payload or response.text[:300]}"
        )

    return payload


def _chat_id():
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not chat_id:
        raise RuntimeError("TELEGRAM_CHAT_ID is not set")
    return chat_id


def send_note(text):
    """Plain text, used for warnings and failures."""

    return _telegram("sendMessage", chat_id=_chat_id(), text=text[:4000])


def send_episode(audio_path, episode_number, subtitle=None):
    """Voice note if we managed to make an OGG, audio file otherwise."""

    audio_path = Path(audio_path)
    caption = f"{SHOW_TITLE} - episode {episode_number}"

    if subtitle:
        caption = f"{caption}. {subtitle}"

    with open(audio_path, "rb") as handle:
        if audio_path.suffix == ".ogg":
            return _telegram(
                "sendVoice",
                files={"voice": (audio_path.name, handle, "audio/ogg")},
                chat_id=_chat_id(),
                caption=caption[:1000],
            )

        return _telegram(
            "sendAudio",
            files={"audio": (audio_path.name, handle, "audio/mpeg")},
            chat_id=_chat_id(),
            caption=caption[:1000],
            title=caption[:60],
            performer="Brooksy",
        )
