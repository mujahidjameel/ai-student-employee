"""
AI Employee Vault — Gmail Watcher
Monitors unread important emails and saves them as task notes in /Needs_Action.
"""

import os
import re
import time
import base64
from datetime import datetime
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# ── Paths ──────────────────────────────────────────────────────────────────────
VAULT        = Path("/mnt/d/AI-EMPLOYEE-VAULT")
SCRIPTS      = VAULT / "scripts"
NEEDS_ACTION = VAULT / "Needs_Action"
CREDENTIALS  = SCRIPTS / "client_secret_938744955997-7ll17btqah5bt1en7gvmlj64l25gr7cj.apps.googleusercontent.com.json"
TOKEN_FILE   = SCRIPTS / "gmail_token.json"

# ── Config ─────────────────────────────────────────────────────────────────────
SCOPES        = ["https://www.googleapis.com/auth/gmail.modify"]
POLL_INTERVAL = 60   # seconds between checks
# Gmail query: unread + marked important. Adjust as needed.
QUERY         = "is:unread is:important"


# ── Auth ───────────────────────────────────────────────────────────────────────
def get_service():
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS), SCOPES
            )
            creds = flow.run_local_server(port=0)
        TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
    return build("gmail", "v1", credentials=creds)


# ── Helpers ────────────────────────────────────────────────────────────────────
def decode_body(payload: dict) -> str:
    """Extract plain-text body from a message payload."""
    if payload.get("mimeType") == "text/plain":
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

    for part in payload.get("parts", []):
        result = decode_body(part)
        if result:
            return result

    return ""


def safe_filename(text: str, max_len: int = 60) -> str:
    """Sanitise a string for use in a filename."""
    text = re.sub(r'[\\/*?:"<>|]', "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_len]


def header_value(headers: list, name: str) -> str:
    for h in headers:
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


def already_saved(msg_id: str) -> bool:
    """Check if a note for this message ID already exists."""
    for f in NEEDS_ACTION.glob("*.md"):
        if msg_id in f.read_text(encoding="utf-8"):
            return True
    return False


# ── Core ───────────────────────────────────────────────────────────────────────
def save_email_as_note(service, msg_id: str) -> None:
    msg = service.users().messages().get(
        userId="me", id=msg_id, format="full"
    ).execute()

    headers  = msg["payload"].get("headers", [])
    subject  = header_value(headers, "Subject") or "(no subject)"
    sender   = header_value(headers, "From")
    date_hdr = header_value(headers, "Date")
    body     = decode_body(msg["payload"]).strip()

    date_str     = datetime.now().strftime("%Y-%m-%d")
    datetime_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    safe_subj    = safe_filename(subject)
    note_name    = f"{date_str} Email - {safe_subj}.md"
    note_path    = NEEDS_ACTION / note_name

    # Avoid filename collision
    counter = 1
    while note_path.exists():
        note_path = NEEDS_ACTION / f"{date_str} Email - {safe_subj} ({counter}).md"
        counter += 1

    content = f"""# Email: {subject}

**Date Received:** {datetime_str}
**From:** {sender}
**Original Date:** {date_hdr}
**Gmail Message ID:** {msg_id}
**Owner:** Unassigned
**Status:** pending

## Desired Outcome
Review and action this email.

## Checklist
- [ ] Read
- [ ] Reply / Forward / Delegate
- [ ] Move to Done

## Body

{body if body else "_No plain-text body available._"}

## Notes

"""

    note_path.write_text(content, encoding="utf-8")
    print(f"  [note]  Saved: {note_path.name}")

    # Mark email as read so it won't be picked up again
    service.users().messages().modify(
        userId="me",
        id=msg_id,
        body={"removeLabelIds": ["UNREAD"]}
    ).execute()
    print(f"  [read]  Marked as read in Gmail")


def poll(service) -> None:
    results = service.users().messages().list(
        userId="me", q=QUERY, maxResults=20
    ).execute()

    messages = results.get("messages", [])
    if not messages:
        return

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Found {len(messages)} unread important email(s)")

    for m in messages:
        msg_id = m["id"]
        if already_saved(msg_id):
            print(f"  [skip]  {msg_id} already saved")
            continue
        save_email_as_note(service, msg_id)


# ── Entry point ────────────────────────────────────────────────────────────────
def main() -> None:
    NEEDS_ACTION.mkdir(parents=True, exist_ok=True)

    print("AI Employee Vault — Gmail Watcher")
    print(f"Query: {QUERY}")
    print(f"Polling every {POLL_INTERVAL} seconds. Press Ctrl+C to stop.\n")

    service = get_service()

    try:
        while True:
            poll(service)
            time.sleep(POLL_INTERVAL)
    except KeyboardInterrupt:
        print("\nWatcher stopped.")


if __name__ == "__main__":
    main()
