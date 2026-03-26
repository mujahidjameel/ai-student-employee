# CLAUDE.md — AI Employee Vault Constitution

## Project Identity
**Project:** Hackathon 0 — Silver Tier
**Vault:** D:\AI-EMPLOYEE-VAULT
**Purpose:** Operate as an AI student employee managing tasks, knowledge, and workflows through an Obsidian vault — with automated ingestion, AI-generated planning, scheduled execution, and a human-approval gate on sensitive actions.

---

## Architecture Overview

The vault operates as a pipeline of loosely-coupled scripts. Each layer hands off to the next:

```
External inputs                 Automation layer              Vault folders
──────────────                  ────────────────              ─────────────
Gmail inbox        →  gmail_watcher.py       →  /Needs_Action  (task notes)
Files dropped      →  filesystem_watcher.py  →  /Needs_Action  (task notes)
                                                     │
                                              /Inbox (raw files also land here
                                               before filesystem_watcher moves them)
                                                     │
                                                     ▼
                                             plan_generator.py  →  Plan.md
                                                     │
                                             scheduler.py  (runs plan_generator
                                                           daily at 09:00)
                                                     │
                                             hitl_approval.py  (gate before any
                                                               sensitive action)
                                                     │
                                             mcp_email_sender.py  (send replies
                                                                   via MCP tool)
```

**Data flow summary:**

1. Inputs arrive via Gmail or the filesystem and are auto-triaged into `/Needs_Action`.
2. `plan_generator.py` reads `/Inbox` + `Dashboard.md` and produces a prioritised `Plan.md` using Gemini.
3. `scheduler.py` runs the plan generator every morning at 09:00 without manual intervention.
4. Before any sensitive action (send, delete, push…) `hitl_approval.py` pauses and asks for Y/N.
5. Outbound emails are sent through `mcp_email_sender.py` exposed as an MCP tool.

---

## Vault Structure

```
D:\AI-EMPLOYEE-VAULT\
├── CLAUDE.md                  ← This file (constitution)
├── Dashboard.md               ← Central status overview
├── Company_Handbook.md        ← SOPs and ground rules
├── Plan.md                    ← Daily plan (auto-generated, overwritten each run)
├── .env                       ← API keys (not committed)
├── Inbox\                     ← All new, unprocessed inputs
├── Needs_Action\              ← Triaged items awaiting action
├── Done\                      ← Completed and archived items
├── scripts\                   ← Automation scripts (see below)
└── skills\                    ← Per-skill documentation
    ├── filesystem_watcher\SKILL.md
    ├── gmail_watcher\SKILL.md
    ├── plan_generator\SKILL.md
    ├── hitl_approval\SKILL.md
    ├── mcp_email_sender\SKILL.md
    └── scheduler\SKILL.md
```

---

## Scripts Reference

### `scripts/filesystem_watcher.py`
**What it does:** Polls `/Inbox` every 10 seconds. When a new file appears it moves it to `/Needs_Action` and creates a stub task note (`YYYY-MM-DD Task - <filename>.md`).
**Run:**
```bash
python /mnt/d/AI-EMPLOYEE-VAULT/scripts/filesystem_watcher.py
```
**Type:** Long-running background watcher. Stop with `Ctrl+C`.
**Deps:** Standard library only.
**Full docs:** [[skills/filesystem_watcher/SKILL]]

---

### `scripts/gmail_watcher.py`
**What it does:** Polls Gmail every 60 seconds for unread important emails (`is:unread is:important`). Saves each email as a task note in `/Needs_Action` and marks it read in Gmail to prevent duplicates.
**Run:**
```bash
python /mnt/d/AI-EMPLOYEE-VAULT/scripts/gmail_watcher.py
```
**Type:** Long-running background watcher. Stop with `Ctrl+C`.
**Deps:** `google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client`
**Auth:** Requires `client_secret_...json` in `scripts/`. Opens browser on first run; saves `gmail_token.json` for subsequent runs.
**Full docs:** [[skills/gmail_watcher/SKILL]]

---

### `scripts/plan_generator.py`
**What it does:** One-shot script. Reads all `.md` files in `/Inbox` (up to 50) and `Dashboard.md`, sends them to Gemini (`gemini-2.5-flash`), and writes a structured `Plan.md` to the vault root.
**Run:**
```bash
python /mnt/d/AI-EMPLOYEE-VAULT/scripts/plan_generator.py
```
**Type:** One-shot (exits after writing `Plan.md`).
**Deps:** `google-genai python-dotenv`
**Auth:** `GOOGLE_API_KEY` in `.env` at vault root.
**Full docs:** [[skills/plan_generator/SKILL]]

---

### `scripts/scheduler.py`
**What it does:** Long-running process that fires `plan_generator.py` as a subprocess every day at 09:00. Logs all output with timestamps. Change `RUN_TIME` at the top of the file to adjust the schedule.
**Run:**
```bash
python /mnt/d/AI-EMPLOYEE-VAULT/scripts/scheduler.py
# or background:
nohup python /mnt/d/AI-EMPLOYEE-VAULT/scripts/scheduler.py >> scheduler.log 2>&1 &
```
**Type:** Long-running scheduler. Stop with `Ctrl+C`.
**Deps:** `schedule`
**Full docs:** [[skills/scheduler/SKILL]]

---

### `scripts/hitl_approval.py`
**What it does:** Human-in-the-Loop gate. Auto-detects sensitive keywords (`delete`, `send`, `email`, `push`, `deploy`, etc.) in an action description and prompts for Y/N before proceeding. Can be used as a CLI tool (exit code 0/1) or imported as a Python module (`guard()` / `request_approval()`).
**Run (CLI):**
```bash
python /mnt/d/AI-EMPLOYEE-VAULT/scripts/hitl_approval.py "send email to client" --details "To: boss@co.com"
# exit 0 = approved, exit 1 = denied
```
**Import:**
```python
from hitl_approval import guard
if guard("delete file", details="Inbox/old-task.md"):
    do_the_thing()
```
**Type:** On-demand / imported module. No background process.
**Deps:** Standard library only.
**Full docs:** [[skills/hitl_approval/SKILL]]

---

### `scripts/mcp_email_sender.py`
**What it does:** MCP server (stdio transport, JSON-RPC 2.0) exposing a single `send_email(to, subject, body)` tool. Sends plain-text email via Gmail API. Register it in Claude Code's MCP config to give Claude the ability to send email directly.
**Run:**
```bash
python /mnt/d/AI-EMPLOYEE-VAULT/scripts/mcp_email_sender.py
```
**MCP config (`.claude/mcp_servers.json`):**
```json
{
  "mcp_email_sender": {
    "command": "python",
    "args": ["/mnt/d/AI-EMPLOYEE-VAULT/scripts/mcp_email_sender.py"]
  }
}
```
**Type:** Long-running MCP server (stdin/stdout).
**Deps:** `google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client`
**Auth:** Shares `gmail_token.json` with `gmail_watcher.py`. Browser auth on first run.
**Full docs:** [[skills/mcp_email_sender/SKILL]]

---

## Environment Setup

### Install all dependencies at once
```bash
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client \
            google-genai python-dotenv schedule
```

### `.env` file (vault root)
```
GOOGLE_API_KEY=your_google_api_key_here
```

### Required files in `scripts/`
| File | Purpose |
|------|---------|
| `client_secret_...json` | Gmail OAuth2 credentials from Google Cloud Console |
| `gmail_token.json` | Auto-generated after first Gmail authorisation |
| `.env` (vault root) | `GOOGLE_API_KEY` for Gemini API |

---

## Core Workflow Rules

1. **All new items go to `/Inbox` first** — no exceptions.
2. **Triage moves items to `/Needs_Action`** — add context, owner, and desired outcome.
3. **Completed items move to `/Done`** — always append a completion note before moving.
4. **Never delete notes** — move or tag as `SUPERSEDED`.
5. **Sensitive actions require HITL approval** — call `hitl_approval.guard()` before any send, delete, push, or deploy.

---

## Behavior Guidelines

- Follow the workflow in `Company_Handbook.md` without deviation unless explicitly instructed otherwise.
- Surface blockers and ambiguities immediately — do not guess.
- Keep `Dashboard.md` up to date when the state of work changes.
- Use Obsidian wiki-link syntax (`[[Note Name]]`) for internal references.
- Prefer editing existing files over creating new ones.
- Do not add unnecessary commentary, emojis, or filler to notes.

---

## File Conventions

- Note titles: `YYYY-MM-DD Topic Name.md` for dated notes, plain `Topic Name.md` for reference docs.
- Every task note must include: **Title**, **Date**, **Owner**, **Desired Outcome**, **Status**.
- Completion notes appended as: `## Resolution\n[date] [what was done]`

---

## What NOT to Do

- Do not create files outside the defined folder structure without instruction.
- Do not push, delete, or destructively modify files without explicit user approval.
- Do not assume completion — confirm when in doubt.
- Do not store ephemeral task state in memory files; use the vault itself.
- Do not send email or take any sensitive action without first calling `hitl_approval.guard()`.

---

## Memory System

Persistent memory lives at `C:\Users\Bajwa\.claude\projects\D--AI-EMPLOYEE-VAULT\memory\`.
Save user preferences, feedback, and project context there across sessions.

---

## Revision History

| Date | Change |
|------|--------|
| 2026-03-17 | Initial constitution created for Hackathon 0 Bronze Tier |
| 2026-03-26 | Updated to Silver Tier — added architecture overview, full scripts reference, environment setup, and HITL rule |
