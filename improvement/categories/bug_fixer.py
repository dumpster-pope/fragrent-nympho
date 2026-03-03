"""
BUG_FIX category handler.
Parses logs/ for ERROR patterns and proposes targeted code patches.
Change limit: ≤ 30 lines.
"""

from pathlib import Path

from improvement.researcher import research_category
from improvement.proposer import generate_proposal
from improvement.analyzer import _read_recent_errors


def run() -> dict | None:
    """Read error logs and propose a minimal bug fix."""
    error_log = _read_recent_errors()
    if not error_log.strip():
        return None
    research = research_category("BUG_FIX")
    return generate_proposal("BUG_FIX", research, error_log)
