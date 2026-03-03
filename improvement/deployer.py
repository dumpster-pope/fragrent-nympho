"""
Deployer — Applies sandbox changes to production and commits via git.
Only called after all 9 tests pass.
"""

import logging
import shutil
import subprocess
from pathlib import Path

log = logging.getLogger("improvement.deployer")

BOT_DIR     = Path(__file__).parent.parent
SANDBOX_DIR = BOT_DIR / "_improvement_sandbox"


def _git(args: list[str]) -> tuple[int, str]:
    result = subprocess.run(
        ["git"] + args,
        cwd=str(BOT_DIR),
        capture_output=True,
        text=True,
    )
    return result.returncode, (result.stdout + result.stderr).strip()


def deploy(proposal: dict, sandbox: Path = None) -> str | None:
    """
    Copy modified files from sandbox to production and make a git commit.
    Returns the new commit hash on success, None on failure.
    """
    if sandbox is None:
        sandbox = SANDBOX_DIR

    files = proposal.get("files", [])
    if not files:
        log.warning("No files to deploy")
        return None

    # Check production isn't locked by the art bot
    lock = BOT_DIR / "artbot.lock"
    if lock.exists():
        log.warning("artbot.lock is present — waiting up to 120s for bot to finish")
        import time
        for _ in range(24):
            time.sleep(5)
            if not lock.exists():
                break
        if lock.exists():
            log.error("artbot.lock still present after 120s — aborting deploy")
            return None

    # Copy each file from sandbox to production
    for fname in files:
        src = sandbox / fname
        dst = BOT_DIR / fname
        if not src.exists():
            log.error(f"Sandbox file missing: {fname}")
            return None
        shutil.copy2(src, dst)
        log.info(f"Deployed: {fname}")

    # Git add + commit
    rc, out = _git(["add"] + files)
    if rc != 0:
        log.error(f"git add failed: {out}")
        return None

    description = proposal.get("description", "Automated improvement")
    category    = proposal.get("category", "UNKNOWN")
    msg = f"improvement[{category}]: {description[:80]}"

    rc, out = _git(["commit", "-m", msg])
    if rc != 0:
        log.error(f"git commit failed: {out}")
        return None

    # Get commit hash
    _, commit_hash = _git(["rev-parse", "--short", "HEAD"])
    log.info(f"Deployed commit {commit_hash}: {msg}")
    return commit_hash.strip()
