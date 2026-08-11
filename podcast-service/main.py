"""The podcast service: web app, scheduler and command line in one file.

Three ways to make an episode happen:

  python main.py sample     one minute test episode, sends straight away
  python main.py run        today's full episode, ignores the clock
  the built-in scheduler    checks every hour and only fires at 07:00 London

The HTTP side exists so Railway has something to health check and so an
external cron can poke /cron on the hour if you would rather not rely on the
in-process loop.
"""

import os
import sys
import threading
import time
import traceback
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException

from config import DATA_DIR, DELIVERY_HOUR, SHOW_TITLE, TIMEZONE
from deliver import (
    already_sent_today,
    next_episode_number,
    read_state,
    record_sent,
    send_episode,
    send_note,
)
from generate_script import generate_script, write_script
from tts import synthesise_script, to_voice_note

app = FastAPI(title=f"{SHOW_TITLE} service")

RUN_TOKEN = os.getenv("RUN_TOKEN")
RUN_SCHEDULER = os.getenv("RUN_SCHEDULER", "1") != "0"

LAST_RUN = {"status": "nothing yet"}
_LOCK = threading.Lock()


def now_local():
    return datetime.now(ZoneInfo(TIMEZONE))


def audio_dir():
    directory = Path(DATA_DIR) / "audio"

    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError:
        directory = Path("./podcast-data/audio")
        directory.mkdir(parents=True, exist_ok=True)

    return directory


def sample_script():
    text = (Path(__file__).parent / "episode0.md").read_text(encoding="utf-8")
    return text.strip()


def run_episode(sample=False, force=False):
    """Generate, speak, deliver. Returns a small dict describing what happened."""

    if not _LOCK.acquire(blocking=False):
        return {"status": "already running"}

    started = time.time()

    try:
        if sample:
            episode_number = 0
            script = sample_script()
            subtitle = "Sample"
            write_script(script)
        else:
            if already_sent_today() and not force:
                return {"status": "skipped", "reason": "already sent today"}

            episode_number = next_episode_number()
            script = generate_script(episode_number)
            subtitle = None

        words = len(script.split())
        print(f"Script ready: {words} words")

        destination = audio_dir() / f"episode-{episode_number:04d}.mp3"
        mp3 = synthesise_script(script, destination)

        voice = to_voice_note(mp3) or mp3
        send_episode(voice, episode_number, subtitle)

        if not sample:
            record_sent(episode_number)

        result = {
            "status": "sent",
            "episode": episode_number,
            "words": words,
            "file": str(voice),
            "seconds": round(time.time() - started, 1),
        }

    except Exception as exc:  # noqa: BLE001 - always report, never die quietly
        traceback.print_exc()
        result = {"status": "failed", "error": str(exc)}

        try:
            send_note(f"Podcast build failed: {exc}")
        except Exception:  # noqa: BLE001
            pass

    finally:
        _LOCK.release()

    LAST_RUN.clear()
    LAST_RUN.update(result)
    print(f"Run finished: {result}")
    return result


def due_now():
    """True only in the delivery hour, and only if nothing went out today."""

    return now_local().hour == DELIVERY_HOUR and not already_sent_today()


def scheduler_loop():
    print(
        f"Scheduler on. Waiting for {DELIVERY_HOUR:02d}:00 {TIMEZONE}. "
        f"Local time is now {now_local():%Y-%m-%d %H:%M}"
    )

    while True:
        try:
            if due_now():
                print("Delivery hour reached, building today's episode")
                run_episode()
        except Exception as exc:  # noqa: BLE001
            print(f"Scheduler error: {exc}")

        # Check every ten minutes: cheap, and it survives a restart mid-hour.
        time.sleep(600)


def _check_token(supplied):
    if RUN_TOKEN and supplied != RUN_TOKEN:
        raise HTTPException(status_code=401, detail="Bad or missing run token")


@app.get("/")
def root():
    return {
        "show": SHOW_TITLE,
        "local_time": now_local().isoformat(timespec="seconds"),
        "delivery_hour": DELIVERY_HOUR,
        "timezone": TIMEZONE,
        "scheduler": RUN_SCHEDULER,
        "state": read_state(),
        "last_run": LAST_RUN,
    }


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/cron")
@app.get("/cron")
def cron():
    """Safe to hit every hour. Only builds during the delivery hour."""

    if not due_now():
        return {
            "status": "not due",
            "local_time": now_local().isoformat(timespec="seconds"),
        }

    threading.Thread(target=run_episode, daemon=True).start()
    return {"status": "started"}


@app.post("/run")
def run(
    background: BackgroundTasks,
    sample: bool = False,
    force: bool = False,
    x_run_token: str = Header(default=None),
):
    _check_token(x_run_token)
    background.add_task(run_episode, sample, force)
    return {"status": "started", "sample": sample, "force": force}


@app.on_event("startup")
def start_scheduler():
    if RUN_SCHEDULER:
        threading.Thread(target=scheduler_loop, daemon=True).start()


def _cli():
    command = sys.argv[1] if len(sys.argv) > 1 else "serve"

    if command == "sample":
        print(run_episode(sample=True))
    elif command == "run":
        print(run_episode(force=True))
    elif command == "script":
        print(generate_script(next_episode_number()))
    else:
        import uvicorn

        uvicorn.run(
            app,
            host="0.0.0.0",
            port=int(os.getenv("PORT", "8000")),
        )


if __name__ == "__main__":
    _cli()
