"""
writes.py — confirmation queue and audit log for Brooksy's write tools.

Nothing that changes the outside world executes on the model's say-so. A write tool
call is intercepted, staged, and summarised back to Dal. It only runs after an
explicit /confirm.

Wiring (three touch points in your bot — see WRITE_ACCESS_SETUP.md):
  1. call writes.init_db() at startup
  2. in your tool dispatcher, call writes.intercept() before executing a tool
  3. add /confirm, /cancel and /pending command handlers

Stdlib only. Stores in the same Railway volume as your chat history.
"""

import json
import os
import secrets
import sqlite3
import time

DATA_DIR = os.getenv("PODCAST_DATA_DIR") or os.getenv("DATA_DIR") or "/data"
DB_PATH = os.path.join(DATA_DIR, "writes.db")

# How long a staged write stays confirmable
TTL_SECONDS = int(os.getenv("WRITE_TTL_SECONDS", "900"))  # 15 minutes

# Global kill switch. DRY_RUN=1 means confirmed writes are logged, never executed.
DRY_RUN = os.getenv("WRITE_DRY_RUN", "0") == "1"

# Tighter than ALLOWED_CHAT_IDS on purpose: reading is one trust level, writing another.
_raw_write_ids = os.getenv("ALLOWED_WRITE_CHAT_IDS", "").strip()
ALLOWED_WRITE_CHAT_IDS = set()
for _entry in _raw_write_ids.replace(" ", "").split(","):
    if not _entry:
        continue
    try:
        ALLOWED_WRITE_CHAT_IDS.add(int(_entry))
    except ValueError:
        print(f"writes: ignoring malformed ALLOWED_WRITE_CHAT_IDS entry {_entry!r}")

# Populated by tools_write.py at import time.
WRITE_TOOLS = set()


def register_write_tool(name):
    """Mark a tool as requiring confirmation before it executes."""
    WRITE_TOOLS.add(name)


def is_write_tool(name):
    return name in WRITE_TOOLS


# ----------------------------------------------------------------------------- db


def _conn():
    os.makedirs(DATA_DIR, exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    with _conn() as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS pending_writes (
                token      TEXT PRIMARY KEY,
                chat_id    INTEGER NOT NULL,
                tool_name  TEXT NOT NULL,
                args_json  TEXT NOT NULL,
                summary    TEXT NOT NULL,
                created_at REAL NOT NULL,
                expires_at REAL NOT NULL,
                status     TEXT NOT NULL DEFAULT 'pending'
            )"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS write_audit (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id    INTEGER,
                tool_name  TEXT NOT NULL,
                args_json  TEXT NOT NULL,
                outcome    TEXT NOT NULL,
                detail     TEXT,
                created_at REAL NOT NULL
            )"""
        )
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_pending_chat ON pending_writes(chat_id, status)"
        )


# -------------------------------------------------------------------------- audit


# Self-initialising: one less thing to remember in agent.py, and one less way for
# a missing startup call to take down every write.
init_db()


def log_write(
    chat_id,
    tool_name,
    args,
    outcome,
    detail: str = "",
):
    """outcome: staged | confirmed | cancelled | expired | executed | failed | blocked"""
    with _conn() as c:
        c.execute(
            "INSERT INTO write_audit (chat_id, tool_name, args_json, outcome, detail, created_at)"
            " VALUES (?,?,?,?,?,?)",
            (chat_id, tool_name, _safe_json(args), outcome, detail[:2000], time.time()),
        )


def recent_audit(limit: int = 20):
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM write_audit ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


def _safe_json(args):
    """Never let a credential-shaped value reach the log."""
    redacted = {}
    for k, v in (args or {}).items():
        if any(s in k.lower() for s in ("token", "key", "secret", "password", "auth")):
            redacted[k] = "[redacted]"
        elif isinstance(v, str) and len(v) > 4000:
            redacted[k] = v[:4000] + f"... [truncated, {len(v)} chars]"
        else:
            redacted[k] = v
    return json.dumps(redacted, ensure_ascii=False, default=str)


# ------------------------------------------------------------------------ staging


def _expire_stale():
    now = time.time()
    with _conn() as c:
        stale = c.execute(
            "SELECT token, chat_id, tool_name, args_json FROM pending_writes"
            " WHERE status='pending' AND expires_at < ?",
            (now,),
        ).fetchall()
        if stale:
            c.execute(
                "UPDATE pending_writes SET status='expired'"
                " WHERE status='pending' AND expires_at < ?",
                (now,),
            )
    for r in stale:
        log_write(r["chat_id"], r["tool_name"], {}, "expired", r["token"])


def stage(chat_id, tool_name, args, summary):
    """Park a write and return its confirmation token."""
    _expire_stale()
    token = secrets.token_hex(2)  # 4 chars, short enough to thumb-type
    now = time.time()
    with _conn() as c:
        c.execute(
            "INSERT INTO pending_writes"
            " (token, chat_id, tool_name, args_json, summary, created_at, expires_at)"
            " VALUES (?,?,?,?,?,?,?)",
            (
                token,
                chat_id,
                tool_name,
                json.dumps(args, ensure_ascii=False, default=str),
                summary,
                now,
                now + TTL_SECONDS,
            ),
        )
    log_write(chat_id, tool_name, args, "staged", token)
    return token


def pending_for(chat_id):
    _expire_stale()
    with _conn() as c:
        rows = c.execute(
            "SELECT token, tool_name, summary, expires_at FROM pending_writes"
            " WHERE chat_id=? AND status='pending' ORDER BY created_at",
            (chat_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def take_confirmed(chat_id, token):
    """
    Claim a staged write for execution.
    Returns (tool_name, args, error). tool_name is None when error is set.
    Single-use: the row is marked confirmed before the caller executes it, so a
    token can never fire twice.
    """
    _expire_stale()
    token = token.strip().lstrip("#").lower()
    with _conn() as c:
        row = c.execute(
            "SELECT * FROM pending_writes WHERE token=?", (token,)
        ).fetchone()
        if row is None:
            return None, {}, f"No pending action `{token}`."
        if row["chat_id"] != chat_id:
            log_write(chat_id, row["tool_name"], {}, "blocked", "wrong chat for token")
            return None, {}, f"No pending action `{token}`."
        if row["status"] != "pending":
            return None, {}, f"Action `{token}` is already {row['status']}."
        c.execute(
            "UPDATE pending_writes SET status='confirmed' WHERE token=?", (token,)
        )
    args = json.loads(row["args_json"])
    log_write(chat_id, row["tool_name"], args, "confirmed", token)
    return row["tool_name"], args, ""


def cancel(chat_id, token):
    token = token.strip().lstrip("#").lower()
    with _conn() as c:
        row = c.execute(
            "SELECT * FROM pending_writes WHERE token=? AND chat_id=?", (token, chat_id)
        ).fetchone()
        if row is None:
            return f"No pending action `{token}`."
        if row["status"] != "pending":
            return f"Action `{token}` is already {row['status']}."
        c.execute("UPDATE pending_writes SET status='cancelled' WHERE token=?", (token,))
    log_write(chat_id, row["tool_name"], {}, "cancelled", token)
    return f"Cancelled `{token}` — {row['summary']}"


def cancel_all(chat_id):
    items = pending_for(chat_id)
    for i in items:
        cancel(chat_id, i["token"])
    return f"Cancelled {len(items)} pending action(s)." if items else "Nothing pending."


# --------------------------------------------------------------------- interception


def summarise(tool_name, args):
    """Human-readable one-liner for the confirmation prompt."""
    a = args or {}
    if tool_name == "github_write_file":
        return f"Write `{a.get('path')}` in **{a.get('repo')}** on branch `{a.get('branch')}`"
    if tool_name == "github_create_branch":
        return f"Create branch `{a.get('new_branch')}` in **{a.get('repo')}** from `{a.get('from_branch', 'main')}`"
    if tool_name == "github_open_pr":
        return f"Open PR in **{a.get('repo')}**: `{a.get('head')}` → `{a.get('base', 'main')}` — {a.get('title')}"
    if tool_name == "supabase_insert_row":
        return f"Insert 1 row into **{a.get('table')}**"
    if tool_name == "supabase_update_row":
        return f"Update **{a.get('table')}** row `{a.get('row_id')}` — fields: {', '.join((a.get('values') or {}).keys())}"
    if tool_name == "lovable_send_message":
        return f"Send a build message to Lovable project `{a.get('project_id')}` (costs credits)"
    return f"Run `{tool_name}`"


def detail_block(tool_name, args):
    """The bit Dal actually reads before approving. Show the real payload."""
    a = args or {}
    if tool_name == "github_write_file":
        body = a.get("content", "")
        preview = body if len(body) <= 1200 else body[:1200] + "\n… [truncated]"
        return f"commit: {a.get('message')}\n\n```\n{preview}\n```"
    if tool_name == "github_open_pr":
        return a.get("body", "") or ""
    if tool_name in ("supabase_insert_row", "supabase_update_row"):
        return "```json\n" + json.dumps(a.get("values", {}), indent=2)[:1200] + "\n```"
    if tool_name == "lovable_send_message":
        return "```\n" + str(a.get("message", ""))[:1500] + "\n```"
    return ""


def intercept(chat_id, tool_name, arguments_json):
    """
    Call this in agent.py BEFORE run_tool(), with the same arguments it gets.

    Returns None  -> not a write tool, carry on and call run_tool as normal.
    Returns a str -> do NOT execute. Hand the string back as the tool result.
    """
    if not is_write_tool(tool_name):
        return None

    try:
        args = json.loads(arguments_json or "{}")
    except json.JSONDecodeError:
        return f"Tool '{tool_name}' was called with malformed arguments. Nothing staged."
    if not isinstance(args, dict):
        return f"Tool '{tool_name}' expects an object of arguments. Nothing staged."

    if chat_id not in ALLOWED_WRITE_CHAT_IDS:
        log_write(chat_id, tool_name, args, "blocked", "chat not write-authorised")
        return "Write tools aren't enabled for this chat. Nothing has been changed."

    token = stage(chat_id, tool_name, args, summarise(tool_name, args))
    lines = ["Confirm this write", "", summarise(tool_name, args)]
    detail = detail_block(tool_name, args)
    if detail:
        lines += ["", detail]
    lines += [
        "",
        f"/confirm {token} to run it - /cancel {token} to bin it",
        f"Expires in {TTL_SECONDS // 60} min. Nothing has changed yet.",
    ]
    if DRY_RUN:
        lines.insert(1, "(dry-run mode: confirming will log but not execute)")
    return "\n".join(lines)


def execute_confirmed(chat_id, token, runner):
    """
    Handler for /confirm. `runner` is tools.run_tool - it takes (name, arguments_json)
    and always returns a string.
    """
    tool_name, args, err = take_confirmed(chat_id, token)
    if err:
        return err
    if DRY_RUN:
        log_write(chat_id, tool_name, args, "executed", "dry-run, skipped")
        return f"Dry run - '{tool_name}' was not executed. Nothing changed."
    try:
        result = runner(tool_name, json.dumps(args))
        log_write(chat_id, tool_name, args, "executed", str(result)[:2000])
        return f"Done - {summarise(tool_name, args)}\n\n{result}"
    except Exception as exc:  # noqa: BLE001 - a write must never kill the agent
        log_write(chat_id, tool_name, args, "failed", repr(exc))
        return f"Failed - {summarise(tool_name, args)}\n\n{exc}\n\nNothing was retried."


def pending_summary(chat_id):
    """Text for /pending."""
    items = pending_for(chat_id)
    if not items:
        return "Nothing waiting for approval."
    lines = ["Waiting for you:", ""]
    for item in items:
        left = max(0, int(item["expires_at"] - time.time()) // 60)
        lines.append(f"  {item['token']}  {item['summary']}  ({left} min left)")
    lines += ["", "/confirm <token> or /cancel <token>"]
    return "\n".join(lines)


def audit_summary(limit=15):
    """Text for /writelog."""
    rows = recent_audit(limit)
    if not rows:
        return "No write activity recorded."
    lines = ["Recent write activity:", ""]
    for row in rows:
        when = time.strftime("%d %b %H:%M", time.localtime(row["created_at"]))
        lines.append(f"  {when}  {row['outcome']:<9} {row['tool_name']}")
    return "\n".join(lines)
