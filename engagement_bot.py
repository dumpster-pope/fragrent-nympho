"""
Instagram Engagement Bot

Performs 5–10 targeted engagement actions (likes, comments, follows, follow-backs)
after each image post to organically drive reach and follower growth.

Actions per session (probabilistic, respects daily limits):
  • 2–3 likes on posts from our home feed (engages existing followers)
  • 2–4 likes on posts under the post's own hashtags (attracts relevant new viewers)
  • 1–2 comments on hashtag posts (hashtag-aware text pool)
  • 1–2 follows of accounts posting quality content under our hashtags
  • 0–2 follow-backs for accounts that recently followed us

Daily hard limits (conservative — well within Instagram's safe thresholds):
  Likes: 80  |  Comments: 20  |  Follows: 15

Usage:
  Called automatically from instagram_bot.py after a successful post.
  Can also be invoked standalone: python engagement_bot.py [caption_text]
"""

import json
import logging
import random
import re
import time
from datetime import datetime
from pathlib import Path

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

# ── Paths ──────────────────────────────────────────────────────────────────────

BOT_DIR       = Path(__file__).parent
COUNTS_FILE   = BOT_DIR / "engagement_counts.json"
INSTAGRAM_URL = "https://www.instagram.com/"

# ── Daily limits ──────────────────────────────────────────────────────────────

DAILY_LIKE_LIMIT    = 80
DAILY_COMMENT_LIMIT = 20
DAILY_FOLLOW_LIMIT  = 15

# ── Logging ────────────────────────────────────────────────────────────────────

log = logging.getLogger("engagement_bot")

# ── Hashtag → comment category map ────────────────────────────────────────────

_HASHTAG_CATEGORY: dict[str, str] = {
    # Nature / landscape
    "natureart": "nature",      "landscapepainting": "nature",
    "forestpainting": "nature", "naturephotography": "nature",
    "landscapeart": "nature",   "oceansart": "nature",
    "mountainpainting": "nature","waterfallpainting": "nature",
    "gardenart": "nature",      "botanicalart": "nature",
    "scenery": "nature",        "pleinair": "nature",
    # Abstract / digital
    "abstractart": "abstract",  "digitalart": "abstract",
    "abstractpainting": "abstract","generativeart": "abstract",
    "abstractexpressionism": "abstract","conceptdesign": "abstract",
    "abstractartist": "abstract",
    # Portrait / figure
    "portraitpainting": "portrait","portraiture": "portrait",
    "figurativeart": "portrait", "portraitart": "portrait",
    "figurativepainting": "portrait",
    # Surreal / fantasy / concept
    "surrealism": "surreal",    "surrealart": "surreal",
    "fantasyart": "surreal",    "conceptart": "surreal",
    "scifiart": "surreal",      "imaginaryworlds": "surreal",
    "sciencefictionart": "surreal","darkart": "surreal",
    "fantasypainting": "surreal",
}

# ── Comment pools ─────────────────────────────────────────────────────────────

COMMENT_POOLS: dict[str, list[str]] = {
    "nature": [
        "The atmosphere here is breathtaking",
        "Incredible sense of place in this",
        "The light is handled so beautifully",
        "Such a peaceful and immersive scene",
        "The mood in this is absolutely perfect",
        "Love how transportive this feels",
        "The detail throughout is remarkable",
        "This really takes you somewhere else entirely",
    ],
    "abstract": [
        "The composition here is so striking",
        "Love the energy and movement in this",
        "The colour balance is just perfect",
        "Such a dynamic and captivating piece",
        "This pulls you in immediately",
        "The rhythm and flow here is incredible",
        "Love how bold and intentional this is",
        "Mesmerising — the depth is remarkable",
    ],
    "portrait": [
        "The emotion captured here is extraordinary",
        "Incredible depth and feeling in this",
        "The lighting is beautifully handled",
        "Such powerful and expressive work",
        "The character and presence here is incredible",
        "Truly captivating — beautiful work",
        "Love the atmosphere and mood here",
        "The way you've captured this is stunning",
    ],
    "surreal": [
        "This takes the imagination somewhere incredible",
        "The world-building here is stunning",
        "So immersive — the concept is brilliant",
        "The atmosphere and detail here is extraordinary",
        "This pulls you into another world entirely",
        "Love the story this tells",
        "The imagination and craft behind this is incredible",
        "Such a beautifully realised vision",
    ],
    "default": [
        "This is absolutely stunning work",
        "The detail and atmosphere here is incredible",
        "Love the mood and feeling in this one",
        "Beautiful — the composition is just right",
        "The craft and vision here is undeniable",
        "Such beautiful and evocative work",
        "Love the feeling this creates",
        "The skill here is really remarkable",
        "Truly beautiful — this really stands out",
        "So much depth here, incredible work",
        "The atmosphere in this is something else",
        "Love the palette and light here",
    ],
}

# ── Daily counts I/O ──────────────────────────────────────────────────────────

def _load_daily_counts() -> dict:
    today = datetime.now().strftime("%Y-%m-%d")
    if COUNTS_FILE.exists():
        try:
            with open(COUNTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("date") == today:
                return data
        except Exception:
            pass
    return {"date": today, "likes": 0, "comments": 0, "follows": 0, "follow_backs": 0}


def _save_daily_counts(counts: dict) -> None:
    with open(COUNTS_FILE, "w", encoding="utf-8") as f:
        json.dump(counts, f, indent=2)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _pause(min_s: float = 2.0, max_s: float = 5.0) -> None:
    """Random human-paced pause."""
    time.sleep(random.uniform(min_s, max_s))


def _pick_comment(hashtag: str) -> str:
    """Pick a comment text appropriate for the given hashtag."""
    category = _HASHTAG_CATEGORY.get(hashtag.lower(), "default")
    return random.choice(COMMENT_POOLS[category])


def _pick_engagement_hashtags(all_hashtags: list[str], n: int = 3) -> list[str]:
    """
    Pick the best hashtags to engage with from the post's hashtag list.
    Prefers specific mid-tier art tags over generic/mega ones.
    """
    SKIP_GENERIC = {
        "art", "artist", "artwork", "painting", "illustration",
        "drawing", "creative", "design", "photography", "nature",
        "instaart", "artoftheday", "artistsoninstagram", "artlovers",
        "fineart", "visualart", "contemporaryart", "artgallery",
        "artstagram", "artcollective", "artgram",
    }
    # Prefer specific tags (longer, more targeted)
    specific   = [h for h in all_hashtags if h.lower() not in SKIP_GENERIC and len(h) > 6]
    fallback   = [h for h in all_hashtags if h.lower() not in SKIP_GENERIC]
    candidates = specific if specific else fallback
    if not candidates:
        candidates = ["digitalart", "surrealism", "conceptart"]
    return random.sample(candidates, min(n, len(candidates)))


def _is_logged_in(driver) -> bool:
    """Quick check: are we logged in to Instagram?"""
    try:
        url = driver.current_url
        if "/accounts/login" in url or "/login" in url:
            return False
        # Presence of the home feed nav icon = logged in
        result = driver.execute_script("""
            return !!(
                document.querySelector("nav") ||
                document.querySelector("[aria-label='Home']") ||
                document.querySelector("svg[aria-label='Home']")
            );
        """)
        return bool(result)
    except Exception:
        return False


# ── Core per-post actions ─────────────────────────────────────────────────────

def _like_current_post(driver) -> bool:
    """Like the currently open post. Returns True on success."""
    try:
        # JS scan: find a button/element with aria-label exactly "Like" (not "Unlike")
        clicked = driver.execute_script("""
            // Check <button aria-label="Like">
            var byBtn = document.querySelector('button[aria-label="Like"]');
            if (byBtn) { byBtn.click(); return true; }
            // Check parent of <svg aria-label="Like">
            var svgs = document.querySelectorAll('svg[aria-label="Like"]');
            for (var i = 0; i < svgs.length; i++) {
                var btn = svgs[i].closest('button') || svgs[i].parentElement;
                if (btn) { btn.click(); return true; }
            }
            return false;
        """)
        if clicked:
            log.info("[engagement] Liked post")
            _pause(1.5, 3.0)
            return True
    except Exception as exc:
        log.debug(f"[engagement] Like failed: {exc}")
    return False


def _comment_current_post(driver, comment_text: str) -> bool:
    """Leave a comment on the currently open post. Returns True on success."""
    try:
        # First try to find a visible comment textarea
        comment_box = None
        for sel in [
            "textarea[placeholder*='Add a comment' i]",
            "textarea[placeholder*='comment' i]",
            "form textarea",
        ]:
            els = driver.find_elements(By.CSS_SELECTOR, sel)
            if els:
                comment_box = els[0]
                break

        # If not found, click the comment icon to open the input
        if not comment_box:
            icon_clicked = driver.execute_script("""
                var svgs = document.querySelectorAll('svg[aria-label="Comment"]');
                for (var i = 0; i < svgs.length; i++) {
                    var btn = svgs[i].closest('button') || svgs[i].parentElement;
                    if (btn) { btn.click(); return true; }
                }
                return false;
            """)
            if icon_clicked:
                _pause(1.0, 2.0)
                for sel in ["textarea[placeholder*='Add a comment' i]", "form textarea", "textarea"]:
                    els = driver.find_elements(By.CSS_SELECTOR, sel)
                    if els:
                        comment_box = els[0]
                        break

        if not comment_box:
            return False

        comment_box.click()
        _pause(0.5, 1.2)
        comment_box.send_keys(comment_text)
        _pause(0.8, 1.8)
        comment_box.send_keys(Keys.RETURN)
        log.info(f"[engagement] Commented: {comment_text}")
        _pause(2.0, 4.0)
        return True

    except Exception as exc:
        log.debug(f"[engagement] Comment failed: {exc}")
    return False


def _follow_current_author(driver) -> bool:
    """Follow the author of the currently open post. Returns True on success."""
    try:
        clicked = driver.execute_script("""
            var btns = document.querySelectorAll('button');
            for (var i = 0; i < btns.length; i++) {
                var t = (btns[i].textContent || '').trim().toLowerCase();
                if (t === 'follow') { btns[i].click(); return true; }
            }
            return false;
        """)
        if clicked:
            log.info("[engagement] Followed post author")
            _pause(2.0, 4.0)
            return True
    except Exception as exc:
        log.debug(f"[engagement] Follow failed: {exc}")
    return False


# ── Bulk action helpers ───────────────────────────────────────────────────────

def _get_post_links_from_hashtag(driver, hashtag: str, max_posts: int = 12) -> list[str]:
    """Navigate to a hashtag explore page and return post URLs (skipping the top 2)."""
    try:
        driver.get(f"https://www.instagram.com/explore/tags/{hashtag}/")
        _pause(4.0, 6.0)
        links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/p/']")
        hrefs: list[str] = []
        for link in links:
            href = link.get_attribute("href")
            if href and "/p/" in href:
                clean = href.split("?")[0]
                if clean not in hrefs:
                    hrefs.append(clean)
            if len(hrefs) >= max_posts + 3:
                break
        # Skip first 2 — too prominent, too much competition
        return hrefs[2: max_posts + 2]
    except Exception as exc:
        log.debug(f"[engagement] Hashtag page #{hashtag} failed: {exc}")
    return []


def _like_feed_posts(driver, n: int, counts: dict) -> int:
    """Like up to N posts from our home feed. Returns actual count liked."""
    liked = 0
    try:
        driver.get(INSTAGRAM_URL)
        _pause(3.0, 5.0)

        # Collect unique post URLs from the feed
        links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/p/']")
        urls: list[str] = []
        for link in links[:30]:
            href = link.get_attribute("href")
            if href and "/p/" in href:
                clean = href.split("?")[0]
                if clean not in urls:
                    urls.append(clean)

        targets = random.sample(urls, min(n, len(urls)))
        for url in targets:
            if counts["likes"] >= DAILY_LIKE_LIMIT:
                break
            driver.get(url)
            _pause(2.5, 4.5)
            if _like_current_post(driver):
                counts["likes"] += 1
                liked += 1
            _pause(2.0, 5.0)

    except Exception as exc:
        log.debug(f"[engagement] Feed likes failed: {exc}")
    return liked


def _engage_hashtag(
    driver,
    hashtag: str,
    counts: dict,
    do_comment: bool = True,
    do_follow: bool = False,
) -> None:
    """
    Engage with posts under a hashtag: like, optionally comment + follow.
    Visits 2–3 posts per hashtag with natural pacing.
    """
    post_urls = _get_post_links_from_hashtag(driver, hashtag, max_posts=8)
    if not post_urls:
        log.debug(f"[engagement] No posts found for #{hashtag}")
        return

    # Visit a random subset — don't always engage in the same order
    targets = random.sample(post_urls, min(3, len(post_urls)))

    for url in targets:
        if counts["likes"] >= DAILY_LIKE_LIMIT:
            break

        driver.get(url)
        _pause(3.0, 5.5)

        # Like
        if _like_current_post(driver):
            counts["likes"] += 1

        # Comment (~50% chance per post, skip if over limit)
        if (do_comment
                and counts["comments"] < DAILY_COMMENT_LIMIT
                and random.random() < 0.5):
            comment = _pick_comment(hashtag)
            if _comment_current_post(driver, comment):
                counts["comments"] += 1

        # Follow (~30% chance, skip if over limit)
        if (do_follow
                and counts["follows"] < DAILY_FOLLOW_LIMIT
                and random.random() < 0.35):
            if _follow_current_author(driver):
                counts["follows"] += 1

        _pause(4.0, 9.0)


def _follow_back_new_followers(driver, username: str, n: int, counts: dict) -> int:
    """
    Visit our follower list and follow back accounts we're not following yet.
    Returns number of accounts followed back.
    """
    followed_back = 0
    try:
        driver.get(f"https://www.instagram.com/{username}/followers/")
        _pause(4.0, 6.0)

        # Scroll slightly to load more entries
        driver.execute_script("window.scrollBy(0, 400);")
        _pause(1.5, 2.5)

        # Find all "Follow" buttons in the follower list (not "Following")
        follow_btns = driver.execute_script("""
            var btns = document.querySelectorAll('button');
            var result = [];
            for (var i = 0; i < btns.length; i++) {
                var t = (btns[i].textContent || '').trim().toLowerCase();
                if (t === 'follow') result.push(btns[i]);
                if (result.length >= 6) break;
            }
            return result;
        """)

        if not follow_btns:
            log.debug("[engagement] No un-followed followers found")
            return 0

        for btn in follow_btns[:n]:
            if counts["follows"] >= DAILY_FOLLOW_LIMIT:
                break
            try:
                driver.execute_script("arguments[0].click();", btn)
                _pause(2.0, 4.0)
                counts["follows"] += 1
                counts["follow_backs"] = counts.get("follow_backs", 0) + 1
                followed_back += 1
                log.info("[engagement] Followed back a follower")
            except Exception:
                pass

    except Exception as exc:
        log.debug(f"[engagement] Follow-back failed: {exc}")

    return followed_back


# ── Main session orchestrator ─────────────────────────────────────────────────

def run_post_engagement(cfg: dict, caption: str) -> None:
    """
    Run a focused engagement burst (5–10 actions) after a successful post.

    Strategy:
      Block 1 — Like 2–3 posts from our home feed (keeps existing followers warm)
      Block 2 — Engage with 2–3 hashtag pages from the post (attracts new followers)
                  First hashtag: like + comment
                  Second hashtag: like + comment + maybe follow
                  Third hashtag: like only (keep session light)
      Block 3 — Follow back 1–2 accounts that followed us (if username set)
    """
    from instagram_bot import make_driver  # shared Chrome profile helpers

    log.info("[engagement] Starting post-engagement session…")
    counts = _load_daily_counts()
    log.info(
        f"[engagement] Daily totals so far — "
        f"likes={counts['likes']}, comments={counts['comments']}, follows={counts['follows']}"
    )

    if counts["likes"] >= DAILY_LIKE_LIMIT and counts["comments"] >= DAILY_COMMENT_LIMIT:
        log.info("[engagement] Daily limits already reached — skipping session")
        return

    # Extract hashtags from the caption string
    all_hashtags = re.findall(r"#(\w+)", caption)
    target_hashtags = _pick_engagement_hashtags(all_hashtags, n=3)
    log.info(f"[engagement] Target hashtags: #{', #'.join(target_hashtags)}")

    username = cfg.get("instagram_username", "").strip()

    driver = make_driver(cfg)
    try:
        driver.get(INSTAGRAM_URL)
        _pause(3.0, 5.0)

        if not _is_logged_in(driver):
            log.warning("[engagement] Not logged in to Instagram — skipping session")
            return

        # ── Block 1: Like posts from home feed (followers' posts) ─────────────
        n_feed_likes = random.randint(2, 3)
        liked = _like_feed_posts(driver, n=n_feed_likes, counts=counts)
        log.info(f"[engagement] Feed: liked {liked} posts")
        _pause(4.0, 7.0)

        # ── Block 2: Engage with hashtag pages ────────────────────────────────
        if target_hashtags and counts["likes"] < DAILY_LIKE_LIMIT:
            log.info(f"[engagement] Engaging with #{target_hashtags[0]} (like + comment)")
            _engage_hashtag(
                driver, target_hashtags[0], counts,
                do_comment=True,
                do_follow=False,
            )
            _save_daily_counts(counts)   # save incrementally
            _pause(5.0, 9.0)

        if len(target_hashtags) > 1 and counts["likes"] < DAILY_LIKE_LIMIT:
            log.info(f"[engagement] Engaging with #{target_hashtags[1]} (like + comment + follow)")
            _engage_hashtag(
                driver, target_hashtags[1], counts,
                do_comment=(counts["comments"] < DAILY_COMMENT_LIMIT),
                do_follow=(counts["follows"] < DAILY_FOLLOW_LIMIT),
            )
            _save_daily_counts(counts)
            _pause(5.0, 9.0)

        if len(target_hashtags) > 2 and counts["likes"] < DAILY_LIKE_LIMIT:
            log.info(f"[engagement] Engaging with #{target_hashtags[2]} (like only)")
            _engage_hashtag(
                driver, target_hashtags[2], counts,
                do_comment=False,
                do_follow=False,
            )
            _pause(3.0, 6.0)

        # ── Block 3: Follow back new followers (only if username is configured) ─
        if username and counts["follows"] < DAILY_FOLLOW_LIMIT:
            log.info("[engagement] Checking for new followers to follow back…")
            fb = _follow_back_new_followers(driver, username, n=2, counts=counts)
            if fb:
                log.info(f"[engagement] Followed back {fb} new follower(s)")

        _save_daily_counts(counts)
        log.info(
            f"[engagement] Session complete — "
            f"likes={counts['likes']}, comments={counts['comments']}, follows={counts['follows']}"
        )

    except Exception as exc:
        log.error(f"[engagement] Session error: {exc}", exc_info=True)
    finally:
        _save_daily_counts(counts)
        try:
            driver.quit()
        except Exception:
            pass


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

    # Allow passing a caption string as argument for testing
    caption = sys.argv[1] if len(sys.argv) > 1 else (
        "#digitalart #surrealism #conceptart #fantasyart #artoftheday "
        "#artistsoninstagram #contemporaryart #landscapepainting"
    )
    run_post_engagement(cfg, caption)
