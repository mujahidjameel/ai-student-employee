"""
AI Employee Vault — Filesystem Watcher
Monitors /Inbox and moves new files to /Needs_Action with a task note.
"""

import shutil
import time
from datetime import datetime
from pathlib import Path

VAULT = Path("/mnt/d/AI-EMPLOYEE-VAULT")
INBOX = VAULT / "Inbox"
NEEDS_ACTION = VAULT / "Needs_Action"
POLL_INTERVAL = 10  # seconds


def create_task_note(original_file: Path, moved_to: Path) -> None:
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    datetime_str = now.strftime("%Y-%m-%d %H:%M:%S")
    note_name = f"{date_str} Task - {original_file.name}.md"
    note_path = NEEDS_ACTION / note_name

    content = f"""# Task: {original_file.name}

**Date Received:** {datetime_str}
**Original Location:** Inbox
**Moved To:** {moved_to}
**Owner:** Unassigned
**Status:** pending

## Desired Outcome
Process and action the received file.

## Checklist
- [ ] Review
- [ ] Process
- [ ] Move to Done

## Notes
"""

    note_path.write_text(content, encoding="utf-8")
    print(f"  [note]  Created task note: {note_name}")


def process_inbox() -> None:
    # Ignore hidden files
    new_files = [
        f for f in INBOX.iterdir()
        if f.is_file() and not f.name.startswith(".")
    ]

    for file in new_files:
        dest = NEEDS_ACTION / file.name
        # Avoid overwriting if a file with the same name already exists
        if dest.exists():
            stem = file.stem
            suffix = file.suffix
            timestamp = datetime.now().strftime("%H%M%S")
            dest = NEEDS_ACTION / f"{stem}_{timestamp}{suffix}"

        shutil.move(str(file), str(dest))
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Detected: {file.name}")
        print(f"  [move]  Inbox -> Needs_Action/{dest.name}")
        create_task_note(file, dest)


def main() -> None:
    INBOX.mkdir(parents=True, exist_ok=True)
    NEEDS_ACTION.mkdir(parents=True, exist_ok=True)

    print("AI Employee Vault — Filesystem Watcher")
    print(f"Watching: {INBOX}")
    print(f"Polling every {POLL_INTERVAL} seconds. Press Ctrl+C to stop.\n")

    try:
        while True:
            process_inbox()
            time.sleep(POLL_INTERVAL)
    except KeyboardInterrupt:
        print("\nWatcher stopped.")


if __name__ == "__main__":
    main()
