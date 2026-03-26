"""
AI Employee Vault — Human-in-the-Loop Approval Gate
Before any sensitive action is executed, this module prints the action and asks
the user for explicit Y/N approval in the terminal.
"""

import sys


SENSITIVE_KEYWORDS = {
    "delete", "remove", "overwrite", "send", "email", "push",
    "deploy", "drop", "truncate", "wipe", "format",
}


def is_sensitive(action: str) -> bool:
    """Return True if the action description contains a sensitive keyword."""
    lower = action.lower()
    return any(kw in lower for kw in SENSITIVE_KEYWORDS)


def request_approval(action: str, details: str = "") -> bool:
    """
    Print the proposed action and ask the user to approve or deny it.

    Returns True if approved, False if denied.
    Raises SystemExit if stdin is not a TTY (non-interactive environments).
    """
    if not sys.stdin.isatty():
        print(
            "[HITL] Non-interactive environment detected. "
            "Cannot prompt for approval — action DENIED by default.",
            file=sys.stderr,
        )
        return False

    print()
    print("=" * 60)
    print("  HUMAN APPROVAL REQUIRED")
    print("=" * 60)
    print(f"  Action  : {action}")
    if details:
        print(f"  Details : {details}")
    print("=" * 60)

    while True:
        try:
            answer = input("  Approve? [Y/N]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n[HITL] Input interrupted — action DENIED.")
            return False

        if answer in ("y", "yes"):
            print("[HITL] Approved.")
            return True
        if answer in ("n", "no"):
            print("[HITL] Denied.")
            return False
        print("  Please enter Y or N.")


def guard(action: str, details: str = "", always_ask: bool = False) -> bool:
    """
    Gate an action behind human approval.

    - If always_ask=True, always prompts regardless of content.
    - Otherwise, only prompts when the action looks sensitive.
    - Returns True if the action should proceed, False if it should be skipped.
    """
    if always_ask or is_sensitive(action):
        return request_approval(action, details)
    return True


# ── CLI usage ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="HITL approval gate — prompt the user before an action."
    )
    parser.add_argument("action", help="Short description of the action to approve")
    parser.add_argument("--details", default="", help="Additional context")
    parser.add_argument(
        "--always", action="store_true", help="Always prompt, not just for sensitive actions"
    )
    args = parser.parse_args()

    approved = guard(args.action, args.details, always_ask=args.always)
    sys.exit(0 if approved else 1)
