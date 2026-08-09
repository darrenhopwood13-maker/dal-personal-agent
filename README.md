# dal-personal-agent

Dal's personal AI agent for Telegram, powered by DeepSeek V4 Flash.

## Tonight's starter skills

- Normal companion conversation: send a regular message.
- `/calc <expression>`: safe arithmetic, for example `/calc 84600 * 17.5 / 100`.
- `/time [IANA timezone]`: time in `Europe/London` by default.
- `/summarise <text>`: a concise DeepSeek summary without adding it to chat history.
- `/research <topic>`: a short live lookup from Wikipedia. This is deliberately
  not presented as broad web search.
- `/search <question or topic>`: live web search and a concise answer with source links.

## Running it

Set these Railway environment variables (never commit their values):

- `TELEGRAM_TOKEN`
- `DEEPSEEK_API_KEY`
- `BRAVE_SEARCH_API_KEY` (optional, required only for `/search`)

Railway starts the process with `python agent.py`.

## Enabling live web search

Create a Brave Search API key and save it in Railway as `BRAVE_SEARCH_API_KEY`.
The key stays in Railway and must never be committed to GitHub. Once set,
restart or redeploy the service, then try `/search latest UK construction news`.
