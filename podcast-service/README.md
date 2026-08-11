# podcast-service

A daily eight minute coding podcast in the Brooksy voice, delivered to
Telegram at 07:00 London time. Separate Railway service, same repo, does not
touch `agent.py`.

## What it does

1. `generate_script.py` pulls the tech feeds, picks today's app and today's
   coding term from the rotation in `config.py`, and has the model write the
   episode to a fixed running order: cold open, lesson, news, app, tease.
2. `tts.py` cuts the script on paragraph breaks, sends each chunk to
   ElevenLabs, and stitches the audio back into one file. The chunking is what
   gets round the 5,000 character limit on a single request.
3. `deliver.py` sends it to Telegram and keeps the episode counter.
4. `main.py` is the FastAPI app, the scheduler and the command line.

## Railway setup

Create a **new service** in the same project, from this repo, then:

| Setting | Value |
| --- | --- |
| Root Directory | `podcast-service` |
| Start Command | `python main.py serve` |
| Volume mount path | `/data` (optional but recommended) |

Without a volume the episode counter resets on every redeploy, and old audio
is thrown away. Neither is fatal.

## Environment variables

| Name | Needed | Notes |
| --- | --- | --- |
| `OPENAI_API_KEY` | yes | writes the script |
| `ELEVENLABS_API_KEY` | yes | speaks it |
| `TELEGRAM_BOT_TOKEN` | yes | same bot as the agent |
| `TELEGRAM_CHAT_ID` | yes | where it lands. Ask the bot `/whoami` |
| `VOICE_ID` | no | defaults to `wnNtQzY8acIH166z7tVO` |
| `OPENAI_MODEL` | no | defaults to `gpt-4o-mini` |
| `ELEVENLABS_MODEL` | no | defaults to `eleven_multilingual_v2` |
| `DELIVERY_HOUR` | no | defaults to 7 |
| `PODCAST_TZ` | no | defaults to `Europe/London`, so BST and GMT sort themselves |
| `PODCAST_DATA_DIR` | no | defaults to `/data/podcast` |
| `RUN_TOKEN` | no | if set, `POST /run` needs it in an `X-Run-Token` header |
| `RUN_SCHEDULER` | no | set to `0` to turn the built-in clock off |

## Making an episode happen

From the Railway console, in the service:

    python main.py sample     one minute test episode, sent immediately
    python main.py run        today's full episode now, ignoring the clock
    python main.py script     write the script only, send nothing

Over HTTP:

    GET  /            what it thinks the time is, and the last run
    GET  /health      for the health check
    GET  /cron        safe to hit hourly, only builds during the delivery hour
    POST /run         ?sample=true or ?force=true

## The clock

The service checks every ten minutes whether it is the delivery hour in
`PODCAST_TZ` and whether anything has already gone out today. That is what
makes the BST and GMT change a non-event: the hour is judged in London time,
not UTC. If you would rather drive it from outside, set `RUN_SCHEDULER=0` and
point an hourly cron at `/cron`.

## Voice notes and ffmpeg

`railpack.json` asks for ffmpeg. With it, the audio is joined cleanly and
converted to OGG/Opus, which is what Telegram needs for a true voice note.
Without it, the service still works: the mp3 parts are joined directly and it
arrives as an audio file instead. No silent failures either way.

## Rotation

`config.py` holds roughly thirty apps and seventy-odd coding terms. The
choice is driven by the date, so nothing repeats until the list is exhausted.
Add to either list and the rotation just gets longer.
