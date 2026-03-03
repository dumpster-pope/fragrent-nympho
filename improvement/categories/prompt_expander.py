"""
PROMPT_EXPAND category handler.
Adds new subjects/styles/environments/moods to prompt_agent.py.
Additions only — removals require manual review.
"""

from improvement.researcher import research_category
from improvement.proposer import generate_proposal


def run() -> dict | None:
    """Research and propose prompt list expansions."""
    research = research_category("PROMPT_EXPAND")
    return generate_proposal("PROMPT_EXPAND", research)
