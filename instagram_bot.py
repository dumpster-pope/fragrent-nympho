"""
Instagram posting module for AI Art Bot.

Handles caption building, hashtag generation, image uploading,
and the posted-image tracker.
"""

import json
import logging
import random
import time
from datetime import datetime
from pathlib import Path

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# Shared helpers — art_bot never imports us at module level, so no circular import.
from art_bot import (
    BOT_DIR, SAVE_DIR, LOG_DIR,
    make_driver, slow_type, find_first, _shorten_descriptor, _screenshot,
)

INSTAGRAM_URL = "https://www.instagram.com/"
TRACKER_FILE  = BOT_DIR / "posted_tracker.json"

log = logging.getLogger("instagram_bot")

# ── Hashtag system ────────────────────────────────────────────────────────────

MAX_HASHTAGS = 28

MEGA_TAGS = [
    "#art", "#artist", "#artwork", "#painting", "#illustration",
    "#drawing", "#creative", "#design", "#photography", "#nature",
]

MID_TAGS = [
    "#digitalart", "#artoftheday", "#artistsoninstagram", "#contemporaryart",
    "#conceptart", "#visualart", "#artgallery", "#fineart", "#instaart",
    "#artstagram", "#artcollective", "#artlovers", "#surrealism",
    "#fantasyart", "#imaginaryworlds",
]

HASHTAG_MAP: dict[str, list[str]] = {
    # Medium / technique
    "watercolour":      ["#watercolour", "#watercolorpainting", "#watercolorart", "#watercolorillustration", "#aquarelle"],
    "watercolor":       ["#watercolor", "#watercolorpainting", "#watercolorart", "#watercolorillustration", "#aquarelle"],
    "oil paint":        ["#oilpainting", "#oiloncanvas", "#oilpaintings", "#classicpainting", "#oldmastersart"],
    "oil":              ["#oilpainting", "#oiloncanvas", "#oilpaintings"],
    "acrylic":          ["#acrylicpainting", "#acrylicart", "#acrylicartist"],
    "ink":              ["#inkdrawing", "#inkart", "#penandink", "#inkillustration"],
    "gouache":          ["#gouache", "#gouacheart", "#gouachepainting"],
    "charcoal":         ["#charcoaldrawing", "#charcoalart", "#charcoalsketch", "#blackandwhiteart"],
    "pastel":           ["#pastelart", "#pastelpainting", "#softpastel"],
    "etching":          ["#etching", "#printmaking", "#intaglio"],
    "linocut":          ["#linocut", "#printmaking", "#linocutprint", "#blockprint"],
    # Film / photography
    "film":             ["#filmphotography", "#analogphotography", "#filmisnotdead", "#shootfilm", "#35mmfilm"],
    "kodachrome":       ["#kodachrome", "#filmphotography", "#analogphotography", "#filmisnotdead"],
    "portra":           ["#kodakportra", "#filmphotography", "#35mm", "#filmisnotdead"],
    "tri-x":            ["#kodaktrix", "#blackandwhitefilm", "#filmisnotdead", "#35mmfilm"],
    "pinhole":          ["#pinholephotography", "#alternativeprocess", "#pinholefilm"],
    "hasselblad":       ["#hasselblad", "#mediumformat", "#filmphotography", "#120film"],
    "long exposure":    ["#longexposure", "#longexposurephotography", "#slowshutter"],
    "black and white":  ["#blackandwhitephotography", "#blackandwhite", "#bnwphotography", "#monochrome"],
    # Named artists / styles
    "ghibli":           ["#studioghibli", "#ghibliart", "#ghibliaesthetic", "#animeart", "#miyazaki"],
    "moebius":          ["#moebius", "#jeanmoebius", "#sciencefictionart", "#graphicnovel"],
    "giraud":           ["#moebius", "#jeanmoebius", "#sciencefictionart", "#graphicnovel"],
    "beksinski":        ["#beksinski", "#darkart", "#surrealpainting", "#darkfantasyart"],
    "mucha":            ["#mucha", "#alphonsmucha", "#artnouveau", "#jugendstil"],
    "dali":             ["#dali", "#salvadordali", "#surrealism", "#surrealart"],
    "hokusai":          ["#hokusai", "#ukiyoe", "#japanesewoodblock", "#japaneseart"],
    "klimt":            ["#klimt", "#artnouveau", "#gustavklimt", "#jugendstil"],
    "turner":           ["#jmwturner", "#romanticism", "#landscapepainting", "#atmosphericpainting"],
    "monet":            ["#monet", "#impressionism", "#claudemonet", "#impressionistpainting"],
    "durer":            ["#albrecht", "#durer", "#crosshatching", "#engraving"],
    "wyeth":            ["#ncwyeth", "#illustrationart", "#adventureart"],
    "rackham":          ["#arthurrackham", "#watercolorillustration", "#fantasyillustration"],
    # Historical periods / movements
    "baroque":          ["#baroque", "#baroqueart", "#oldmastersart", "#chiaroscuro"],
    "impressionism":    ["#impressionism", "#impressionistpainting", "#pleinair"],
    "impressionist":    ["#impressionism", "#impressionistpainting", "#pleinair"],
    "art nouveau":      ["#artnouveau", "#jugendstil", "#decorativeart"],
    "art deco":         ["#artdeco", "#artdecodesign", "#vintageposter", "#geometricart"],
    "romanticism":      ["#romanticism", "#romanticpainting", "#19thcenturyart"],
    "symbolism":        ["#symbolism", "#symbolistart", "#mysticalart"],
    "gothic":           ["#gothicart", "#darkromanticism", "#gothicaesthetic"],
    "medieval":         ["#medievalart", "#medievalpainting", "#gothicart"],
    "illuminated":      ["#illuminatedmanuscript", "#medievalart", "#manuscriptart"],
    "renaissance":      ["#renaissanceart", "#renaissance", "#oldmastersart"],
    "constructivist":   ["#constructivism", "#sovietart", "#propagandaart"],
    "nihonga":          ["#nihonga", "#japaneseart", "#japanesepaintng"],
    "pre-raphaelite":   ["#preraphaelite", "#victorianaert", "#paintingdetail"],
    "risograph":        ["#risograph", "#risoprintmaking", "#risoprint"],
    "woodblock":        ["#woodblockprint", "#ukiyoe", "#japanesewoodblock", "#printmaking"],
    # Subject matter
    "portrait":         ["#portraitpainting", "#portraiture", "#figurativeart", "#portraitart"],
    "figure":           ["#figurativeart", "#figurativepainting", "#humanform"],
    "landscape":        ["#landscapepainting", "#landscapeart", "#scenery", "#pleinair"],
    "cityscape":        ["#cityscape", "#cityscapepainting", "#urbanart", "#architectureart"],
    "still life":       ["#stilllife", "#stilllifepainting", "#botanicalart"],
    "abstract":         ["#abstractart", "#abstractpainting", "#abstractexpressionism"],
    # Nature / environment
    "forest":           ["#forestpainting", "#woodlandart", "#enchantedforest", "#natureart"],
    "jungle":           ["#jungleart", "#tropicalart", "#rainforest", "#natureart"],
    "ocean":            ["#seascape", "#oceanart", "#marinepainting", "#seascapepainting"],
    "sea":              ["#seascape", "#oceanart", "#marinepainting"],
    "river":            ["#riverpainting", "#waterscape", "#natureart"],
    "waterfall":        ["#waterfallpainting", "#natureart", "#waterfallart"],
    "mountain":         ["#mountainpainting", "#mountainscape", "#alpineart"],
    "desert":           ["#desertart", "#desertlandscape", "#aridlandscape"],
    "cave":             ["#caveart", "#undergroundart"],
    "garden":           ["#gardenart", "#botanicalart", "#gardenpainting"],
    "flowers":          ["#floralart", "#botanicalillustration", "#botanicalart", "#flowerpainting"],
    "tree":             ["#treeart", "#treepainting", "#natureart"],
    "fog":              ["#atmosphericart", "#foggylandscape", "#moodyphotography"],
    "mist":             ["#atmosphericart", "#mistyphotography", "#moodylandscape"],
    "storm":            ["#stormpainting", "#dramaticskies", "#stormscape"],
    "snow":             ["#snowscene", "#winterlandscape", "#snowpainting"],
    "fire":             ["#fireart", "#flameart", "#lightandshadow"],
    "night":            ["#nightscene", "#nightphotography", "#nightscape", "#nocturnal"],
    "sunset":           ["#sunsetpainting", "#goldenhourst", "#sunsetart", "#twilight"],
    "aurora":           ["#auroraborialis", "#northernlights", "#aurorapainting"],
    # Architecture / place
    "cathedral":        ["#cathedralart", "#gothicarchitecture", "#sacredart"],
    "temple":           ["#templeart", "#sacredarchitecture", "#ancientart"],
    "castle":           ["#castleart", "#medievalcastle", "#fortressart"],
    "ruin":             ["#ruins", "#ruinsoftheworld", "#abandonedplaces"],
    "library":          ["#libraryart", "#bookart", "#bibliophile", "#literaryart"],
    "staircase":        ["#staircaseart", "#architecturepainting", "#perspectiveart"],
    "stained glass":    ["#stainedglass", "#stainedglassart", "#sacredart"],
    "lighthouse":       ["#lighthouseart", "#coastalart", "#marineart"],
    "greenhouse":       ["#botanicalgarden", "#plantart", "#horticulture"],
    "observatory":      ["#astronomyart", "#telescopeart", "#scifiart"],
    # Themes / mood
    "space":            ["#spaceart", "#cosmicart", "#astronomy", "#scifiart"],
    "cosmos":           ["#cosmicart", "#cosmos", "#universe", "#spaceart"],
    "galaxy":           ["#galaxyart", "#nebulaart", "#deepspace", "#spaceart"],
    "star":             ["#stargazing", "#nightsky", "#astrophotography", "#celestialart"],
    "moon":             ["#moonart", "#moonphotography", "#lunarart", "#celestialart"],
    "astronaut":        ["#astronautart", "#scifiart", "#spaceexploration"],
    "magic":            ["#magicart", "#mysticalart", "#enchanted", "#magicalrealism"],
    "light":            ["#chiaroscuro", "#lightandshadow", "#luminismart"],
    "shadow":           ["#chiaroscuro", "#lightandshadow", "#silhouetteart"],
    "ancient":          ["#ancientart", "#ancienthistory", "#historicalpainting"],
    # Japanese / Asian
    "japanese":         ["#japaneseart", "#japanesepainting", "#asianart", "#wabi_sabi"],
    "samurai":          ["#samuraiart", "#bushido", "#japaneseart", "#feudaljapan"],
    "ukiyo":            ["#ukiyoe", "#woodblockprint", "#japanesewoodblock"],
    "zen":              ["#zenart", "#zenpainting", "#japaneseart", "#wabi_sabi"],
    # Sci-fi / futurism
    "cyberpunk":        ["#cyberpunkart", "#cyberpunk", "#futuristicart", "#neonart"],
    "steampunk":        ["#steampunkart", "#steampunk", "#victorianfuturism"],
    "futurist":         ["#futurism", "#futuristicart", "#retrofuturism", "#scifiart"],
    "bioluminescent":   ["#bioluminescence", "#glowinglight", "#underwaterart"],
    "fireflies":        ["#fireflies", "#naturephotography", "#magicalnature"],
    "whale":            ["#whaleart", "#marineart", "#oceanpainting"],
    "phoenix":          ["#phoenixart", "#mythologicalart", "#epicart"],
    "dragon":           ["#dragonart", "#dragonpainting", "#mythologicalart"],
}


def generate_hashtags(prompt: str) -> str:
    """Build a tiered hashtag set from the prompt text."""
    prompt_lower = prompt.lower()

    niche: list[str] = []
    for keyword, tags in HASHTAG_MAP.items():
        if keyword in prompt_lower:
            for t in tags:
                if t not in niche:
                    niche.append(t)

    mega_sample = random.sample(MEGA_TAGS, min(3, len(MEGA_TAGS)))
    mid_pool    = [t for t in MID_TAGS if t not in mega_sample]
    mid_sample  = random.sample(mid_pool, min(6, len(mid_pool)))
    random.shuffle(niche)

    combined: list[str] = []
    seen:     set[str]  = set()
    for tag in mega_sample + mid_sample + niche:
        if tag not in seen:
            seen.add(tag)
            combined.append(tag)
        if len(combined) >= MAX_HASHTAGS:
            break

    return " ".join(combined)


# ── Caption builder ───────────────────────────────────────────────────────────

def build_caption(image_path: Path) -> str:
    """Build a human-readable caption from the image's _meta.json sidecar."""
    meta_path = image_path.with_name(image_path.stem + "_meta.json")
    if not meta_path.exists():
        prompt       = image_path.stem.replace("_", " ")
        generated_at = datetime.now()
        return (
            f"{generated_at.strftime('%B %#d, %Y')} at {generated_at.strftime('%#I:%M %p')}\n\n"
            f"{prompt}\n\n"
            f"{generate_hashtags(prompt)}"
        )

    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    generated_at = datetime.fromisoformat(meta.get("generated_at", datetime.now().isoformat()))
    date_str     = generated_at.strftime("%B %#d, %Y")
    time_str     = generated_at.strftime("%#I:%M %p")

    comps = meta.get("components", {})
    if comps:
        subject = comps.get("subject", "").strip().rstrip(".")
        env     = comps.get("environment", "").strip().rstrip(".")
        style   = comps.get("style", "").strip().rstrip(".")
        mood    = comps.get("mood", "").strip().rstrip(".")

        subject_line = (
            f"{subject.capitalize()}, {env}."
            if subject and env
            else f"{subject.capitalize()}." if subject
            else meta.get("prompt", "").split(".")[0].capitalize() + "."
        )

        style_short = _shorten_descriptor(style) if style else ""
        mood_short  = _shorten_descriptor(mood)  if mood  else ""
        art_note    = (
            f"{style_short} · {mood_short}" if style_short and mood_short
            else style_short or mood_short
        )

        hashtags = generate_hashtags(f"{subject} {env} {style} {mood}")

        lines = [f"{date_str} at {time_str}", "", subject_line]
        if art_note:
            lines.append(art_note)
        lines += ["", hashtags]
        return "\n".join(lines)

    prompt   = meta.get("prompt", image_path.stem)
    hashtags = generate_hashtags(prompt)
    return f"{date_str} at {time_str}\n\n{prompt}\n\n{hashtags}"


# ── Clipboard helper ──────────────────────────────────────────────────────────

def _set_clipboard(text: str) -> None:
    """Write text to the Windows clipboard via PowerShell."""
    import subprocess
    tmp = BOT_DIR / "_tmp_caption.txt"
    tmp.write_text(text, encoding="utf-8")
    try:
        subprocess.run(
            ["powershell", "-command",
             f'Get-Content -Path "{tmp}" -Raw -Encoding UTF8 | Set-Clipboard'],
            check=True, capture_output=True, timeout=10,
        )
    finally:
        try:
            tmp.unlink()
        except Exception:
            pass


def _clipboard_paste(driver, element, text: str) -> None:
    """Set clipboard to text, click element, then Ctrl+V."""
    _set_clipboard(text)
    element.click()
    time.sleep(0.5)
    element.send_keys(Keys.CONTROL, "a")
    time.sleep(0.2)
    element.send_keys(Keys.CONTROL, "v")
    time.sleep(0.5)


# ── Posted-image tracker ──────────────────────────────────────────────────────

def load_tracker() -> dict:
    if TRACKER_FILE.exists():
        try:
            with open(TRACKER_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"posted": [], "daily_counts": {}, "post_urls": {}}


def save_tracker(tracker: dict) -> None:
    with open(TRACKER_FILE, "w", encoding="utf-8") as f:
        json.dump(tracker, f, indent=2)


def daily_count(tracker: dict, date_str: str | None = None) -> int:
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")
    return tracker.get("daily_counts", {}).get(date_str, 0)


def mark_posted(tracker: dict, image_path: Path, post_url: str | None = None) -> None:
    date_str = datetime.now().strftime("%Y-%m-%d")
    tracker.setdefault("posted", []).append(image_path.name)
    tracker.setdefault("daily_counts", {})[date_str] = (
        tracker["daily_counts"].get(date_str, 0) + 1
    )
    if post_url:
        tracker.setdefault("post_urls", {})[image_path.name] = post_url


def pick_unposted_image(tracker: dict) -> Path | None:
    """Return the oldest unposted PNG from SAVE_DIR, or None."""
    posted_set = set(tracker.get("posted", []))
    candidates = sorted(
        (p for p in SAVE_DIR.glob("*.png") if p.name not in posted_set),
        key=lambda p: p.stat().st_mtime,
    )
    return candidates[0] if candidates else None


# ── Instagram bot class ───────────────────────────────────────────────────────

class InstagramBot:
    def __init__(self, cfg: dict):
        self.cfg = cfg

    def setup_login(self) -> None:
        """Open Instagram in the bot Chrome profile for manual login."""
        import ctypes
        driver = make_driver(self.cfg)
        driver.get(INSTAGRAM_URL)
        ctypes.windll.user32.MessageBoxW(
            0,
            "Log in to Instagram in Chrome, then click OK to save the session.",
            "Instagram Login Setup",
            0x00000040,
        )
        log.info("Login session saved.")
        driver.quit()

    def _check_logged_in(self, driver) -> bool:
        if "/accounts/login" in driver.current_url or "/login" in driver.current_url:
            return False
        try:
            WebDriverWait(driver, 8).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "nav, [role='navigation'], svg[aria-label='Home']")
                )
            )
            return True
        except Exception:
            log.warning(f"Login check failed. URL: {driver.current_url}")
            return False

    def _get_file_input(self, driver, timeout: int = 10):
        """Find the file input element, handling the sub-menu case."""
        file_input = None
        for _ in range(timeout):
            try:
                file_input = driver.find_element(By.CSS_SELECTOR, "input[type='file']")
                break
            except Exception:
                time.sleep(1)

        if file_input is None:
            # Sometimes Create opens a sub-menu — try clicking "Post" first
            post_opt = find_first(driver, [
                (By.XPATH, "//span[text()='Post']"),
                (By.XPATH, "//div[text()='Post']"),
            ], timeout=5)
            if post_opt:
                post_opt.click()
                time.sleep(2)
                try:
                    file_input = driver.find_element(By.CSS_SELECTOR, "input[type='file']")
                except Exception:
                    pass

        return file_input

    def _finish_post(self, driver, caption: str) -> tuple:
        """
        Walk through: crop step → filter step → caption step → share → confirm.
        Returns (True, post_url) or (False, None).
        """
        # Crop step → Next
        next_btn = find_first(driver, [
            (By.XPATH, "//div[@role='button' and normalize-space(text())='Next']"),
            (By.XPATH, "//button[normalize-space(text())='Next']"),
        ], timeout=15)
        if next_btn:
            next_btn.click()
            log.info("Passed crop step.")
            time.sleep(3)
        else:
            log.warning("Crop Next button not found — continuing anyway.")

        # Filter/edit step → Next
        next_btn = find_first(driver, [
            (By.XPATH, "//div[@role='button' and normalize-space(text())='Next']"),
            (By.XPATH, "//button[normalize-space(text())='Next']"),
        ], timeout=15)
        if next_btn:
            next_btn.click()
            log.info("Passed filter step.")
            time.sleep(5)
        else:
            log.warning("Filter Next button not found — continuing anyway.")
            time.sleep(3)

        # Caption step
        caption_box = find_first(driver, [
            (By.CSS_SELECTOR, "[aria-label='Write a caption...']"),
            (By.CSS_SELECTOR, "div[role='textbox']"),
            (By.XPATH, "//div[@aria-multiline='true']"),
            (By.XPATH, "//textarea[@placeholder]"),
        ], timeout=20)
        if caption_box is None:
            log.error("Caption text box not found.")
            _screenshot(driver, "caption_missing")
            return False, None

        _clipboard_paste(driver, caption_box, caption)
        log.info("Caption pasted.")
        time.sleep(2)

        # Share
        share_btn = find_first(driver, [
            (By.XPATH, "//div[@role='button' and normalize-space(text())='Share']"),
            (By.XPATH, "//button[normalize-space(text())='Share']"),
        ], timeout=15)
        if share_btn is None:
            log.error("Share button not found.")
            return False, None

        share_btn.click()
        log.info("Clicked Share — waiting for confirmation…")
        time.sleep(10)

        # Confirm
        try:
            WebDriverWait(driver, 30).until(
                EC.any_of(
                    EC.presence_of_element_located(
                        (By.XPATH, "//*[contains(text(),'Your post has been shared')]")
                    ),
                    EC.presence_of_element_located(
                        (By.XPATH, "//*[contains(text(),'Post shared')]")
                    ),
                    EC.url_contains("instagram.com/p/"),
                )
            )
            log.info("Post confirmed shared.")
        except Exception:
            log.warning("Could not confirm share — assuming success if no error.")

        # Capture post URL
        post_url: str | None = None
        username = self.cfg.get("instagram_username", "").strip()
        if username:
            try:
                driver.get(f"https://www.instagram.com/{username}/")
                time.sleep(4)
                links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/p/']")
                if links:
                    href = links[0].get_attribute("href")
                    if href and "/p/" in href:
                        post_url = href.split("?")[0]
                        log.info(f"Captured post URL: {post_url}")
            except Exception as exc:
                log.warning(f"Could not capture post URL: {exc}")

        return True, post_url

    def post_image(self, image_path: Path, caption: str) -> tuple:
        """Upload a single image to Instagram. Returns (True, post_url) or (False, None)."""
        log.info(f"Posting: {image_path.name}")
        driver = make_driver(self.cfg)
        try:
            driver.get(INSTAGRAM_URL)
            time.sleep(4)

            if not self._check_logged_in(driver):
                log.error("Not logged in to Instagram. Run: python art_bot.py login instagram")
                return False, None

            # Click Create / New Post
            create_btn = find_first(driver, [
                (By.CSS_SELECTOR, "svg[aria-label='New post']"),
                (By.XPATH, "//*[@aria-label='New post']"),
                (By.XPATH, "//span[contains(text(),'Create')]"),
                (By.XPATH, "//a[contains(@href,'/create/')]"),
            ], timeout=10)
            if not create_btn:
                log.error("Create/New Post button not found.")
                return False, None
            create_btn.click()
            time.sleep(2)

            # Upload file
            file_input = self._get_file_input(driver)
            if file_input is None:
                log.error("File input element not found.")
                return False, None

            file_input.send_keys(str(image_path.resolve()))
            log.info("File selected, waiting for crop step…")
            time.sleep(5)

            return self._finish_post(driver, caption)

        except Exception as exc:
            log.error(f"post_image() failed: {exc}", exc_info=True)
            return False, None
        finally:
            try:
                driver.quit()
            except Exception:
                pass
