"""
FEATURE_PROPOSE category handler.
Researches Instagram features (stories, reels, carousels) and generates proposals
for MANUAL REVIEW ONLY — never auto-deployed.
"""

from improvement.researcher import research_category
from improvement.proposer import generate_proposal


def run() -> dict | None:
    """Research Instagram features and generate a manual-review proposal."""
    research = research_category("FEATURE_PROPOSE")
    proposal = generate_proposal("FEATURE_PROPOSE", research)
    if proposal:
        proposal["complexity"] = "HIGH"
        proposal["manual_review_required"] = True
    return proposal
