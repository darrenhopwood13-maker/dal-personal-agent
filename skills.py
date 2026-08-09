"""On-demand skill briefs for Brooksy.

The design principle (from the master spec) is four separate layers:

    Persona  - how the agent behaves        -> SYSTEM_PROMPT in agent.py
    Skills   - what it knows how to do      -> this module + skills/*.md
    Tools    - what it can actually execute -> tools.py
    Memory   - facts that change over time  -> the SQLite history

Skills live as markdown files in skills/. Only the short index goes into the
system prompt on every call; the full brief is pulled with the load_skill tool
when the job actually calls for it. That keeps the per-message token cost flat
no matter how many skills you add.

To add a skill: drop a new .md file in skills/ with name and description at the
top. No code change, no schema change.
"""

import os
import re


SKILLS_DIRECTORY = os.getenv(
    "SKILLS_DIR",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "skills"),
)

# A brief longer than this gets truncated rather than blowing the context.
MAX_SKILL_CHARACTERS = 12000

_FRONT_MATTER = re.compile(
    r"\A\s*---\s*\n(.*?)\n---\s*\n", re.DOTALL
)


def _parse_skill_file(path):
    """Return (name, description, body) for one skill file."""
    with open(path, "r", encoding="utf-8") as handle:
        raw = handle.read()

    slug = os.path.splitext(os.path.basename(path))[0]
    name = slug
    description = ""
    body = raw

    match = _FRONT_MATTER.match(raw)
    if match:
        for line in match.group(1).splitlines():
            key, separator, value = line.partition(":")
            if not separator:
                continue
            key = key.strip().lower()
            value = value.strip().strip('"').strip("'")
            if key == "name" and value:
                name = value
            elif key == "description" and value:
                description = value
        body = raw[match.end():]

    if not description:
        for line in body.splitlines():
            line = line.strip().lstrip("#").strip()
            if line:
                description = line
                break

    return name, description, body.strip()


def _discover():
    skills = {}

    if not os.path.isdir(SKILLS_DIRECTORY):
        print(f"No skills directory at {SKILLS_DIRECTORY} - skills disabled.")
        return skills

    for filename in sorted(os.listdir(SKILLS_DIRECTORY)):
        if not filename.endswith(".md"):
            continue

        path = os.path.join(SKILLS_DIRECTORY, filename)

        try:
            name, description, body = _parse_skill_file(path)
        except OSError as exc:
            print(f"Could not read skill {filename}: {exc}")
            continue

        if not body:
            print(f"Skipping empty skill file {filename}")
            continue

        skills[name.lower()] = {
            "name": name,
            "description": description,
            "body": body,
            "slug": os.path.splitext(filename)[0].lower(),
        }

    return skills


SKILLS = _discover()


def skill_names():
    return [skill["name"] for skill in SKILLS.values()]


def skills_index():
    """Short list for the system prompt. One line per skill."""
    if not SKILLS:
        return "(No skill briefs are installed.)"

    return "\n".join(
        f"- {skill['name']}: {skill['description']}" for skill in SKILLS.values()
    )


def _find(name):
    if not name:
        return None

    wanted = name.strip().lower()

    for skill in SKILLS.values():
        if wanted in (skill["name"].lower(), skill["slug"]):
            return skill

    # Be forgiving: "app review" should find "app-reviewer".
    normalised = re.sub(r"[^a-z0-9]", "", wanted)
    for skill in SKILLS.values():
        candidates = {
            re.sub(r"[^a-z0-9]", "", skill["name"].lower()),
            re.sub(r"[^a-z0-9]", "", skill["slug"]),
        }
        if normalised in candidates:
            return skill
        if normalised and any(normalised in candidate for candidate in candidates):
            return skill

    return None


def tool_load_skill(name):
    """Return the full text of one skill brief."""
    skill = _find(name)

    if skill is None:
        available = ", ".join(skill_names()) or "none installed"
        return (
            f"No skill called '{name}'. Available skills: {available}. "
            "Answer from your own judgement instead."
        )

    body = skill["body"]
    if len(body) > MAX_SKILL_CHARACTERS:
        body = body[:MAX_SKILL_CHARACTERS] + "\n\n[brief truncated]"

    return f"SKILL BRIEF: {skill['name']}\n\n{body}"
