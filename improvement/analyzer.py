"""
Analyzer — Triage: reads logs + engagement metrics, ranks categories by urgency.
Uses Ollama for the ranking decision.
"""

import json
import logging
import re
from pathlib import Path

from improvement.ollama_agent import OllamaAgent

log = logging.getLogger("improvement.analyzer")

BOT_DIR  = Path(__file__).parent.parent
LOG_DIR  = BOT_DIR / "logs"
STATE_FILE = Path(__file__).parent / "improvement_state.json"

CATEGORIES = ["PROMPT_EXPAND", "API_SCOUT", "ENGAGEMENT_TUNE", "BUG_FIX", "FEATURE_PROPOSE"]


def _load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {cat: {"last_run": 0, "last_deploy_commit": None} for cat in CATEGORIES}


def _save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2))


def _read_recent_errors(max_lines: int = 100) -> str:
    """Read ERROR lines from the most recent log file."""
    errors = []
    if not LOG_DIR.exists():
        return ""
    log_files = sorted(LOG_DIR.glob("*.log"), key=lambda f: f.stat().st_mtime, reverse=True)
    for lf in log_files[:3]:
        try:
            lines = lf.read_text(errors="ignore").splitlines()
            errors.extend(l for l in lines if "ERROR" in l or "CRITICAL" in l)
        except Exception:
            pass
    return "\n".join(errors[-max_lines:])


def _read_engagement_metrics() -> str:
    """Read engagement_counts.json if available."""
    counts_file = BOT_DIR / "engagement_counts.json"
    if counts_file.exists():
        try:
            return counts_file.read_text()
        except Exception:
            pass
    return "{}"


class TriageAgent(OllamaAgent):
    name = "TriageAgent"
    temperature = 0.2
    system_prompt = (
        "You are a software triage assistant for an Instagram art bot. "
        "You rank improvement categories by urgency. "
        "Return only valid JSON — a list of category names in order of priority."
    )


def rank_categories(recent_errors: str, engagement_json: str, state: dict) -> list[str]:
    """Ask Ollama to rank categories, fallback to default order on failure."""
    agent = TriageAgent()
    prompt = (
        f"Recent bot errors (last 100 lines):\n{recent_errors or 'None'}\n\n"
        f"Engagement metrics:\n{engagement_json}\n\n"
        f"Category last-run timestamps (Unix): {json.dumps({k: v['last_run'] for k, v in state.items()})}\n\n"
        "Rank these categories by urgency: PROMPT_EXPAND, API_SCOUT, ENGAGEMENT_TUNE, BUG_FIX, FEATURE_PROPOSE\n"
        "Rules: BUG_FIX ranks first if there are ERROR lines. "
        "Categories not run in 24h get a boost. FEATURE_PROPOSE always last.\n"
        "Return JSON array of strings only, e.g.: [\"BUG_FIX\", \"PROMPT_EXPAND\", ...]"
    )
    try:
        raw = agent.call(prompt)
        # Extract JSON array from response
        m = re.search(r'\[.*?\]', raw, re.DOTALL)
        if m:
            ranked = json.loads(m.group())
            # Validate all categories present
            if set(ranked) == set(CATEGORIES):
                return ranked
    except Exception as e:
        log.warning(f"Triage agent failed: {e}")

    # Fallback: BUG_FIX first if errors, else default order
    if recent_errors.strip():
        order = ["BUG_FIX", "PROMPT_EXPAND", "ENGAGEMENT_TUNE", "API_SCOUT", "FEATURE_PROPOSE"]
    else:
        order = ["PROMPT_EXPAND", "ENGAGEMENT_TUNE", "BUG_FIX", "API_SCOUT", "FEATURE_PROPOSE"]
    return order


def select_categories(n: int = 2) -> tuple[list[str], dict]:
    """
    Returns (selected_categories, state) where selected_categories are the top
    n categories not run in the last 24 hours (skipping FEATURE_PROPOSE for auto-deploy).
    """
    import time
    state = _load_state()
    errors = _read_recent_errors()
    metrics = _read_engagement_metrics()

    ranked = rank_categories(errors, metrics, state)
    now = time.time()
    cooldown = 24 * 3600  # 24 hours

    selected = []
    for cat in ranked:
        if len(selected) >= n:
            break
        last = state.get(cat, {}).get("last_run", 0)
        if (now - last) >= cooldown:
            selected.append(cat)

    # If nothing qualifies (all run recently), pick top 1 anyway
    if not selected:
        selected = [ranked[0]]

    log.info(f"Selected categories: {selected}")
    return selected, state
