"""
AI Employee Vault — Plan Generator
Reads /Inbox and Dashboard.md, then uses Gemini to generate a structured Plan.md.
"""

import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from google import genai

# Load .env from vault root before anything else reads env vars
load_dotenv(Path(__file__).parent.parent / ".env")

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")

# ── Paths ──────────────────────────────────────────────────────────────────────
VAULT     = Path("/mnt/d/AI-EMPLOYEE-VAULT")
INBOX     = VAULT / "Inbox"
DASHBOARD = VAULT / "Dashboard.md"
PLAN_OUT  = VAULT / "Plan.md"

# ── Config ─────────────────────────────────────────────────────────────────────
MODEL     = "gemini-2.5-flash"
MAX_FILES = 50   # cap on Inbox files to avoid blowing the context window


# ── Helpers ────────────────────────────────────────────────────────────────────
def read_inbox() -> list[tuple[str, str]]:
    """Return a list of (filename, content) for every .md file in /Inbox."""
    files = sorted(INBOX.glob("*.md"))[:MAX_FILES]
    results = []
    for f in files:
        try:
            results.append((f.name, f.read_text(encoding="utf-8")))
        except OSError:
            results.append((f.name, "[could not read file]"))
    return results


def read_dashboard() -> str:
    try:
        return DASHBOARD.read_text(encoding="utf-8")
    except OSError:
        return "[Dashboard.md not found]"


def build_prompt(today: str, inbox_items: list[tuple[str, str]], dashboard: str) -> str:
    inbox_section = ""
    if inbox_items:
        for name, content in inbox_items:
            inbox_section += f"### {name}\n{content.strip()}\n\n"
    else:
        inbox_section = "_No files found in /Inbox._\n"

    return f"""You are an AI student employee operating a personal knowledge vault. Today is {today}.

Your job is to review the items currently sitting in the /Inbox folder and produce a clear, actionable daily plan.

---

## Dashboard (current vault context)

{dashboard.strip()}

---

## Inbox Items ({len(inbox_items)} file(s))

{inbox_section.strip()}

---

## Instructions

Write a structured Plan.md with exactly these sections:

1. **# Daily Plan — {today}**
2. **## Inbox Summary** — one-sentence description of each inbox item (list form).
3. **## Prioritised Task List** — ordered list of actions to take today; prefix urgent items with `[URGENT]`.
4. **## Notes & Blockers** — anything ambiguous, blocked, or that needs more information before it can be actioned.

Be concise. Use Obsidian wiki-link syntax ([[Note Name]]) when referencing vault notes. Do not add extra commentary outside these sections."""


# ── Core ───────────────────────────────────────────────────────────────────────
def generate_plan() -> str:
    today       = datetime.now().strftime("%Y-%m-%d")
    inbox_items = read_inbox()
    dashboard   = read_dashboard()

    print(f"Reading Inbox ({len(inbox_items)} item(s))...")
    print("Reading Dashboard.md...")

    prompt = build_prompt(today, inbox_items, dashboard)

    print("Calling Gemini to generate plan...")

    client   = genai.Client(api_key=GOOGLE_API_KEY)
    response = client.models.generate_content(model=MODEL, contents=prompt)

    return response.text.strip()


# ── Entry point ────────────────────────────────────────────────────────────────
def main() -> None:
    if not GOOGLE_API_KEY:
        print("Error: GOOGLE_API_KEY environment variable is not set.")
        sys.exit(1)

    INBOX.mkdir(parents=True, exist_ok=True)

    print("AI Employee Vault — Plan Generator")

    plan = generate_plan()

    PLAN_OUT.write_text(plan + "\n", encoding="utf-8")
    print(f"Plan written to: {PLAN_OUT}")
    print("Done.")


if __name__ == "__main__":
    main()
