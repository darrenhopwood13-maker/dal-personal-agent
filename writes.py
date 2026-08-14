"""
tools_write.py — Brooksy's write tools.

Every function here is registered as a write tool, which means it cannot execute
directly from a model tool call. writes.intercept() stages it and Dal confirms it.

Design rules baked in, not left to the model:
  * repo allowlist, and default branches are hard-refused
  * table allowlist, and there is no delete path at all
  * updates target one row by primary key
  * no schema changes, no deploys, no credential handling

Requires: requests. Swap to httpx if that's what the repo already uses.
"""

import base64
import json
import os
import requests

from writes import register_write_tool

TIMEOUT = 30

# ----------------------------------------------------------------- configuration

GITHUB_TOKEN = os.getenv("GITHUB_WRITE_TOKEN") or os.getenv("GITHUB_TOKEN", "")
GITHUB_API = "https://api.github.com"

# Only these repos can be written to. Comma-separated owner/name.
GITHUB_WRITE_ALLOWLIST = {
    r.strip()
    for r in os.getenv("GITHUB_WRITE_ALLOWLIST", "").split(",")
    if r.strip()
}

PROTECTED_BRANCHES = {"main", "master", "production", "prod", "live", "release"}

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_WRITE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

# Only these tables can be written to. Comma-separated.
SUPABASE_WRITE_TABLES = {
    t.strip()
    for t in os.getenv("SUPABASE_WRITE_TABLES", "").split(",")
    if t.strip()
}

# Tables that must never be written to even if someone adds them to the allowlist.
SUPABASE_FORBIDDEN_TABLES = {"audit_log", "auth.users", "users", "write_audit"}

class WriteRefused(Exception):
    """A guard said no. Not a transport failure — don't retry."""


def _gh_headers():
    if not GITHUB_TOKEN:
        raise WriteRefused("GITHUB_WRITE_TOKEN is not set.")
    return {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _check_repo(repo):
    if "/" not in repo:
        raise WriteRefused(f"Repo must be owner/name, got '{repo}'.")
    if not GITHUB_WRITE_ALLOWLIST:
        raise WriteRefused("GITHUB_WRITE_ALLOWLIST is empty — no repo is writable.")
    if repo not in GITHUB_WRITE_ALLOWLIST:
        raise WriteRefused(
            f"'{repo}' is not on the write allowlist. Ask Dal to add it, don't route around it."
        )


def _check_branch(branch):
    if not branch:
        raise WriteRefused("A branch must be named explicitly.")
    if branch.lower() in PROTECTED_BRANCHES:
        raise WriteRefused(
            f"'{branch}' is protected. Write to a brooksy/* branch and open a PR."
        )


# --------------------------------------------------------------------- github


def tool_github_create_branch(
    repo, new_branch, from_branch = "main"
):
    _check_repo(repo)
    _check_branch(new_branch)

    r = requests.get(
        f"{GITHUB_API}/repos/{repo}/git/ref/heads/{from_branch}",
        headers=_gh_headers(),
        timeout=TIMEOUT,
    )
    if r.status_code != 200:
        raise WriteRefused(f"Could not read '{from_branch}' in {repo}: {r.status_code} {r.text[:200]}")
    sha = r.json()["object"]["sha"]

    r = requests.post(
        f"{GITHUB_API}/repos/{repo}/git/refs",
        headers=_gh_headers(),
        json={"ref": f"refs/heads/{new_branch}", "sha": sha},
        timeout=TIMEOUT,
    )
    if r.status_code == 422:
        return f"Branch '{new_branch}' already exists in {repo}."
    if r.status_code not in (200, 201):
        raise WriteRefused(f"Branch create failed: {r.status_code} {r.text[:300]}")
    return f"Created branch '{new_branch}' in {repo} from '{from_branch}' ({sha[:7]})."


def tool_github_write_file(
    repo, path, content, message, branch: str
):
    """Create or update a single file on a non-default branch."""
    _check_repo(repo)
    _check_branch(branch)
    if not message.strip():
        raise WriteRefused("A commit message is required.")
    if path.startswith("/") or ".." in path:
        raise WriteRefused(f"Refusing suspicious path '{path}'.")
    if os.path.basename(path) in (".env", ".env.local", ".env.production"):
        raise WriteRefused("Refusing to commit an env file.")

    # Existing file? Need its sha to update.
    existing_sha = None
    r = requests.get(
        f"{GITHUB_API}/repos/{repo}/contents/{path}",
        headers=_gh_headers(),
        params={"ref": branch},
        timeout=TIMEOUT,
    )
    if r.status_code == 200:
        existing_sha = r.json().get("sha")
    elif r.status_code not in (404,):
        raise WriteRefused(f"Could not check '{path}': {r.status_code} {r.text[:200]}")

    payload = {
        "message": message,
        "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
        "branch": branch,
    }
    if existing_sha:
        payload["sha"] = existing_sha

    r = requests.put(
        f"{GITHUB_API}/repos/{repo}/contents/{path}",
        headers=_gh_headers(),
        json=payload,
        timeout=TIMEOUT,
    )
    if r.status_code not in (200, 201):
        raise WriteRefused(f"File write failed: {r.status_code} {r.text[:300]}")
    commit = r.json().get("commit", {}).get("sha", "")[:7]
    verb = "Updated" if existing_sha else "Created"
    return f"{verb} {path} in {repo} on '{branch}' (commit {commit})."


def tool_github_open_pr(
    repo, head, title, body = "", base = "main"
):
    _check_repo(repo)
    _check_branch(head)  # head must not be a protected branch
    if not title.strip():
        raise WriteRefused("A PR title is required.")

    r = requests.post(
        f"{GITHUB_API}/repos/{repo}/pulls",
        headers=_gh_headers(),
        json={"title": title, "head": head, "base": base, "body": body, "draft": False},
        timeout=TIMEOUT,
    )
    if r.status_code not in (200, 201):
        raise WriteRefused(f"PR open failed: {r.status_code} {r.text[:300]}")
    d = r.json()
    return f"Opened PR #{d.get('number')} in {repo}: {d.get('html_url')}"


# ------------------------------------------------------------------- supabase


def _sb_headers():
    if not (SUPABASE_URL and SUPABASE_WRITE_KEY):
        raise WriteRefused("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set.")
    return {
        "apikey": SUPABASE_WRITE_KEY,
        "Authorization": f"Bearer {SUPABASE_WRITE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def _check_table(table):
    t = table.strip().lower()
    if not t or not t.replace("_", "").isalnum():
        raise WriteRefused(f"Refusing table name '{table}'.")
    if t in SUPABASE_FORBIDDEN_TABLES:
        raise WriteRefused(f"'{table}' is permanently read-only.")
    if not SUPABASE_WRITE_TABLES:
        raise WriteRefused("SUPABASE_WRITE_TABLES is empty — no table is writable.")
    if t not in SUPABASE_WRITE_TABLES:
        raise WriteRefused(
            f"'{table}' is not on the write allowlist. Ask Dal to add it, don't route around it."
        )


def tool_supabase_insert_row(table, values):
    _check_table(table)
    if not isinstance(values, dict) or not values:
        raise WriteRefused("values must be a non-empty object.")

    r = requests.post(
        f"{SUPABASE_URL}/rest/v1/{table}",
        headers=_sb_headers(),
        json=values,
        timeout=TIMEOUT,
    )
    if r.status_code not in (200, 201):
        raise WriteRefused(f"Insert failed: {r.status_code} {r.text[:300]}")
    return f"Inserted into {table}:\n{json.dumps(r.json(), indent=2)[:1500]}"


def tool_supabase_update_row(
    table, row_id, values, id_column = "id"
):
    """Update exactly one row, matched on its primary key."""
    _check_table(table)
    if not row_id:
        raise WriteRefused("row_id is required — no bulk updates.")
    if not isinstance(values, dict) or not values:
        raise WriteRefused("values must be a non-empty object.")
    if id_column in values:
        raise WriteRefused("Refusing to change a row's primary key.")
    if not id_column.replace("_", "").isalnum():
        raise WriteRefused(f"Refusing id_column '{id_column}'.")

    r = requests.patch(
        f"{SUPABASE_URL}/rest/v1/{table}",
        headers=_sb_headers(),
        params={id_column: f"eq.{row_id}"},
        json=values,
        timeout=TIMEOUT,
    )
    if r.status_code not in (200, 204):
        raise WriteRefused(f"Update failed: {r.status_code} {r.text[:300]}")
    rows = r.json() if r.text.strip() else []
    if isinstance(rows, list) and len(rows) > 1:
        return (
            f"WARNING: {len(rows)} rows matched {id_column}={row_id} in {table}. "
            "That column is not unique — tell Dal before doing this again."
        )
    if not rows:
        return f"No row matched {id_column}={row_id} in {table}. Nothing changed."
    return f"Updated {table} row {row_id}:\n{json.dumps(rows, indent=2)[:1500]}"


# -------------------------------------------------------------------- registry

WRITE_TOOL_FUNCTIONS = {
    "github_create_branch": tool_github_create_branch,
    "github_write_file": tool_github_write_file,
    "github_open_pr": tool_github_open_pr,
    "supabase_insert_row": tool_supabase_insert_row,
    "supabase_update_row": tool_supabase_update_row,
}

READ_TOOL_FUNCTIONS = {}

for _name in WRITE_TOOL_FUNCTIONS:
    register_write_tool(_name)


# Merged into tools.py's TOOL_SCHEMAS / TOOL_FUNCTIONS by three lines there.
# Lovable tools deliberately absent. Lovable exposes no REST API for project
# messages - only an MCP server at mcp.lovable.dev, which is OAuth-only and whose
# OAuth flow is restricted to ChatGPT/Claude/Cursor/VS Code. A Python service
# cannot connect. To change a Lovable app, write to the GitHub repo it syncs with.

WRITE_TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "github_create_branch",
            "description": "Create a new branch in one of Dal's repos. Requires Dal's confirmation before it runs. Branch names should be brooksy/<short-description>.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "owner/name"
                    },
                    "new_branch": {
                        "type": "string"
                    },
                    "from_branch": {
                        "type": "string",
                        "default": "main"
                    }
                },
                "required": [
                    "repo",
                    "new_branch"
                ]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "github_write_file",
            "description": "Create or update one file on a non-default branch. Read the file first. Never targets main/master/production. Requires Dal's confirmation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "owner/name"
                    },
                    "path": {
                        "type": "string"
                    },
                    "content": {
                        "type": "string",
                        "description": "Full new file contents"
                    },
                    "message": {
                        "type": "string",
                        "description": "One-line commit message"
                    },
                    "branch": {
                        "type": "string"
                    }
                },
                "required": [
                    "repo",
                    "path",
                    "content",
                    "message",
                    "branch"
                ]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "github_open_pr",
            "description": "Open a pull request. Body should cover what changed, why, what was not touched, and what Dal should test. Requires Dal's confirmation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string"
                    },
                    "head": {
                        "type": "string",
                        "description": "Branch with the changes"
                    },
                    "title": {
                        "type": "string"
                    },
                    "body": {
                        "type": "string"
                    },
                    "base": {
                        "type": "string",
                        "default": "main"
                    }
                },
                "required": [
                    "repo",
                    "head",
                    "title"
                ]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "supabase_insert_row",
            "description": "Insert one row into an allowlisted table. Requires Dal's confirmation. There is no delete tool and never will be.",
            "parameters": {
                "type": "object",
                "properties": {
                    "table": {
                        "type": "string"
                    },
                    "values": {
                        "type": "object"
                    }
                },
                "required": [
                    "table",
                    "values"
                ]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "supabase_update_row",
            "description": "Update exactly one row by primary key in an allowlisted table. Query the row first. No bulk updates. Requires Dal's confirmation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "table": {
                        "type": "string"
                    },
                    "row_id": {
                        "type": "string"
                    },
                    "values": {
                        "type": "object"
                    },
                    "id_column": {
                        "type": "string",
                        "default": "id"
                    }
                },
                "required": [
                    "table",
                    "row_id",
                    "values"
                ]
            }
        }
    }
]
