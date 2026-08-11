"""Turns a script into one audio file using ElevenLabs.

ElevenLabs caps a single request at 5,000 characters, and an eight minute
episode is well past that. So the script is cut on paragraph breaks into
chunks, each chunk is synthesised on its own, and the pieces are stitched
back together. Each request is told what came before and after so the
delivery does not reset at every join.
"""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import requests

ELEVENLABS_API = "https://api.elevenlabs.io/v1/text-to-speech"

VOICE_ID = os.getenv("VOICE_ID", "wnNtQzY8acIH166z7tVO")
MODEL_ID = os.getenv("ELEVENLABS_MODEL", "eleven_multilingual_v2")
OUTPUT_FORMAT = os.getenv("ELEVENLABS_FORMAT", "mp3_44100_128")

# Well under the 5,000 character limit, and short enough that one bad chunk
# is cheap to retry.
MAX_CHUNK_CHARS = int(os.getenv("MAX_CHUNK_CHARS", "2200"))


def have_ffmpeg():
    return shutil.which("ffmpeg") is not None


def split_script(script, max_chars=MAX_CHUNK_CHARS):
    """Cut on blank lines, then on sentences if a paragraph is still too big."""

    paragraphs = [p.strip() for p in script.split("\n\n") if p.strip()]
    chunks = []
    current = ""

    for paragraph in paragraphs:
        while len(paragraph) > max_chars:
            cut = paragraph.rfind(". ", 0, max_chars)
            if cut == -1:
                cut = max_chars - 1
            chunks.append(paragraph[: cut + 1].strip())
            paragraph = paragraph[cut + 1 :].strip()

        if not current:
            current = paragraph
        elif len(current) + len(paragraph) + 2 <= max_chars:
            current = f"{current}\n\n{paragraph}"
        else:
            chunks.append(current)
            current = paragraph

    if current:
        chunks.append(current)

    return chunks


def synthesise_chunk(text, previous_text=None, next_text=None):
    key = os.getenv("ELEVENLABS_API_KEY")
    if not key:
        raise RuntimeError("ELEVENLABS_API_KEY is not set")

    payload = {
        "text": text,
        "model_id": MODEL_ID,
        "voice_settings": {
            "stability": float(os.getenv("VOICE_STABILITY", "0.45")),
            "similarity_boost": float(os.getenv("VOICE_SIMILARITY", "0.8")),
            "style": float(os.getenv("VOICE_STYLE", "0.15")),
            "use_speaker_boost": True,
        },
    }

    if previous_text:
        payload["previous_text"] = previous_text[-400:]
    if next_text:
        payload["next_text"] = next_text[:400]

    response = requests.post(
        f"{ELEVENLABS_API}/{VOICE_ID}",
        params={"output_format": OUTPUT_FORMAT},
        headers={"xi-api-key": key, "accept": "audio/mpeg"},
        json=payload,
        timeout=180,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"ElevenLabs returned {response.status_code}: {response.text[:300]}"
        )

    return response.content


def _stitch_with_ffmpeg(parts, destination):
    with tempfile.TemporaryDirectory() as workspace:
        listing = Path(workspace) / "parts.txt"
        lines = []

        for index, audio in enumerate(parts):
            piece = Path(workspace) / f"part-{index:03d}.mp3"
            piece.write_bytes(audio)
            lines.append(f"file '{piece}'")

        listing.write_text("\n".join(lines), encoding="utf-8")

        subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(listing),
                "-c",
                "copy",
                str(destination),
            ],
            check=True,
        )

    return destination


def _stitch_by_bytes(parts, destination):
    """Fallback when ffmpeg is missing. MP3 frames tolerate being appended."""

    with open(destination, "wb") as handle:
        for audio in parts:
            handle.write(audio)

    return destination


def synthesise_script(script, destination):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)

    chunks = split_script(script)
    if not chunks:
        raise RuntimeError("Nothing to speak: the script was empty")

    print(f"Synthesising {len(chunks)} chunks with voice {VOICE_ID}")

    parts = []
    for index, chunk in enumerate(chunks):
        previous_text = chunks[index - 1] if index else None
        next_text = chunks[index + 1] if index + 1 < len(chunks) else None
        parts.append(synthesise_chunk(chunk, previous_text, next_text))
        print(f"  chunk {index + 1}/{len(chunks)} done ({len(chunk)} chars)")

    if have_ffmpeg():
        _stitch_with_ffmpeg(parts, destination)
    else:
        print("ffmpeg not found, joining the mp3 parts directly")
        _stitch_by_bytes(parts, destination)

    return destination


def to_voice_note(mp3_path):
    """Convert to OGG/Opus so Telegram treats it as a real voice note.

    Returns None if ffmpeg is not installed, and the caller falls back to
    sending the mp3 as audio instead.
    """

    if not have_ffmpeg():
        return None

    mp3_path = Path(mp3_path)
    destination = mp3_path.with_suffix(".ogg")

    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(mp3_path),
            "-c:a",
            "libopus",
            "-b:a",
            "48k",
            "-ar",
            "48000",
            "-ac",
            "1",
            str(destination),
        ],
        check=True,
    )

    return destination
