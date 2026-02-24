"""
Instagram Auto-Poster for AI Art Bot
Posts 3 images/day at peak engagement windows.
Caption = date + time + full prompt + smart hashtags.
Run every 30 minutes via Windows Task Scheduler (see setup_instagram_scheduler.ps1)
"""

import ctypes
import ctypes.wintypes
import json
import logging
import random
import re
import time
from datetime import datetime, timedelta
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# ── Paths ─────────────────────────────────────────────────────────────────────

BOT_DIR      = Path(__file__).parent
SAVE_DIR     = Path(r"C:\Users\gageg\Desktop\AI_Art")
CONFIG_FILE  = BOT_DIR / "config.json"
TRACKER_FILE = BOT_DIR / "posted_tracker.json"
LOG_DIR      = BOT_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

INSTAGRAM_URL = "https://www.instagram.com/"

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.FileHandler(
            LOG_DIR / f"instagram_{datetime.now().strftime('%Y%m%d')}.log",
            encoding="utf-8",
        ),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("instagram_bot")

# ── Peak posting times (day-of-week, 0=Monday … 6=Sunday) ────────────────────
# Research-backed best times for art/creative accounts on Instagram (local time).

BEST_TIMES = {
    0: [(8, 0), (13, 0), (21, 0)],   # Monday
    1: [(7, 0), (12, 0), (20, 0)],   # Tuesday
    2: [(7, 0), (11, 0), (21, 0)],   # Wednesday
    3: [(8, 0), (12, 0), (20, 0)],   # Thursday
    4: [(9, 0), (13, 0), (20, 0)],   # Friday
    5: [(10, 0), (14, 0), (20, 0)],  # Saturday
    6: [(10, 0), (13, 0), (21, 0)],  # Sunday
}

WINDOW_MINUTES = 30   # post within ±30 min of target slot
DAILY_CAP      = 3    # max posts per calendar day

# ── Hashtag system ────────────────────────────────────────────────────────────
#
# Three-tier strategy for maximum reach + engagement:
#   MEGA  (>5M posts)  — broad discovery, always included
#   MID   (200K–5M)    — strong engagement community, always included
#   NICHE (<200K)      — highly targeted, best conversion, keyword-derived
#
# Research shows the optimal mix for art accounts is:
#   4–5 mega tags + 6–8 mid tags + 12–16 niche tags ≈ 25–28 total

MAX_HASHTAGS = 28

# Always included — mega reach tags (rotate a random subset so posts
# don't look identical and avoid hashtag-ban triggers)
MEGA_TAGS = [
    "#art", "#artist", "#artwork", "#painting", "#illustration",
    "#drawing", "#creative", "#design", "#photography", "#nature",
]

# Always included — strong mid-size art community tags
MID_TAGS = [
    "#digitalart", "#artoftheday", "#artistsoninstagram", "#contemporaryart",
    "#conceptart", "#visualart", "#artgallery", "#fineart", "#instaart",
    "#artstagram", "#artcollective", "#artlovers", "#surrealism",
    "#fantasyart", "#imaginaryworlds",
]

# Keyword → [niche tags] mapped from prompt content.
# Each entry mixes highly specific niche tags (best engagement-per-follower)
# with a couple of mid-tier tags unique to that theme.
HASHTAG_MAP: dict[str, list[str]] = {
    # ── Medium / technique ────────────────────────────────────────────────────
    "watercolour":      ["#watercolour", "#watercolorpainting", "#watercolorart",
                         "#watercolorillustration", "#aquarelle"],
    "watercolor":       ["#watercolor", "#watercolorpainting", "#watercolorart",
                         "#watercolorillustration", "#aquarelle"],
    "oil paint":        ["#oilpainting", "#oiloncanvas", "#oilpaintings",
                         "#classicpainting", "#oldmastersart"],
    "oil":              ["#oilpainting", "#oiloncanvas", "#oilpaintings"],
    "acrylic":          ["#acrylicpainting", "#acrylicart", "#acrylicartist",
                         "#acrylicpour"],
    "ink":              ["#inkdrawing", "#inkart", "#penandink",
                         "#inkillustration", "#inkwork"],
    "gouache":          ["#gouache", "#gouacheart", "#gouachepainting",
                         "#gouacheillustration"],
    "charcoal":         ["#charcoaldrawing", "#charcoalart", "#charcoalsketch",
                         "#blackandwhiteart"],
    "pastel":           ["#pastelart", "#pastelpainting", "#softpastel",
                         "#pastelcolors"],
    "etching":          ["#etching", "#printmaking", "#intaglio",
                         "#printmakingartist"],
    "linocut":          ["#linocut", "#printmaking", "#linocutprint",
                         "#blockprint"],
    # ── Film / photography ───────────────────────────────────────────────────
    "film":             ["#filmphotography", "#analogphotography", "#filmisnotdead",
                         "#shootfilm", "#35mmfilm"],
    "kodachrome":       ["#kodachrome", "#filmphotography", "#analogphotography",
                         "#filmisnotdead", "#slidefilm"],
    "portra":           ["#kodakportra", "#filmphotography", "#35mm",
                         "#filmisnotdead", "#portra400"],
    "tri-x":            ["#kodaktrix", "#blackandwhitefilm", "#filmisnotdead",
                         "#analogphotography", "#35mmfilm"],
    "pinhole":          ["#pinholephotography", "#alternativeprocess",
                         "#pinholefilm", "#cameraobscura"],
    "hasselblad":       ["#hasselblad", "#mediumformat", "#filmphotography",
                         "#120film"],
    "long exposure":    ["#longexposure", "#longexposurephotography",
                         "#slowshutter", "#lightpainting"],
    "black and white":  ["#blackandwhitephotography", "#blackandwhite",
                         "#bnwphotography", "#monochrome", "#bnw"],
    # ── Named artists / styles ────────────────────────────────────────────────
    "ghibli":           ["#studioghibli", "#ghibliart", "#ghibliaesthetic",
                         "#animeart", "#anime", "#miyazaki"],
    "moebius":          ["#moebius", "#jeanmoebius", "#sciencefictionart",
                         "#graphicnovel", "#comicart"],
    "giraud":           ["#moebius", "#jeanmoebius", "#sciencefictionart",
                         "#graphicnovel"],
    "beksinski":        ["#beksinski", "#darkart", "#surrealpainting",
                         "#darkfantasyart", "#horrorart"],
    "rembrandt":        ["#rembrandt", "#baroque", "#oldmastersart",
                         "#chiaroscuro", "#classicpainting"],
    "vermeer":          ["#vermeer", "#baroque", "#dutchgoldenage",
                         "#classicpainting", "#oldmastersart"],
    "klimt":            ["#klimt", "#artnouveau", "#gustavklimt",
                         "#jugendstil", "#symbolism"],
    "hokusai":          ["#hokusai", "#ukiyoe", "#japanesewoodblock",
                         "#japaneseart", "#woodblockprint"],
    "mucha":            ["#mucha", "#alphonsmucha", "#artnouveau",
                         "#jugendstil", "#decorativeart"],
    "caravaggio":       ["#caravaggio", "#baroque", "#chiaroscuro",
                         "#oldmastersart", "#classicpainting"],
    "turner":           ["#jmwturner", "#romanticism", "#landscapepainting",
                         "#britishart", "#atmosphericpainting"],
    "sargent":          ["#johnssingersargent", "#impressionism",
                         "#portraitpainting", "#americanart"],
    "monet":            ["#monet", "#impressionism", "#claudemonet",
                         "#impressionistpainting", "#pleinair"],
    "dali":             ["#dali", "#salvadordali", "#surrealism",
                         "#surrealart", "#dalipainting"],
    "escher":           ["#escher", "#mcescher", "#geometricart",
                         "#impossibleart", "#opticalillusion"],
    "frazetta":         ["#frazetta", "#frankfrazetta", "#fantasyart",
                         "#heroicfantasy", "#fantasypainting"],
    # ── Historical periods / movements ───────────────────────────────────────
    "baroque":          ["#baroque", "#baroqueart", "#oldmastersart",
                         "#classicpainting", "#chiaroscuro"],
    "impressionism":    ["#impressionism", "#impressionistpainting",
                         "#pleinair", "#impressionistart"],
    "impressionist":    ["#impressionism", "#impressionistpainting",
                         "#pleinair", "#impressionistart"],
    "art nouveau":      ["#artnouveau", "#jugendstil", "#decorativeart",
                         "#natureinspired", "#organicdesign"],
    "art deco":         ["#artdeco", "#artdecodesign", "#vintageposter",
                         "#geometricart", "#twentiesart"],
    "romanticism":      ["#romanticism", "#romanticpainting", "#19thcenturyart",
                         "#landscapepainting"],
    "symbolism":        ["#symbolism", "#symbolistart", "#mysticalart",
                         "#esotericart"],
    "gothic":           ["#gothicart", "#darkromanticism", "#gothicaesthetic",
                         "#macabreart", "#darkart"],
    "medieval":         ["#medievalart", "#medievalpainting", "#gothicart",
                         "#historicalart", "#illuminatedmanuscript"],
    "illuminated":      ["#illuminatedmanuscript", "#medievalart",
                         "#manuscriptart", "#historicalillustration"],
    "renaissance":      ["#renaissanceart", "#renaissance", "#oldmastersart",
                         "#italianart", "#classicpainting"],
    # ── Subject matter ────────────────────────────────────────────────────────
    "portrait":         ["#portraitpainting", "#portraiture", "#figurativeart",
                         "#portraitart", "#facepainting"],
    "figure":           ["#figurativeart", "#figurativepainting", "#humanform",
                         "#lifedrawing", "#figuralart"],
    "self portrait":    ["#selfportrait", "#portraitpainting", "#selfportraitart",
                         "#artistselfportrait"],
    "landscape":        ["#landscapepainting", "#landscapeart", "#scenery",
                         "#outdoorpainting", "#pleinair"],
    "cityscape":        ["#cityscape", "#cityscapepainting", "#urbanart",
                         "#architectureart", "#cityart"],
    "still life":       ["#stilllife", "#stilllifepainting", "#vanitas",
                         "#botanicalart"],
    "abstract":         ["#abstractart", "#abstractpainting", "#abstractexpressionism",
                         "#abstractartist", "#abstractdaily"],
    # ── Nature / environment ──────────────────────────────────────────────────
    "forest":           ["#forestpainting", "#woodlandart", "#enchantedforest",
                         "#natureart", "#treeart"],
    "jungle":           ["#jungleart", "#tropicalart", "#rainforest",
                         "#lushfoliage", "#natureart"],
    "ocean":            ["#seascape", "#oceanart", "#marinepainting",
                         "#seascapepainting", "#waveart"],
    "sea":              ["#seascape", "#oceanart", "#marinepainting",
                         "#seascapepainting"],
    "river":            ["#riverpainting", "#waterscape", "#streamscape",
                         "#natureart"],
    "waterfall":        ["#waterfallpainting", "#natureart", "#waterfallart",
                         "#cascades"],
    "mountain":         ["#mountainpainting", "#mountainscape", "#alpineart",
                         "#mountainart", "#highaltitude"],
    "desert":           ["#desertart", "#desertlandscape", "#aridlandscape",
                         "#sanddunes"],
    "cave":             ["#caveart", "#undergroundart", "#spelunkingphotography",
                         "#cavernart"],
    "garden":           ["#gardenart", "#botanicalart", "#floralpaining",
                         "#gardenpainting"],
    "flowers":          ["#floralart", "#botanicalillustration", "#floralpaining",
                         "#botanicalart", "#flowerpainting"],
    "tree":             ["#treeart", "#treepainting", "#natureart",
                         "#forestpainting"],
    "fog":              ["#atmosphericart", "#foggylandscape", "#moodyphotography",
                         "#mistylandscape", "#atmosphericphotography"],
    "mist":             ["#atmosphericart", "#mistyphotography", "#moodylandscape",
                         "#mistyforest"],
    "storm":            ["#stormpainting", "#dramaticskies", "#stormscape",
                         "#thunderstorm", "#dramaticart"],
    "snow":             ["#snowscene", "#winterlandscape", "#snowpainting",
                         "#winterart"],
    "fire":             ["#fireart", "#flameart", "#pyroart",
                         "#lightandshadow"],
    "night":            ["#nightscene", "#nightphotography", "#nightscape",
                         "#nocturnal", "#nightart"],
    "sunset":           ["#sunsetpainting", "#goldenhourst", "#sunsetart",
                         "#twilight", "#duskphotography"],
    "aurora":           ["#auroraborialis", "#northernlights", "#aurorapainting",
                         "#polarlight"],
    # ── Architecture / place ─────────────────────────────────────────────────
    "cathedral":        ["#cathedralart", "#gothicarchitecture", "#sacredart",
                         "#architecturephotography", "#gothicart"],
    "temple":           ["#templeart", "#sacredarchitecture", "#ancientart",
                         "#archaeologyart"],
    "castle":           ["#castleart", "#medievalcastle", "#fortressart",
                         "#historicalarchitecture"],
    "ruin":             ["#ruins", "#ruinsoftheworld", "#abandonedplaces",
                         "#historicalruins", "#ancientruins"],
    "library":          ["#libraryart", "#bookart", "#bibliophile",
                         "#literaryart", "#booksofinstagram"],
    "staircase":        ["#staircaseart", "#architecturepainting",
                         "#perspectiveart", "#architectureart"],
    "stained glass":    ["#stainedglass", "#stainedglassart", "#sacredart",
                         "#churchwindow", "#gothicart"],
    # ── Themes / mood ─────────────────────────────────────────────────────────
    "space":            ["#spaceart", "#cosmicart", "#astronomy",
                         "#scifiart", "#sciencefiction"],
    "cosmos":           ["#cosmicart", "#cosmos", "#universe",
                         "#spaceart", "#astrophotography"],
    "galaxy":           ["#galaxyart", "#galaxyphotography", "#nebulaart",
                         "#deepspace", "#spaceart"],
    "star":             ["#stargazing", "#nightsky", "#astrophotography",
                         "#celestialart", "#starrynight"],
    "moon":             ["#moonart", "#moonphotography", "#lunarart",
                         "#fullmoon", "#celestialart"],
    "astronaut":        ["#astronautart", "#scifiart", "#spaceexploration",
                         "#spaceart", "#futurism"],
    "dragon":           ["#dragonart", "#dragonpainting", "#mythologicalart",
                         "#fantasypainting", "#epicart"],
    "mythology":        ["#mythologyart", "#mythologicalart", "#classicalmythology",
                         "#epicart", "#legendaryart"],
    "ancient":          ["#ancientart", "#ancienthistory", "#archaeologyart",
                         "#historicalpainting"],
    "magic":            ["#magicart", "#mysticalart", "#enchanted",
                         "#magicalrealism", "#fantasyart"],
    "light":            ["#chiaroscuro", "#lightandshadow", "#luminismart",
                         "#lightpainting", "#glowingart"],
    "shadow":           ["#chiaroscuro", "#lightandshadow", "#silhouetteart",
                         "#darkart", "#moodylighting"],
    # ── Japanese / Asian ──────────────────────────────────────────────────────
    "japanese":         ["#japaneseart", "#japanesepainting", "#asianart",
                         "#japaneseaesthetics", "#wabi_sabi"],
    "samurai":          ["#samuraiart", "#bushido", "#japaneseart",
                         "#katana", "#feudaljapan"],
    "ukiyo":            ["#ukiyoe", "#woodblockprint", "#japanesewoodblock",
                         "#japaneseprint", "#japaneseart"],
    "zen":              ["#zenart", "#zenpainting", "#japaneseart",
                         "#mindfulart", "#wabi_sabi"],
    # ── Sci-fi / futurism ─────────────────────────────────────────────────────
    "cyberpunk":        ["#cyberpunkart", "#cyberpunk", "#futuristicart",
                         "#neonart", "#dystopianart"],
    "steampunk":        ["#steampunkart", "#steampunk", "#victorianfuturism",
                         "#retrofuturism", "#steampunkfashion"],
    "futurist":         ["#futurism", "#futuristicart", "#retrofuturism",
                         "#scifiart", "#sciencefictionart"],
    "post-apocalyptic": ["#postapocalyptic", "#dystopianart", "#survivorart",
                         "#apocalypseart"],
}


# ── Hashtag generation ────────────────────────────────────────────────────────

def generate_hashtags(prompt: str) -> str:
    """
    Build an optimised, tiered hashtag set from the prompt.

    Strategy (28 tags max):
      • 3 random MEGA tags  — broad discovery reach
      • 6 random MID tags   — established art community engagement
      • Up to 19 NICHE tags — keyword-matched, highest engagement-per-view
    """
    prompt_lower = prompt.lower()

    # Collect all matching niche tags (deduplicated, prompt order)
    niche: list[str] = []
    for keyword, tags in HASHTAG_MAP.items():
        if keyword in prompt_lower:
            for t in tags:
                if t not in niche:
                    niche.append(t)

    # Sample from each tier
    mega_sample = random.sample(MEGA_TAGS, min(3, len(MEGA_TAGS)))
    mid_pool    = [t for t in MID_TAGS if t not in mega_sample]
    mid_sample  = random.sample(mid_pool, min(6, len(mid_pool)))

    # Shuffle niche tags so each post doesn't look identical
    random.shuffle(niche)

    # Combine: mega → mid → niche, then cap
    combined: list[str] = []
    seen: set[str] = set()
    for tag in mega_sample + mid_sample + niche:
        if tag not in seen:
            seen.add(tag)
            combined.append(tag)
        if len(combined) >= MAX_HASHTAGS:
            break

    return " ".join(combined)


# ── Caption builder ───────────────────────────────────────────────────────────

def build_caption(image_path: Path) -> str:
    """Read the _meta.json sidecar and assemble the caption."""
    meta_path = image_path.with_name(image_path.stem + "_meta.json")
    if not meta_path.exists():
        log.warning(f"No meta file found for {image_path.name}")
        prompt = image_path.stem.replace("_", " ")
        generated_at = datetime.now()
    else:
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        prompt = meta.get("prompt", image_path.stem)
        generated_at = datetime.fromisoformat(meta.get("generated_at", datetime.now().isoformat()))

    date_str = generated_at.strftime("%B %#d, %Y")   # "February 23, 2026"
    time_str = generated_at.strftime("%#I:%M %p")    # "12:10 PM"
    hashtags = generate_hashtags(prompt)

    caption = (
        f"{date_str} at {time_str}\n\n"
        f"{prompt}\n\n"
        f"{hashtags}"
    )
    return caption


def build_series_caption(series_data: dict, now: datetime | None = None) -> str:
    """
    Build a structured multi-variation caption for a carousel post.

    Format:
        February 24, 2026 at 12:00 PM

        A scholar translating manuscripts..., at the edge of a sheer cliff.

          ↗ Baroque impasto oils · Profound melancholy
          ↗ Art Nouveau poster · Ancient forgotten wonder
          ↗ Gustave Doré engraving · Electric tension

        #digitalart #surrealism ...
    """
    from art_bot import _shorten_descriptor
    if now is None:
        now = datetime.now()
    date_str = now.strftime("%B %#d, %Y")
    time_str = now.strftime("%#I:%M %p")

    base_subject = series_data.get("base_subject", "")
    base_env     = series_data.get("base_env", "")
    subject_line = f"{base_subject.capitalize()}, {base_env}."

    variation_lines = []
    for vc in series_data.get("variation_components", []):
        style_short = _shorten_descriptor(vc.get("style", ""))
        mood_short  = _shorten_descriptor(vc.get("mood", ""))
        variation_lines.append(f"  \u2197 {style_short} \u00b7 {mood_short}")

    # Feed all style/mood/subject text through the hashtag generator
    hashtag_text = " ".join(
        vc.get("style", "") + " " + vc.get("mood", "")
        for vc in series_data.get("variation_components", [])
    )
    full_text = f"{base_subject} {base_env} {hashtag_text}"
    hashtags  = generate_hashtags(full_text)

    caption = (
        f"{date_str} at {time_str}\n\n"
        f"{subject_line}\n\n"
        + "\n".join(variation_lines)
        + f"\n\n{hashtags}"
    )
    return caption


def pick_unposted_series() -> tuple | None:
    """
    Return (series_id, series_data, [existing_paths]) for the oldest unposted
    series that has at least 2 images on disk, or None if none found.
    """
    from art_bot import _load_series_manifest
    for series_id, data in sorted(_load_series_manifest().get("series", {}).items()):
        if data.get("posted"):
            continue
        existing = [
            SAVE_DIR / f
            for f in data.get("files", [])
            if (SAVE_DIR / f).exists()
        ]
        if len(existing) >= 2:
            return series_id, data, existing
    return None


# ── Posting window check ──────────────────────────────────────────────────────

def is_posting_window(now: datetime | None = None) -> bool:
    """Return True if current time falls within a peak posting window."""
    if now is None:
        now = datetime.now()
    day = now.weekday()
    slots = BEST_TIMES.get(day, [])
    for hour, minute in slots:
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        delta  = abs((now - target).total_seconds())
        if delta <= WINDOW_MINUTES * 60:
            return True
    return False


def next_posting_window(now: datetime | None = None) -> str:
    """Human-readable description of next peak window."""
    if now is None:
        now = datetime.now()
    candidates = []
    for offset in range(8):  # look up to 7 days ahead
        day = (now + timedelta(days=offset)).replace(hour=0, minute=0, second=0, microsecond=0)
        weekday = day.weekday()
        for hour, minute in BEST_TIMES.get(weekday, []):
            candidate = day.replace(hour=hour, minute=minute)
            if candidate > now:
                candidates.append(candidate)
    if candidates:
        nxt = min(candidates)
        return nxt.strftime("%A at %#I:%M %p")
    return "unknown"


# ── Tracker ───────────────────────────────────────────────────────────────────

def load_tracker() -> dict:
    if TRACKER_FILE.exists():
        try:
            with open(TRACKER_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"posted": [], "daily_counts": {}}


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


def mark_series_posted(series_id: str, image_paths: list, tracker: dict,
                       post_url: str | None) -> None:
    """Mark every image in a series as posted and flag the manifest entry."""
    for p in image_paths:
        mark_posted(tracker, Path(p), post_url)
    save_tracker(tracker)

    from art_bot import _load_series_manifest, _save_series_manifest
    manifest = _load_series_manifest()
    if series_id in manifest.get("series", {}):
        manifest["series"][series_id]["posted"] = True
        _save_series_manifest(manifest)


def pick_unposted_image(tracker: dict) -> Path | None:
    """Return the oldest unposted PNG from SAVE_DIR, or None."""
    posted_set = set(tracker.get("posted", []))
    candidates = sorted(
        (p for p in SAVE_DIR.glob("*.png") if p.name not in posted_set),
        key=lambda p: p.stat().st_mtime,
    )
    return candidates[0] if candidates else None


# ── Config ────────────────────────────────────────────────────────────────────

def load_config() -> dict:
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"chrome_profile_path": "", "instagram_username": "", "instagram_password": ""}


# ── Selenium helpers ──────────────────────────────────────────────────────────

def _clear_profile_locks(profile_dir: str) -> None:
    """Recursively remove every Chrome lock file in the profile tree."""
    root = Path(profile_dir)
    for pattern in ("LOCK", "SingletonLock", "SingletonCookie", "SingletonSocket"):
        for p in root.rglob(pattern):
            try:
                p.unlink()
                log.debug(f"Removed lock: {p}")
            except Exception:
                pass


def make_driver(cfg: dict) -> webdriver.Chrome:
    opts = Options()
    profile = cfg.get("chrome_profile_path", "").strip()
    if profile:
        Path(profile).mkdir(parents=True, exist_ok=True)
        _clear_profile_locks(profile)
        opts.add_argument(f"--user-data-dir={profile}")
        log.info(f"Chrome profile: {profile}")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    opts.add_argument("--window-size=1400,960")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--no-first-run")
    opts.add_argument("--no-default-browser-check")
    driver = webdriver.Chrome(options=opts)
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"},
    )
    return driver


def slow_type(element, text: str) -> None:
    for ch in text:
        element.send_keys(ch)
        if random.random() < 0.05:
            time.sleep(random.uniform(0.05, 0.2))


def _set_clipboard(text: str) -> None:
    """Write text to the Windows clipboard (handles 64-bit pointer sizes correctly)."""
    import subprocess
    from pathlib import Path as _Path

    # Write to a temp file and use PowerShell to set the clipboard.
    # This avoids all ctypes pointer-width issues on 64-bit Windows.
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
    """Set Windows clipboard to text, click element, then Ctrl+V.

    More reliable than send_keys() for React contenteditable divs because
    it avoids stale element references from mid-typing DOM re-renders.
    """
    _set_clipboard(text)

    # Focus the element and paste
    element.click()
    time.sleep(0.5)
    element.send_keys(Keys.CONTROL, "a")   # select all (clear any placeholder text)
    time.sleep(0.2)
    element.send_keys(Keys.CONTROL, "v")   # paste
    time.sleep(0.5)


def find_first(driver, selectors: list[tuple], timeout: int = 15):
    for by, sel in selectors:
        try:
            el = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((by, sel))
            )
            log.debug(f"Found element: {sel}")
            return el
        except Exception:
            pass
    return None


# ── Instagram bot class ───────────────────────────────────────────────────────

class InstagramBot:
    def __init__(self, cfg: dict):
        self.cfg = cfg

    # ─ Login setup (interactive) ─────────────────────────────────────────────

    def setup_login(self) -> None:
        """Open Instagram in the bot profile so the user can log in manually."""
        import ctypes
        log.info("Opening Instagram for manual login setup…")
        driver = make_driver(self.cfg)
        driver.get(INSTAGRAM_URL)
        ctypes.windll.user32.MessageBoxW(
            0,
            "Log in to Instagram in the Chrome window, then click OK to save the session.",
            "Instagram Login Setup",
            0x00000040,  # MB_ICONINFORMATION
        )
        log.info("Login session saved to Chrome profile.")
        driver.quit()

    # ─ Check login state ─────────────────────────────────────────────────────

    def _check_logged_in(self, driver) -> bool:
        """Return True if the Instagram session is active."""
        # If Instagram redirected to login page, we're definitely not logged in
        if "/accounts/login" in driver.current_url or "/login" in driver.current_url:
            return False
        # If we're on the home URL with the right title, we're in
        if driver.current_url.rstrip("/") == "https://www.instagram.com":
            if "Login" not in driver.title:
                log.info(f"Logged in — URL: {driver.current_url}, Title: {driver.title}")
                return True
        # Fallback: look for any nav or sidebar element that only appears when logged in
        try:
            WebDriverWait(driver, 8).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "nav, [role='navigation'], svg[aria-label='Home']")
                )
            )
            return True
        except Exception:
            log.warning(f"Login check fallback failed. URL: {driver.current_url}")
            return False

    # ─ Shared upload helpers ──────────────────────────────────────────────────

    def _get_file_input(self, driver, timeout: int = 10):
        """Find and return the file input element, handling the sub-menu case."""
        file_input = None
        for _ in range(timeout):
            try:
                file_input = driver.find_element(By.CSS_SELECTOR, "input[type='file']")
                break
            except Exception:
                time.sleep(1)

        if file_input is None:
            # Sometimes Create opens a sub-menu; try clicking "Post" first
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
        Handle the shared end-of-post steps (crop → filter → caption → share →
        confirm → URL capture). Returns (True, post_url) or (False, None).
        """
        # ── Step 3: crop step → click Next ─────────────────────────────────
        next_btn = find_first(driver, [
            (By.XPATH, "//div[@role='button' and normalize-space(text())='Next']"),
            (By.XPATH, "//button[normalize-space(text())='Next']"),
            (By.XPATH, "//*[contains(@class,'Next')]"),
        ], timeout=15)
        if next_btn:
            next_btn.click()
            log.info("Passed crop step.")
            time.sleep(3)
        else:
            log.warning("Crop Next button not found — trying to continue anyway.")

        # ── Step 4: filter/edit step → click Next ──────────────────────────
        next_btn = find_first(driver, [
            (By.XPATH, "//div[@role='button' and normalize-space(text())='Next']"),
            (By.XPATH, "//button[normalize-space(text())='Next']"),
        ], timeout=15)
        if next_btn:
            next_btn.click()
            log.info("Passed filter step.")
            time.sleep(5)   # extra wait — React re-renders caption step
        else:
            log.warning("Filter Next button not found — trying to continue anyway.")
            time.sleep(3)

        # ── Step 5: caption step ────────────────────────────────────────────
        caption_box = find_first(driver, [
            (By.CSS_SELECTOR, "[aria-label='Write a caption...']"),
            (By.CSS_SELECTOR, "div[role='textbox']"),
            (By.XPATH, "//div[@aria-multiline='true']"),
            (By.XPATH, "//textarea[@placeholder]"),
        ], timeout=20)

        if caption_box is None:
            log.error("Could not find caption text box.")
            return False, None

        _clipboard_paste(driver, caption_box, caption)
        log.info("Caption pasted.")
        time.sleep(2)

        # ── Step 6: click Share ─────────────────────────────────────────────
        share_btn = find_first(driver, [
            (By.XPATH, "//div[@role='button' and normalize-space(text())='Share']"),
            (By.XPATH, "//button[normalize-space(text())='Share']"),
        ], timeout=15)

        if share_btn is None:
            log.error("Could not find Share button.")
            return False, None

        share_btn.click()
        log.info("Clicked Share — waiting for upload confirmation…")
        time.sleep(10)

        # ── Step 7: confirm success ─────────────────────────────────────────
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
            log.info("Post confirmed shared successfully.")
        except Exception:
            log.warning("Could not confirm share — assuming success if no error.")

        # ── Step 8: capture the post URL ────────────────────────────────────
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

    # ─ Core post flow ─────────────────────────────────────────────────────────

    def post_image(self, image_path: Path, caption: str) -> tuple:
        """Upload a single image to Instagram with the given caption.
        Returns (True, post_url) on success, (False, None) on failure."""
        log.info(f"Posting: {image_path.name}")
        driver = make_driver(self.cfg)
        try:
            driver.get(INSTAGRAM_URL)
            time.sleep(4)

            if not self._check_logged_in(driver):
                log.error("Not logged in to Instagram. Run: python instagram_bot.py login")
                return False, None

            # ── Step 1: click the Create / New Post button ─────────────────
            create_btn = find_first(driver, [
                (By.CSS_SELECTOR, "svg[aria-label='New post']"),
                (By.XPATH, "//*[@aria-label='New post']"),
                (By.XPATH, "//span[contains(text(),'Create')]"),
                (By.XPATH, "//a[contains(@href,'/create/')]"),
            ], timeout=10)

            if not create_btn:
                log.error("Could not find the Create/New Post button.")
                return False, None
            create_btn.click()
            time.sleep(2)

            # ── Step 2: upload the image file ──────────────────────────────
            file_input = self._get_file_input(driver)
            if file_input is None:
                log.error("Could not find file input element.")
                return False, None

            file_input.send_keys(str(image_path.resolve()))
            log.info("File selected, waiting for crop step…")
            time.sleep(5)

            # ── Steps 3–8: crop / filter / caption / share / confirm / URL ─
            return self._finish_post(driver, caption)

        except Exception as exc:
            log.error(f"post_image() failed: {exc}", exc_info=True)
            return False, None
        finally:
            driver.quit()

    # ─ Carousel post flow ─────────────────────────────────────────────────────

    def post_series(self, image_paths: list, caption: str) -> tuple:
        """
        Upload multiple images as an Instagram carousel post.
        Returns (True, post_url) on success, (False, None) on failure.
        Falls back to a single-image post if carousel mode can't be enabled.
        """
        log.info(f"Posting carousel: {len(image_paths)} images")
        driver = make_driver(self.cfg)
        try:
            driver.get(INSTAGRAM_URL)
            time.sleep(4)

            if not self._check_logged_in(driver):
                log.error("Not logged in to Instagram. Run: python instagram_bot.py login")
                return False, None

            # ── Step 1: click Create ────────────────────────────────────────
            create_btn = find_first(driver, [
                (By.CSS_SELECTOR, "svg[aria-label='New post']"),
                (By.XPATH, "//*[@aria-label='New post']"),
                (By.XPATH, "//span[contains(text(),'Create')]"),
                (By.XPATH, "//a[contains(@href,'/create/')]"),
            ], timeout=10)
            if not create_btn:
                log.error("Could not find Create/New Post button.")
                return False, None
            create_btn.click()
            time.sleep(2)

            # ── Step 2: upload first image ──────────────────────────────────
            file_input = self._get_file_input(driver)
            if file_input is None:
                log.error("Could not find file input element.")
                return False, None
            file_input.send_keys(str(Path(image_paths[0]).resolve()))
            log.info(f"Uploaded image 1/{len(image_paths)}, waiting for crop step…")
            time.sleep(5)

            # ── Step 3: enable carousel mode and upload remaining images ────
            if len(image_paths) > 1:
                select_multiple = find_first(driver, [
                    (By.CSS_SELECTOR, "svg[aria-label='Select multiple']"),
                    (By.XPATH, "//*[@aria-label='Select multiple']"),
                    (By.XPATH, "//button[contains(@aria-label,'multiple')]"),
                ], timeout=10)

                if select_multiple:
                    select_multiple.click()
                    log.info("Carousel mode enabled.")
                    time.sleep(2)

                    for i, img_path in enumerate(image_paths[1:], start=2):
                        add_btn = find_first(driver, [
                            (By.CSS_SELECTOR, "button[aria-label='+']"),
                            (By.XPATH, "//button[@aria-label='+']"),
                            (By.XPATH, "//button[normalize-space()='+']"),
                        ], timeout=10)
                        if not add_btn:
                            log.warning(f"Could not find '+' button for image {i}/{len(image_paths)}")
                            break
                        add_btn.click()
                        time.sleep(2)

                        fi = self._get_file_input(driver)
                        if fi is None:
                            log.warning(f"No file input found for image {i}/{len(image_paths)}")
                            break
                        fi.send_keys(str(Path(img_path).resolve()))
                        log.info(f"Uploaded image {i}/{len(image_paths)}")
                        time.sleep(3)
                else:
                    log.warning("'Select multiple' button not found — posting as single image.")

            # ── Steps 4–9 (shared): crop / filter / caption / share / URL ──
            return self._finish_post(driver, caption)

        except Exception as exc:
            log.error(f"post_series() failed: {exc}", exc_info=True)
            return False, None
        finally:
            driver.quit()

    # ─ Posting cycle (called every 30 min by scheduler) ──────────────────────

    def run_posting_cycle(self) -> None:
        """Post one carousel (or single image) if inside a peak window and under the daily cap."""
        now      = datetime.now()
        tracker  = load_tracker()
        date_str = now.strftime("%Y-%m-%d")
        count    = daily_count(tracker, date_str)

        if count >= DAILY_CAP:
            log.info(f"Daily cap reached ({count}/{DAILY_CAP}). Next window: {next_posting_window(now)}")
            return

        if not is_posting_window(now):
            log.info(f"Outside posting window. Next window: {next_posting_window(now)}")
            return

        # ── Try carousel (series) first ────────────────────────────────────
        series_result = pick_unposted_series()
        if series_result:
            series_id, series_data, image_paths = series_result
            caption = build_series_caption(series_data, now)
            log.info(f"Peak window active. Posting carousel {count + 1}/{DAILY_CAP}: {series_id}")
            log.info(f"Caption preview: {caption[:120]}…")
            success, post_url = self.post_series([str(p) for p in image_paths], caption)
            if success:
                mark_series_posted(series_id, [str(p) for p in image_paths], tracker, post_url)
                log.info(f"Carousel posted! Daily count: {daily_count(tracker, date_str)}/{DAILY_CAP}")
                try:
                    from engagement_bot import run_post_engagement
                    run_post_engagement(self.cfg, caption)
                except Exception as exc:
                    log.warning(f"Engagement session failed (non-fatal): {exc}")
            else:
                log.error("Carousel post failed. Will retry at next scheduler run.")
            return

        # ── Fall back to single image ───────────────────────────────────────
        image = pick_unposted_image(tracker)
        if image is None:
            log.warning("No unposted images or series found in AI_Art folder.")
            return

        caption = build_caption(image)
        log.info(f"Peak window active. Posting image {count + 1}/{DAILY_CAP}: {image.name}")
        log.info(f"Caption preview: {caption[:120]}…")

        success, post_url = self.post_image(image, caption)
        if success:
            mark_posted(tracker, image, post_url)
            save_tracker(tracker)
            log.info(f"Posted! Daily count: {daily_count(tracker, date_str)}/{DAILY_CAP}")
            try:
                from engagement_bot import run_post_engagement
                run_post_engagement(self.cfg, caption)
            except Exception as exc:
                log.warning(f"Engagement session failed (non-fatal): {exc}")
        else:
            log.error("Post failed. Will retry at next scheduler run.")

    # ─ Force post (bypass window/cap checks) ─────────────────────────────────

    def force_post(self) -> None:
        """Post the next unposted series (carousel) or single image, bypassing time/cap."""
        tracker = load_tracker()

        # ── Try carousel (series) first ────────────────────────────────────
        series_result = pick_unposted_series()
        if series_result:
            series_id, series_data, image_paths = series_result
            caption = build_series_caption(series_data)
            log.info(f"Force-posting carousel: {series_id} ({len(image_paths)} images)")
            success, post_url = self.post_series([str(p) for p in image_paths], caption)
            if success:
                mark_series_posted(series_id, [str(p) for p in image_paths], tracker, post_url)
                log.info("Force carousel post complete.")
                try:
                    from engagement_bot import run_post_engagement
                    run_post_engagement(self.cfg, caption)
                except Exception as exc:
                    log.warning(f"Engagement session failed (non-fatal): {exc}")
            else:
                log.error("Force carousel post failed.")
            return

        # ── Fall back to single image ───────────────────────────────────────
        image = pick_unposted_image(tracker)
        if image is None:
            log.warning("No unposted images or series to force-post.")
            return
        caption = build_caption(image)
        log.info(f"Force-posting: {image.name}")
        success, post_url = self.post_image(image, caption)
        if success:
            mark_posted(tracker, image, post_url)
            save_tracker(tracker)
            log.info("Force post complete.")
            try:
                from engagement_bot import run_post_engagement
                run_post_engagement(self.cfg, caption)
            except Exception as exc:
                log.warning(f"Engagement session failed (non-fatal): {exc}")
        else:
            log.error("Force post failed.")

    # ─ Preview ───────────────────────────────────────────────────────────────

    def preview(self) -> None:
        """Print what the next post would look like without actually posting."""
        tracker = load_tracker()
        image   = pick_unposted_image(tracker)
        if image is None:
            print("No unposted images available.")
            return
        caption = build_caption(image)
        date_str = datetime.now().strftime("%Y-%m-%d")
        print(f"\n{'='*60}")
        print(f"Image    : {image.name}")
        print(f"Posted   : {daily_count(tracker, date_str)}/{DAILY_CAP} today")
        print(f"In window: {is_posting_window()}")
        print(f"Next slot: {next_posting_window()}")
        print(f"\n--- CAPTION PREVIEW ---\n")
        print(caption)
        print(f"{'='*60}\n")

    # ─ Status ────────────────────────────────────────────────────────────────

    def status(self) -> None:
        """Display current bot status."""
        tracker    = load_tracker()
        date_str   = datetime.now().strftime("%Y-%m-%d")
        total_imgs = len(list(SAVE_DIR.glob("*.png")))
        posted_ct  = len(tracker.get("posted", []))
        unposted   = total_imgs - posted_ct

        print(f"\n{'='*60}")
        print(f"  Instagram Bot Status")
        print(f"{'='*60}")
        print(f"  Total images in AI_Art : {total_imgs}")
        print(f"  Posted (all time)       : {posted_ct}")
        print(f"  Unposted                : {unposted}")
        print(f"  Posted today            : {daily_count(tracker, date_str)}/{DAILY_CAP}")
        print(f"  Inside posting window   : {is_posting_window()}")
        print(f"  Next posting window     : {next_posting_window()}")
        print(f"{'='*60}\n")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    import sys

    cfg = load_config()
    bot = InstagramBot(cfg)

    cmd = sys.argv[1] if len(sys.argv) > 1 else "post"

    if cmd == "post":
        bot.run_posting_cycle()

    elif cmd == "login":
        bot.setup_login()

    elif cmd == "force":
        bot.force_post()

    elif cmd == "preview":
        bot.preview()

    elif cmd == "status":
        bot.status()

    elif cmd == "learn":
        from engagement_learner import run_engagement_update
        run_engagement_update(cfg)

    elif cmd == "engage":
        # Manual engagement session using a test hashtag set
        caption_arg = sys.argv[2] if len(sys.argv) > 2 else (
            "#digitalart #surrealism #conceptart #fantasyart #landscapepainting"
        )
        from engagement_bot import run_post_engagement
        run_post_engagement(cfg, caption_arg)

    else:
        print(f"Unknown command: {cmd}")
        print("Usage: python instagram_bot.py [post|login|force|preview|status|learn|engage]")
        print()
        print("  post    — check window + daily cap, then post if due (scheduled mode)")
        print("  login   — open Instagram in bot Chrome profile for manual login")
        print("  force   — post next image immediately (bypass window/cap)")
        print("  preview — show what the next post would look like")
        print("  status  — show posting stats and current window info")
        print("  learn   — scrape engagement for all tracked posts, update weights")
        print("  engage  — run a manual engagement session (5–10 actions)")


if __name__ == "__main__":
    main()
