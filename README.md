# dal-personal-agent

Dal's personal AI agent for Telegram, powered by DeepSeek V4 Flash.

## Tonight's starter skills

- Normal companion conversation: send a regular message.
- `/calc <expression>`: safe arithmetic, for example `/calc 84600 * 17.5 / 100`.
- `/time [IANA timezone]`: time in `Europe/London` by default.
- `/summarise <text>`: a concise DeepSeek summary without adding it to chat history.
- `/research <topic>`: a short live lookup from Wikipedia. This is deliberately
  not presented as broad web search.

## Running it

Set these Railway environment variables (never commit their values):

- `TELEGRAM_TOKEN`
- `DEEPSEEK_API_KEY`

Railway starts the process with `python agent.py`.
