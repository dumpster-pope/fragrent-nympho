"""
Engagement Learning System for AI Art Bot

Tracks Instagram engagement (likes + comments) per post and biases
future prompt generation toward higher-performing components.

Data file: engagement_data.json  (same directory as this script)

Usage:
  python engagement_learner.py        — scrape all tracked posts, print report
  python engagement_learner.py report — just print the report (no scraping)
"""

import json
import logging
import re
import time
from datetime import datetime, timedelta
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────

BOT_DIR         = Path(__file__).parent
ENGAGEMENT_FILE = BOT_DIR / "engagement_data.json"
TRACKER_FILE    = BOT_DIR / "posted_tracker.json"

# ── Tuning constants ───────────────────────────────────────────────────────────

MIN_POSTS_FOR_LEARNING = 5    # below this, return uniform weights
RECENCY_WINDOW         = 10   # last N posts get full weight
RECENCY_DECAY          = 0.5  # older posts get 50% weight
WEIGHT_FLOOR           = 0.4  # worst-performing component
WEIGHT_CEILING         = 1.8  # best-performing component
RESCRAPE_HOURS         = 6    # skip posts scraped less than N hours ago

# ── Logging ────────────────────────────────────────────────────────────────────

log = logging.getLogger("engagement_learner")


# ── Data I/O ──────────────────────────────────────────────────────────────────

def load_engagement_data() -> dict:
    """Load engagement_data.json, returning empty structure on missing/corrupt file."""
    if ENGAGEMENT_FILE.exists():
        try:
            with open(ENGAGEMENT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            log.warning(f"Could not load engagement data: {exc}")
    return {"posts": {}, "last_updated": None}


def save_engagement_data(data: dict) -> None:
    """Persist engagement data and stamp last_updated."""
    data["last_updated"] = datetime.now().isoformat()
    with open(ENGAGEMENT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# ── Count parsing ─────────────────────────────────────────────────────────────

def _parse_count(text: str) -> int:
    """Parse Instagram count strings like '1,234', '42K', '1.2M' into ints."""
    if not text:
        return 0
    text = text.strip().replace(",", "")
    try:
        if text.upper().endswith("K"):
            return int(float(text[:-1]) * 1_000)
        elif text.upper().endswith("M"):
            return int(float(text[:-1]) * 1_000_000)
        else:
            return int(float(text))
    except (ValueError, TypeError):
        return 0


# ── Engagement scraping ───────────────────────────────────────────────────────

def scrape_post_engagement(driver, post_url: str) -> tuple[int, int]:
    """
    Scrape likes and comments for an Instagram post.
    Uses JS innerText scan — resilient to Instagram's frequent DOM class-name changes.
    Returns (likes, comments).
    """
    try:
        driver.get(post_url)
        time.sleep(5)  # let React hydrate

        result = driver.execute_script(r"""
            var text = document.body.innerText;
            var likes    = text.match(/([\d,\.]+[KkMm]?)\s+like/i);
            var comments = text.match(/([\d,\.]+[KkMm]?)\s+comment/i);
            return {
                likes:    likes    ? likes[1]    : null,
                comments: comments ? comments[1] : null
            };
        """)

        likes    = _parse_count(result.get("likes")    or "0")
        comments = _parse_count(result.get("comments") or "0")
        log.info(f"[engagement] Scraped {post_url}: likes={likes}, comments={comments}")
        return likes, comments

    except Exception as exc:
        log.warning(f"[engagement] Failed to scrape {post_url}: {exc}")
        return 0, 0


# ── Full engagement update ────────────────────────────────────────────────────

def run_engagement_update(cfg: dict) -> None:
    """
    Open Chrome with the bot profile, visit all tracked post URLs,
    scrape likes + comments for posts older than RESCRAPE_HOURS,
    merge component data from sidecar files, and save to engagement_data.json.
    """
    # Lazy imports to avoid circular dependency at module level
    from instagram_bot import make_driver  # shares same Chrome profile helpers
    from art_bot import SAVE_DIR

    data = load_engagement_data()

    # Load posted_tracker.json to get post URLs
    tracker_data: dict = {}
    if TRACKER_FILE.exists():
        try:
            with open(TRACKER_FILE, "r", encoding="utf-8") as f:
                tracker_data = json.load(f)
        except Exception:
            pass

    post_urls: dict[str, str] = tracker_data.get("post_urls", {})
    if not post_urls:
        log.info("[engagement] No post URLs tracked yet. Post some images first.")
        return

    # Load component data from sidecar .json files
    sidecars: dict[str, dict] = {}
    for img_name in post_urls:
        meta_path = SAVE_DIR / img_name.replace(".png", "_meta.json")
        if meta_path.exists():
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                sidecars[img_name] = meta.get("components", {})
            except Exception:
                pass

    # Decide which posts need (re-)scraping
    now    = datetime.now()
    cutoff = now - timedelta(hours=RESCRAPE_HOURS)

    urls_to_scrape: list[tuple[str, str]] = []
    for img_name, url in post_urls.items():
        if not url:
            continue
        existing   = data["posts"].get(img_name, {})
        scraped_at = existing.get("scraped_at")
        if scraped_at:
            try:
                scraped_dt = datetime.fromisoformat(scraped_at)
                if scraped_dt > cutoff:
                    log.info(f"[engagement] Skipping {img_name} (scraped {scraped_at})")
                    # Still merge components if they were missing
                    if img_name in sidecars and not existing.get("components"):
                        data["posts"][img_name]["components"] = sidecars[img_name]
                    continue
            except Exception:
                pass
        urls_to_scrape.append((img_name, url))

    if not urls_to_scrape:
        log.info("[engagement] All posts are up-to-date.")
        save_engagement_data(data)
        _print_top_posts(data)
        return

    log.info(f"[engagement] Scraping {len(urls_to_scrape)} posts…")
    driver = make_driver(cfg)
    try:
        for img_name, url in urls_to_scrape:
            likes, comments = scrape_post_engagement(driver, url)
            data["posts"][img_name] = {
                "post_url":   url,
                "likes":      likes,
                "comments":   comments,
                "scraped_at": datetime.now().isoformat(),
                "components": sidecars.get(img_name, {}),
            }
    finally:
        try:
            driver.quit()
        except Exception:
            pass

    save_engagement_data(data)
    log.info(f"[engagement] Updated {len(urls_to_scrape)} posts → {ENGAGEMENT_FILE}")
    _print_top_posts(data)


# ── Reporting ─────────────────────────────────────────────────────────────────

def _print_top_posts(data: dict) -> None:
    posts = data.get("posts", {})
    if not posts:
        print("[engagement] No posts tracked yet.")
        return

    scored = [
        (p.get("likes", 0) + 3 * p.get("comments", 0), name, p)
        for name, p in posts.items()
    ]
    scored.sort(reverse=True)

    print(f"\n{'='*60}")
    print(f"  Engagement Report — {len(scored)} posts tracked")
    print(f"{'='*60}")
    for score, name, info in scored[:10]:
        print(f"  {score:5d}  {name[:40]:<40}  "
              f"likes={info.get('likes',0)}, comments={info.get('comments',0)}")
    print(f"{'='*60}\n")


# ── Weight computation ────────────────────────────────────────────────────────

def compute_component_weights(
    data: dict,
    component_key: str,
    all_items: list,
) -> list[float]:
    """
    Compute a weight for each item in all_items based on engagement data.

    Weight formula:
      - raw engagement score:  likes + 3 × comments  (comments = higher intent)
      - recency:  last RECENCY_WINDOW posts count at full weight,
                  older posts at RECENCY_DECAY (0.5)
      - per-component score: average weighted engagement for all posts using it
      - normalise across known components: 0.0 (worst) → 1.0 (best)
      - final weight: WEIGHT_FLOOR + (WEIGHT_CEILING - WEIGHT_FLOOR) × normalised
      - items with no data: 1.0 (neutral, between floor and ceiling)
      - items with data:    0.4 (worst) … 1.8 (best)  — 4.5× spread, nothing eliminated

    Returns list[float] same length as all_items.
    """
    posts = data.get("posts", {})
    if len(posts) < MIN_POSTS_FOR_LEARNING:
        return [1.0] * len(all_items)

    # Sort chronologically by scraped_at to determine recency
    post_list = sorted(posts.items(), key=lambda kv: kv[1].get("scraped_at", ""))

    n            = len(post_list)
    recent_start = max(0, n - RECENCY_WINDOW)

    # Accumulate weighted engagement scores per component value
    component_scores: dict[str, list[float]] = {}
    for idx, (img_name, post_info) in enumerate(post_list):
        recency_weight = 1.0 if idx >= recent_start else RECENCY_DECAY
        raw_score      = post_info.get("likes", 0) + 3 * post_info.get("comments", 0)
        weighted_score = raw_score * recency_weight

        comp_value = post_info.get("components", {}).get(component_key)
        if comp_value is None:
            continue
        component_scores.setdefault(comp_value, []).append(weighted_score)

    if not component_scores:
        return [1.0] * len(all_items)

    # Average score per component value
    avg_scores: dict[str, float] = {
        v: sum(s) / len(s) for v, s in component_scores.items()
    }

    min_score   = min(avg_scores.values())
    max_score   = max(avg_scores.values())
    score_range = max_score - min_score

    weights: list[float] = []
    for item in all_items:
        if item not in avg_scores:
            weights.append(1.0)  # no data → neutral
        else:
            if score_range > 0:
                normalised = (avg_scores[item] - min_score) / score_range
            else:
                normalised = 0.5  # all items performed equally
            w = WEIGHT_FLOOR + (WEIGHT_CEILING - WEIGHT_FLOOR) * normalised
            weights.append(w)

    return weights


def get_all_weights(data: dict, lists: dict) -> dict:
    """
    Compute weights for all prompt component types at once.

    Args:
        data:  engagement_data dict from load_engagement_data()
        lists: mapping of component_key -> list[str]  (e.g. {"subject": SUBJECTS, ...})

    Returns:
        mapping of component_key -> list[float]
    """
    return {key: compute_component_weights(data, key, items) for key, items in lists.items()}


# ── CLI entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        handlers=[logging.StreamHandler()],
    )

    sys.path.insert(0, str(BOT_DIR))

    from art_bot import load_config

    cfg = load_config()

    if len(sys.argv) > 1 and sys.argv[1] == "report":
        # Just print report, no scraping
        data = load_engagement_data()
        n = len(data.get("posts", {}))
        if n < MIN_POSTS_FOR_LEARNING:
            print(f"[engagement] Only {n} posts tracked (need {MIN_POSTS_FOR_LEARNING} for learning).")
        _print_top_posts(data)
    else:
        run_engagement_update(cfg)
