"""
API_SCOUT category handler.
Finds new free image generation APIs and proposes _generate_via_X() additions.
"""

from improvement.researcher import research_category
from improvement.proposer import generate_proposal


def run() -> dict | None:
    """Research free image APIs and propose a new generator function."""
    research = research_category("API_SCOUT")
    return generate_proposal("API_SCOUT", research)
