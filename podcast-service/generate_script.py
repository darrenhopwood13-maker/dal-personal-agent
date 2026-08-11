"""Builds the daily episode script and writes it to script.md.

Four ingredients: two tech stories off the wire, one app of the day, one
coding term explained in plain English, then a running order the model has to
follow. Everything rotates on the date, so nothing repeats until the list
runs out.
"""

import os
import re
from datetime import date, datetime
from pathlib import Path
from xml.etree import ElementTree
from zoneinfo import ZoneInfo

import requests
from openai import OpenAI

from config import (
    APPS,
    DATA_DIR,
    FEEDS,
    SHOW_TITLE,
    TARGET_WORDS,
    TERMS,
    TIMEZONE,
)

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

VOICE_BRIEF = """
You write for Brooksy: Dal's mate who happens to know software inside out.

WHO YOU ARE TALKING TO
Darren Hopwood, goes by Dal. East End, senior site manager at a tier 1 UK
contractor, currently finishing a job in Mayfair. Builds software on the side.
Three daughters. He listens to this on the way to site, one ear, holding a
coffee.

HOW IT SOUNDS
- Spoken British English. Contractions always. Site language, not consultancy
  language.
- Warm and quick. A dry line in passing, never a performance, never explained.
- Short sentences. This is being read aloud, so anything he would not say out
  loud does not go in.
- No exclamation marks, no emoji, no Americanisms, no corporate filler.
- Never "in today's fast-paced world", never "let's dive in", never
  "buckle up".
- Numbers spoken as a person says them: "about fifteen quid a month", not
  "GBP 15.00".
- No headings, no bullet points, no stage directions, no speaker labels. Just
  the words to be spoken, in paragraphs.

HOW IT TEACHES
Every technical idea gets one comparison from building work: sites, drawings,
subcontractors, snagging, deliveries, scaffolding, sign-off. One good analogy
beats three weak ones. Never talk down to him. He is not slow, he is just new
to this bit.
"""


def _client():
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    return OpenAI(api_key=key)


def _strip_html(text):
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _parse_feed(source, xml_text, limit):
    """Handles both RSS and Atom without pulling in another dependency."""

    items = []

    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError:
        return items

    for item in root.iter():
        tag = item.tag.split("}")[-1]
        if tag not in ("item", "entry"):
            continue

        title = ""
        summary = ""
        link = ""

        for child in item:
            child_tag = child.tag.split("}")[-1]
            if child_tag == "title" and not title:
                title = _strip_html(child.text)
            elif child_tag in ("description", "summary", "content") and not summary:
                summary = _strip_html(child.text)
            elif child_tag == "link" and not link:
                link = (child.text or child.attrib.get("href") or "").strip()

        if title:
            items.append(
                {
                    "source": source,
                    "title": title,
                    "summary": summary[:600],
                    "link": link,
                }
            )

        if len(items) >= limit:
            break

    return items


def fetch_headlines(per_feed=5):
    headlines = []

    for source, url in FEEDS:
        try:
            response = requests.get(
                url,
                timeout=20,
                headers={"User-Agent": "brooksy-podcast/1.0"},
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            print(f"Feed failed, skipping {source}: {exc}")
            continue

        headlines.extend(_parse_feed(source, response.text, per_feed))

    return headlines


def rotation_index(day=None):
    day = day or datetime.now(ZoneInfo(TIMEZONE)).date()
    return day.toordinal()


def pick_app(day=None):
    return APPS[rotation_index(day) % len(APPS)]


def pick_term(day=None):
    return TERMS[rotation_index(day) % len(TERMS)]


def _headline_block(headlines):
    if not headlines:
        return "No feeds came back. Skip the news section and say so in one line."

    lines = []
    for item in headlines[:18]:
        lines.append(f"- [{item['source']}] {item['title']}. {item['summary'][:220]}")
    return "\n".join(lines)


def build_prompt(headlines, app, term, episode_number, day=None):
    day = day or datetime.now(ZoneInfo(TIMEZONE)).date()
    app_name, app_note = app
    term_name, term_angle = term

    return f"""Write today's episode of {SHOW_TITLE}, episode {episode_number},
for {day.strftime('%A %d %B %Y')}.

{VOICE_BRIEF}

RUNNING ORDER. Follow it exactly, in this order, with no headings.

1. Cold open, about 30 seconds, roughly 75 words. Greet him, say the date,
   and say in one line what is coming. No throat clearing.

2. The lesson, about 3 minutes, roughly 450 words. Today's term is
   "{term_name}" - {term_angle}. Explain what it is, why it matters to
   someone building software, one building-site analogy, and one concrete
   thing he could look at in his own projects today.

3. Tech news, about 2 minutes. The two biggest stories from the list below,
   about 60 words each, in plain English: what happened, and why he should
   care. Ignore anything trivial, and ignore anything that is really an
   advert. Name the outlet.

4. App of the day, about 2 minutes, roughly 300 words. Today it is
   {app_name} - {app_note}. What it does, who it is actually for, one honest
   drawback, and whether it is worth his time.

5. Tomorrow tease, about 30 seconds. One line on what is coming, then sign
   off short.

TODAY'S HEADLINES
{_headline_block(headlines)}

RULES
- Total length about {TARGET_WORDS} words. Closer to that number is better
  than shorter.
- Output only the spoken words. No headings, no numbering, no notes, no
  markdown, no URLs read aloud.
- Paragraph breaks where the delivery should breathe. They are used to split
  the audio, so keep each paragraph under about 1,200 characters.
- If a story is speculation, say so. Never invent a fact or a quote.
"""


def generate_script(episode_number, day=None, save=True):
    """Returns the finished script text, and writes script.md next to it."""

    day = day or datetime.now(ZoneInfo(TIMEZONE)).date()
    headlines = fetch_headlines()
    app = pick_app(day)
    term = pick_term(day)

    print(f"Episode {episode_number}: term '{term[0]}', app '{app[0]}', "
          f"{len(headlines)} headlines")

    response = _client().chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": VOICE_BRIEF},
            {
                "role": "user",
                "content": build_prompt(headlines, app, term, episode_number, day),
            },
        ],
        temperature=0.8,
    )

    script = (response.choices[0].message.content or "").strip()

    if not script:
        raise RuntimeError("The model returned an empty script")

    if save:
        write_script(script, day)

    return script


def write_script(script, day=None):
    day = day or datetime.now(ZoneInfo(TIMEZONE)).date()
    directory = Path(DATA_DIR)

    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError:
        directory = Path("./podcast-data")
        directory.mkdir(parents=True, exist_ok=True)

    (directory / "script.md").write_text(script, encoding="utf-8")
    (directory / f"script-{day.isoformat()}.md").write_text(script, encoding="utf-8")

    return directory / "script.md"


if __name__ == "__main__":
    print(generate_script(episode_number=999))
