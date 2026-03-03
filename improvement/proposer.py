"""
Proposer — Generates improvement proposals via Ollama.
Reads current source code sections + research text, returns structured JSON proposals.
"""

import json
import logging
import re
from pathlib import Path

from improvement.ollama_agent import OllamaAgent

log = logging.getLogger("improvement.proposer")

BOT_DIR = Path(__file__).parent.parent


def _read_source(rel_path: str, max_chars: int = 6000) -> str:
    p = BOT_DIR / rel_path
    if p.exists():
        return p.read_text(errors="ignore")[:max_chars]
    return f"[File not found: {rel_path}]"


class ProposerAgent(OllamaAgent):
    name = "ProposerAgent"
    temperature = 0.5
    system_prompt = (
        "You are an expert Python developer improving an Instagram art bot. "
        "You generate precise, minimal code improvements based on research. "
        "Always return valid JSON exactly as specified — no markdown, no prose, just JSON."
    )


_PROPOSER = ProposerAgent()


def _extract_json(raw: str) -> dict | None:
    """Try to extract a JSON object from raw LLM output."""
    raw = raw.strip()
    # Remove markdown code fences
    raw = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.MULTILINE)
    raw = re.sub(r'```\s*$', '', raw, flags=re.MULTILINE)
    try:
        return json.loads(raw)
    except Exception:
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except Exception:
                pass
    return None


def propose_prompt_expand(research: str) -> dict | None:
    source = _read_source("prompt_agent.py", max_chars=3000)

    # Extract a sample of existing subjects to give the model context
    existing_sample = []
    for line in source.splitlines():
        if line.strip().startswith('"') and len(existing_sample) < 15:
            existing_sample.append(line.strip().strip('",'))

    prompt = (
        f"Research findings:\n{research[:2000]}\n\n"
        f"Sample of existing subjects/entries in prompt_agent.py:\n"
        + "\n".join(existing_sample[:15]) + "\n\n"
        "Generate 6 new entries for each of these lists: subjects (pick one category), "
        "environments, moods. Each entry must be stylistically distinct from the existing ones.\n\n"
        "Return JSON:\n"
        '{"description": "...", "complexity": "LOW", '
        '"files": ["prompt_agent.py"], '
        '"changes": ['
        '  {"list_name": "ARCHITECTURAL", "new_entries": ["entry1", "entry2", ...]},'
        '  {"list_name": "ALL_ENVIRONMENTS", "new_entries": ["entry1", ...]},'
        '  {"list_name": "ALL_MOODS", "new_entries": ["entry1", ...]}'
        ']}'
    )
    raw = _PROPOSER.call(prompt)
    result = _extract_json(raw)
    if result:
        result.setdefault("category", "PROMPT_EXPAND")
        result.setdefault("complexity", "LOW")
    return result


def propose_api_scout(research: str) -> dict | None:
    source = _read_source("art_bot.py", max_chars=3000)

    prompt = (
        f"Research findings about free image generation APIs:\n{research[:2000]}\n\n"
        f"Current art_bot.py (first 3000 chars):\n{source}\n\n"
        "Identify ONE free image generation API that:\n"
        "1. Has a working public endpoint\n"
        "2. Requires no API key or has a free tier\n"
        "3. Returns a base64-encoded image or image URL\n\n"
        "Return JSON describing a new _generate_via_X() function to add to art_bot.py:\n"
        '{"description": "...", "complexity": "MEDIUM", "files": ["art_bot.py"], '
        '"api_name": "...", "api_base_url": "https://...", '
        '"changes": [{"action": "add_function", "function_name": "_generate_via_X", '
        '"code": "def _generate_via_X(prompt):\\n    ..."}]}'
    )
    raw = _PROPOSER.call(prompt)
    result = _extract_json(raw)
    if result:
        result.setdefault("category", "API_SCOUT")
        result.setdefault("complexity", "MEDIUM")
    return result


def propose_engagement_tune(research: str) -> dict | None:
    ig_source = _read_source("instagram_bot.py", max_chars=3000)

    prompt = (
        f"Research findings about Instagram engagement:\n{research[:2000]}\n\n"
        f"Current instagram_bot.py (first 3000 chars):\n{ig_source}\n\n"
        "Propose improvements to:\n"
        "1. Add new entries to HASHTAG_MAP for underrepresented art styles\n"
        "2. Add new comment/reply strings to engagement pools (if engagement_bot.py has them)\n\n"
        "Return JSON:\n"
        '{"description": "...", "complexity": "LOW", "files": ["instagram_bot.py"], '
        '"changes": ['
        '  {"action": "add_hashtag_entries", '
        '   "entries": {"new_style_key": ["#tag1", "#tag2", "#tag3"]}},'
        '  {"action": "add_comment_entries", "file": "engagement_bot.py", '
        '   "pool_name": "GENERIC_COMMENTS", "new_entries": ["comment1", "comment2"]}'
        ']}'
    )
    raw = _PROPOSER.call(prompt)
    result = _extract_json(raw)
    if result:
        result.setdefault("category", "ENGAGEMENT_TUNE")
        result.setdefault("complexity", "LOW")
    return result


def propose_bug_fix(research: str, error_log: str) -> dict | None:
    if not error_log.strip():
        log.info("No errors found — skipping BUG_FIX proposal")
        return None

    prompt = (
        f"Error log (recent ERROR lines):\n{error_log[:1500]}\n\n"
        f"Research about fixing similar errors:\n{research[:1000]}\n\n"
        "Identify the most critical error. Propose a minimal fix (≤ 30 lines changed).\n"
        "Return JSON:\n"
        '{"description": "...", "complexity": "LOW", "files": ["<filename>"], '
        '"changes": [{"action": "replace_snippet", "file": "<filename>", '
        '"old_snippet": "exact existing code", "new_snippet": "fixed code", '
        '"explanation": "..."}]}'
        "\nIf no safe fix is possible, return null."
    )
    raw = _PROPOSER.call(prompt)
    if raw.strip().lower() == "null":
        return None
    result = _extract_json(raw)
    if result:
        result.setdefault("category", "BUG_FIX")
        result.setdefault("complexity", "LOW")
    return result


def propose_feature(research: str) -> dict | None:
    prompt = (
        f"Research about Instagram features for art accounts:\n{research[:2000]}\n\n"
        "Propose ONE new feature (stories, reels, carousels, etc.) for the art bot.\n"
        "This is for MANUAL REVIEW only — describe the approach, not code.\n\n"
        "Return JSON:\n"
        '{"description": "...", "complexity": "HIGH", "files": [], '
        '"feature_name": "...", "approach": "...", "manual_review_required": true}'
    )
    raw = _PROPOSER.call(prompt)
    result = _extract_json(raw)
    if result:
        result.setdefault("category", "FEATURE_PROPOSE")
        result["complexity"] = "HIGH"  # always HIGH for features
        result["manual_review_required"] = True
    return result


def generate_proposal(category: str, research: str, error_log: str = "") -> dict | None:
    """Route to the correct proposal generator by category."""
    log.info(f"Generating proposal for {category}")
    try:
        if category == "PROMPT_EXPAND":
            return propose_prompt_expand(research)
        elif category == "API_SCOUT":
            return propose_api_scout(research)
        elif category == "ENGAGEMENT_TUNE":
            return propose_engagement_tune(research)
        elif category == "BUG_FIX":
            return propose_bug_fix(research, error_log)
        elif category == "FEATURE_PROPOSE":
            return propose_feature(research)
    except Exception as e:
        log.error(f"Proposal generation failed for {category}: {e}")
    return None
