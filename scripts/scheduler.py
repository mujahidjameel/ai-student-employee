"""
AI Employee Vault — Daily Scheduler
Runs plan_generator.py every day at 09:00 using the `schedule` library.
"""

import logging
import subprocess
import sys
from pathlib import Path

import schedule
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [scheduler] %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

VAULT    = Path(__file__).parent.parent
SCRIPT   = Path(__file__).parent / "plan_generator.py"
PYTHON   = sys.executable
RUN_TIME = "09:00"


def run_plan_generator() -> None:
    log.info("Running plan_generator.py …")
    result = subprocess.run(
        [PYTHON, str(SCRIPT)],
        capture_output=True,
        text=True,
        cwd=str(VAULT),
    )
    if result.returncode == 0:
        log.info("plan_generator.py completed successfully.")
        if result.stdout:
            for line in result.stdout.strip().splitlines():
                log.info("  %s", line)
    else:
        log.error("plan_generator.py failed (exit %d).", result.returncode)
        if result.stderr:
            for line in result.stderr.strip().splitlines():
                log.error("  %s", line)


def main() -> None:
    log.info("Scheduler started — plan_generator.py will run daily at %s.", RUN_TIME)
    schedule.every().day.at(RUN_TIME).do(run_plan_generator)

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
