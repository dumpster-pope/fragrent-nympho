"""
Rollback — Regression detection and git revert for failed improvement commits.
Uses non-destructive revert (creates a new commit).
"""

import json
import logging
import subprocess
import time
from pathlib import Path

log = logging.getLogger("improvement.rollback")

BOT_DIR    = Path(__file__).parent.parent
STATE_FILE = Path(__file__).parent / "improvement_state.json"
LOG_DIR    = BOT_DIR / "logs"

# Number of ERROR lines in the last 2 hours that triggers a rollback
ERROR_THRESHOLD = 5


def _git(args: list[str]) -> tuple[int, str]:
    result = subprocess.run(
        ["git"] + args,
        cwd=str(BOT_DIR),
        capture_output=True,
        text=True,
    )
    return result.returncode, (result.stdout + result.stderr).strip()


def _load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {}


def _recent_error_count(window_seconds: int = 7200) -> int:
    """Count ERROR lines in log files modified in the last window_seconds."""
    if not LOG_DIR.exists():
        return 0
    cutoff = time.time() - window_seconds
    count = 0
    for lf in LOG_DIR.glob("*.log"):
        if lf.stat().st_mtime < cutoff:
            continue
        try:
            lines = lf.read_text(errors="ignore").splitlines()
            count += sum(1 for l in lines if "ERROR" in l or "CRITICAL" in l)
        except Exception:
            pass
    return count


def check_and_rollback() -> bool:
    """
    Check if the last improvement commit caused a regression.
    If so, revert it. Returns True if a rollback was performed.
    """
    state = _load_state()
    # Collect all last_deploy_commits across categories
    commits = [
        v.get("last_deploy_commit")
        for v in state.values()
        if isinstance(v, dict) and v.get("last_deploy_commit")
    ]
    if not commits:
        log.info("No previous improvement commits to check")
        return False

    error_count = _recent_error_count()
    log.info(f"Recent error count: {error_count}")

    if error_count < ERROR_THRESHOLD:
        return False

    # Find the most recent improvement commit in git log
    rc, log_out = _git(["log", "--oneline", "-20"])
    if rc != 0:
        log.error(f"git log failed: {log_out}")
        return False

    revert_hash = None
    for line in log_out.splitlines():
        parts = line.split(" ", 1)
        if len(parts) < 2:
            continue
        h, msg = parts
        if msg.startswith("improvement[") and h in "".join(commits):
            revert_hash = h
            break
        # Also match by hash prefix
        for c in commits:
            if c and line.startswith(c):
                revert_hash = h
                break

    if not revert_hash:
        # Try matching by commit message prefix
        for line in log_out.splitlines():
            if "improvement[" in line:
                revert_hash = line.split()[0]
                break

    if not revert_hash:
        log.warning("Could not identify improvement commit to revert")
        return False

    log.warning(f"Regression detected ({error_count} errors) — reverting {revert_hash}")
    rc, out = _git(["revert", "--no-edit", revert_hash])
    if rc != 0:
        log.error(f"git revert failed: {out}")
        return False

    log.info(f"Successfully reverted {revert_hash}")

    # Clear the last_deploy_commit in state
    for cat_state in state.values():
        if isinstance(cat_state, dict):
            cat_state["last_deploy_commit"] = None
    STATE_FILE.write_text(json.dumps(state, indent=2))
    return True


def manual_rollback() -> bool:
    """CLI-triggered rollback of the last improvement commit."""
    rc, log_out = _git(["log", "--oneline", "-20"])
    if rc != 0:
        log.error(f"git log failed: {log_out}")
        return False

    for line in log_out.splitlines():
        if "improvement[" in line:
            h = line.split()[0]
            log.info(f"Reverting {h}: {line}")
            rc, out = _git(["revert", "--no-edit", h])
            if rc != 0:
                log.error(f"git revert failed: {out}")
                return False
            log.info(f"Reverted {h}")
            return True

    log.warning("No improvement commit found in recent history")
    return False
