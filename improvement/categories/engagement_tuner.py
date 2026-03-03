"""
ENGAGEMENT_TUNE category handler.
Updates hashtag map, comment pools, and daily limits.
"""

from improvement.researcher import research_category
from improvement.proposer import generate_proposal


def run() -> dict | None:
    """Research engagement strategies and propose hashtag/comment improvements."""
    research = research_category("ENGAGEMENT_TUNE")
    return generate_proposal("ENGAGEMENT_TUNE", research)
