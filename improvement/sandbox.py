"""
Sandbox — Creates an isolated copy of the AIArtBot project for safe testing.
Production files are never touched until all tests pass.
"""

import logging
import shutil
from pathlib import Path

log = logging.getLogger("improvement.sandbox")

BOT_DIR     = Path(__file__).parent.parent
SANDBOX_DIR = BOT_DIR / "_improvement_sandbox"

# Files/dirs to exclude from sandbox copy
_EXCLUDE = {
    "_improvement_sandbox",
    "__pycache__",
    ".git",
    "logs",
    "chrome_profile",
    "ChromeProfile",
    ".gitignore",
    "improvement.lock",
}


def create() -> Path:
    """Copy the production directory to _improvement_sandbox/. Returns sandbox path."""
    if SANDBOX_DIR.exists():
        shutil.rmtree(SANDBOX_DIR)

    def _ignore(src, names):
        return [n for n in names if n in _EXCLUDE or n.startswith("chrome_profile")]

    shutil.copytree(BOT_DIR, SANDBOX_DIR, ignore=_ignore)
    log.info(f"Sandbox created at {SANDBOX_DIR}")
    return SANDBOX_DIR


def apply_changes(proposal: dict, sandbox: Path) -> bool:
    """
    Apply the proposal's changes to the sandbox copy.
    Returns True on success, False on any error.
    """
    changes = proposal.get("changes", [])
    if not changes:
        log.warning("Proposal has no changes — nothing to apply")
        return False

    for change in changes:
        action = change.get("action", "")
        try:
            if action == "replace_snippet":
                _apply_replace(change, sandbox)
            elif action == "add_function":
                _apply_add_function(change, sandbox)
            elif action in ("add_hashtag_entries", "add_comment_entries"):
                _apply_add_list_entries(change, sandbox)
            elif action == "add_list_entries":
                _apply_add_to_list(change, sandbox)
            else:
                log.warning(f"Unknown action '{action}' — skipping")
        except Exception as e:
            log.error(f"Failed to apply change {action}: {e}")
            return False
    return True


def teardown() -> None:
    """Remove the sandbox directory."""
    if SANDBOX_DIR.exists():
        shutil.rmtree(SANDBOX_DIR)
        log.info("Sandbox removed")


def _resolve_file(change: dict, sandbox: Path) -> Path:
    fname = change.get("file", "")
    if not fname:
        raise ValueError("Change missing 'file' key")
    target = sandbox / fname
    if not target.exists():
        raise FileNotFoundError(f"Sandbox file not found: {target}")
    return target


def _apply_replace(change: dict, sandbox: Path) -> None:
    target = _resolve_file(change, sandbox)
    old_snippet = change.get("old_snippet", "")
    new_snippet = change.get("new_snippet", "")
    if not old_snippet:
        raise ValueError("replace_snippet missing old_snippet")
    content = target.read_text(encoding="utf-8")
    if old_snippet not in content:
        raise ValueError(f"old_snippet not found in {target.name}")
    target.write_text(content.replace(old_snippet, new_snippet, 1), encoding="utf-8")
    log.info(f"Applied replace_snippet to {target.name}")


def _apply_add_function(change: dict, sandbox: Path) -> None:
    """Append a new function to the end of a file."""
    fname = change.get("file", change.get("files", ["art_bot.py"])[0] if isinstance(change.get("files"), list) else "art_bot.py")
    target = sandbox / fname
    code = change.get("code", "")
    if not code:
        raise ValueError("add_function missing code")
    content = target.read_text(encoding="utf-8")
    content += f"\n\n{code}\n"
    target.write_text(content, encoding="utf-8")
    log.info(f"Appended function to {target.name}")


def _apply_add_list_entries(change: dict, sandbox: Path) -> None:
    """Add entries to hashtag map or comment pool via simple string injection."""
    action = change.get("action", "")
    if action == "add_hashtag_entries":
        target = sandbox / "instagram_bot.py"
        entries = change.get("entries", {})
        content = target.read_text(encoding="utf-8")
        # Find the HASHTAG_MAP closing brace and inject before it
        insert_lines = ""
        for key, tags in entries.items():
            tag_list = ", ".join(f'"{t}"' for t in tags)
            insert_lines += f'    "{key}":      [{tag_list}],\n'
        # Inject before the closing } of HASHTAG_MAP
        marker = "}\n\n# ── Mood"
        if marker not in content:
            marker = "}\n\nlog"
        if marker not in content:
            raise ValueError("Could not find HASHTAG_MAP end marker in instagram_bot.py")
        content = content.replace(marker, insert_lines + marker, 1)
        target.write_text(content, encoding="utf-8")
        log.info(f"Added hashtag entries to instagram_bot.py")

    elif action == "add_comment_entries":
        file_name = change.get("file", "engagement_bot.py")
        target = sandbox / file_name
        pool_name = change.get("pool_name", "GENERIC_COMMENTS")
        new_entries = change.get("new_entries", [])
        content = target.read_text(encoding="utf-8")
        # Find the pool list and append entries before closing bracket
        import re
        pattern = rf'({re.escape(pool_name)}\s*=\s*\[)(.*?)(\])'
        m = re.search(pattern, content, re.DOTALL)
        if not m:
            raise ValueError(f"Could not find {pool_name} in {file_name}")
        existing = m.group(2)
        new_lines = "".join(f'\n    "{e}",' for e in new_entries)
        replacement = m.group(1) + existing + new_lines + "\n" + m.group(3)
        content = content[:m.start()] + replacement + content[m.end():]
        target.write_text(content, encoding="utf-8")
        log.info(f"Added comment entries to {file_name}")


def _apply_add_to_list(change: dict, sandbox: Path) -> None:
    """Add new entries to a named list in prompt_agent.py."""
    import re
    target = sandbox / "prompt_agent.py"
    list_name = change.get("list_name", "")
    new_entries = change.get("new_entries", [])
    if not list_name or not new_entries:
        raise ValueError("add_list_entries missing list_name or new_entries")

    content = target.read_text(encoding="utf-8")
    # Find the list and append before its closing bracket
    # Handles both top-level lists and dict values
    pattern = rf'("{re.escape(list_name)}"\s*:\s*\[|{re.escape(list_name)}\s*=\s*\[)(.*?)(\n\s*\])'
    m = re.search(pattern, content, re.DOTALL)
    if not m:
        raise ValueError(f"Could not find list '{list_name}' in prompt_agent.py")
    new_lines = "".join(f'\n        "{e}",' for e in new_entries)
    replacement = m.group(1) + m.group(2) + new_lines + m.group(3)
    content = content[:m.start()] + replacement + content[m.end():]
    target.write_text(content, encoding="utf-8")
    log.info(f"Added {len(new_entries)} entries to {list_name} in prompt_agent.py")
