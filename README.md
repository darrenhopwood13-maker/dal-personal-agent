# dal-personal-agent

Brooksy — Dal's personal AI agent for Telegram, powered by DeepSeek with real
tool calling.

## What changed in v2

v1 was a chat bot with slash commands. v2 is an agent: the model decides for
itself when to search the web, read a page, do a calculation or look at a
GitHub repo. You no longer type `/search` — just ask.

Also added: voice notes in and out via ElevenLabs, history that survives a
redeploy, and access control.

## Tools

The model calls these on its own, no command needed:

| Tool | What it does |
| --- | --- |
| `web_search` | Live Brave web search, UK-biased |
| `fetch_page` | Reads the text of any URL |
| `calculate` | Exact arithmetic, AST-parsed, no `eval` |
| `current_time` | Time in any IANA timezone |
| `wikipedia` | Background reference lookup |
| `github_list_files` | Lists files in any repo |
| `github_read_file` | Reads a file from any repo |
| `github_search_code` | Searches code in a repo (needs a token) |
| `list_voices` | Lists your ElevenLabs voices |

## Commands

Only for things the model shouldn't decide:

- `/voice on` / `/voice off` — spoken replies alongside text
- `/say <text>` — speak something back
- `/voices` — list ElevenLabs voices and their ids
- `/forget` — wipe conversation history
- `/status` — show which keys are wired up
- `/whoami` — show your Telegram chat id

Send a voice note and it gets transcribed automatically.

## Environment variables

Set these in Railway. Never commit their values.

**Required**

- `TELEGRAM_TOKEN`
- `DEEPSEEK_API_KEY`

**Strongly recommended**

- `ALLOWED_CHAT_IDS` — comma separated Telegram chat ids. Without this,
  anyone who finds the bot can use it and spend your API credits. Message the
  bot `/whoami` to get your id, then set it.

**Optional**

- `BRAVE_SEARCH_API_KEY` — enables `web_search`
- `ELEVENLABS_API_KEY` — enables voice in and out
- `ELEVENLABS_VOICE_ID` — defaults to a stock voice; run `/voices` to pick
- `GITHUB_TOKEN` — a fine-grained read-only PAT; needed for private repos
  and code search
- `DEEPSEEK_MODEL` — defaults to `deepseek-v4-flash`
- `DATABASE_PATH` — defaults to `/data/agent.db`
- `HISTORY_TURNS` — conversation turns to remember, defaults to 30

## History persistence

History is stored in SQLite at `DATABASE_PATH`. Railway containers are
ephemeral, so **attach a Railway volume mounted at `/data`** or the history
will still be wiped on redeploy. If the path isn't writable, the agent falls
back to `./agent.db` and logs a warning.

## Running it

Railway starts the process with `python agent.py`.

## Security notes

- Search results and fetched web pages are passed to the model clearly
  labelled as untrusted data, with an instruction not to obey anything inside
  them. This is prompt-injection mitigation, not a guarantee — don't give this
  agent write access to anything you can't afford to lose.
- The GitHub tools are read-only by design.
- Keep `GITHUB_TOKEN` fine-grained and read-only.
