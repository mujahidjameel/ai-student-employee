"""
AI Employee Vault — MCP Email Sender
Exposes a single MCP tool: send_email(to, subject, body)
Uses the Gmail API with the same OAuth credentials as gmail_watcher.py.

Run as an MCP server:
    python scripts/mcp_email_sender.py

The server communicates over stdin/stdout (MCP stdio transport).
"""

import base64
import json
import sys
from email.mime.text import MIMEText
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# ── Paths ───────────────────────────────────────────────────────────────────
SCRIPTS     = Path(__file__).parent
CREDENTIALS = SCRIPTS / "client_secret_938744955997-7ll17btqah5bt1en7gvmlj64l25gr7cj.apps.googleusercontent.com.json"
TOKEN_FILE  = SCRIPTS / "gmail_token.json"

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

# ── Auth ─────────────────────────────────────────────────────────────────────

def get_gmail_service():
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_FILE.write_text(creds.to_json())
    return build("gmail", "v1", credentials=creds)


# ── Tool implementation ───────────────────────────────────────────────────────

def send_email(to: str, subject: str, body: str) -> dict:
    """Send an email via Gmail API. Returns a result dict."""
    service = get_gmail_service()
    message = MIMEText(body)
    message["to"] = to
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    sent = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    return {"status": "sent", "message_id": sent.get("id")}


# ── MCP stdio server ──────────────────────────────────────────────────────────

TOOL_MANIFEST = {
    "tools": [
        {
            "name": "send_email",
            "description": (
                "Send an email via Gmail. "
                "Requires prior OAuth authorisation (run once interactively)."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "to":      {"type": "string", "description": "Recipient email address"},
                    "subject": {"type": "string", "description": "Email subject line"},
                    "body":    {"type": "string", "description": "Plain-text email body"},
                },
                "required": ["to", "subject", "body"],
            },
        }
    ]
}


def handle_request(req: dict) -> dict:
    method = req.get("method", "")
    req_id = req.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0", "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "mcp-email-sender", "version": "1.0.0"},
            },
        }

    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": TOOL_MANIFEST}

    if method == "tools/call":
        params = req.get("params", {})
        tool   = params.get("name")
        args   = params.get("arguments", {})

        if tool == "send_email":
            try:
                result = send_email(
                    to=args["to"],
                    subject=args["subject"],
                    body=args["body"],
                )
                return {
                    "jsonrpc": "2.0", "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(result)}],
                        "isError": False,
                    },
                }
            except Exception as exc:
                return {
                    "jsonrpc": "2.0", "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": f"Error: {exc}"}],
                        "isError": True,
                    },
                }

    return {
        "jsonrpc": "2.0", "id": req_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError as exc:
            resp = {"jsonrpc": "2.0", "id": None,
                    "error": {"code": -32700, "message": f"Parse error: {exc}"}}
            print(json.dumps(resp), flush=True)
            continue

        resp = handle_request(req)
        print(json.dumps(resp), flush=True)


if __name__ == "__main__":
    main()
