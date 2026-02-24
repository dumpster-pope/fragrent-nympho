"""
AI Art Bot - Multi-Source Browser Automation
Generates a 3-image series per hour by rotating across 7 AI image platforms:
  - Grok (grok.com)          — Aurora model, strong painterly/surreal
  - Leonardo.ai              — DreamShaper / Alchemy, rich fantasy/concept art
  - Adobe Firefly            — Firefly model, photorealistic / fine-art painterly
  - EaseMate.ai              — Nano Banana model, wild/unique/engaging outputs
  - ChatGPT (chatgpt.com)    — DALL-E 3 via GPT-4o, versatile and descriptive
  - Raphael.app              — fast high-quality generation, clean aesthetic
  - Google Gemini            — Imagen 3, photorealistic and painterly
Saves to Desktop/AI_Art/
Run once per hour via Windows Task Scheduler (see setup_scheduler.ps1)
"""

import os
import re
import json
import time
import base64
import random
import logging
from datetime import datetime
from pathlib import Path

import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

# ── Paths ─────────────────────────────────────────────────────────────────────

SAVE_DIR = Path(r"C:\Users\gageg\Desktop\AI_Art")
SAVE_DIR.mkdir(parents=True, exist_ok=True)

BOT_DIR  = Path(__file__).parent
LOG_DIR  = BOT_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

CONFIG_FILE     = BOT_DIR / "config.json"
SERIES_MANIFEST = BOT_DIR / "series_manifest.json"

# ── Source URLs ───────────────────────────────────────────────────────────────
GROK_URL      = "https://grok.com"
LEONARDO_URL  = "https://app.leonardo.ai/ai-generations"
FIREFLY_URL   = "https://firefly.adobe.com/generate/images"
EASEMATE_URL  = "https://www.easemate.ai/ai-image-generator"
CHATGPT_URL   = "https://chatgpt.com/"
RAPHAEL_URL   = "https://raphael.app/"
GEMINI_URL    = "https://gemini.google.com/"

# Equal weight rotation across all 7 sources (Bing removed — image quality too low)
SOURCES = ["grok", "leonardo", "firefly", "easemate", "chatgpt", "raphael", "gemini"]

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / f"bot_{datetime.now().strftime('%Y%m%d')}.log",
                            encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("art_bot")


# ── Prompt library ─────────────────────────────────────────────────────────────

SUBJECTS = [
    # Architectural / structural
    "an ancient lighthouse assembled from crystallised memories",
    "a cathedral sculpted entirely from frozen ocean waves",
    "a clockwork forest where every tree displays a different era",
    "a city suspended inside an enormous soap bubble over the void",
    "a vast library whose books drift like paper lanterns in still air",
    "a mechanical garden where iron flowers bloom only at midnight",
    "a staircase of glowing marble that spirals up into deep space",
    "a train station perched at the absolute edge of the known world",
    "a tower built from the fossilised bones of dead languages",
    "a bridge constructed from the interlocked silhouettes of dancers",
    "a monastery carved directly into the face of a thunderstorm",
    "a coral reef flowering through the skeletal ruins of a skyscraper",
    "a crumbling opera house slowly being swallowed by an ancient forest",
    "a cathedral made entirely of stacked hourglasses, each one running",
    "a vast greenhouse on a frozen planet, lit from within like a lantern",
    "an observatory whose telescope points inward instead of outward",
    # Figures / characters
    "a musician whose instrument releases clouds of coloured sound",
    "a painter whose every brushstroke becomes a living creature",
    "a clockmaker who repairs broken moments stolen from time itself",
    "a child who discovers a hidden door inside the cast shadow of a tree",
    "a scholar translating manuscripts written in light on cave walls",
    "a child chasing fireflies through the corridors of a palace of mirrors",
    "a samurai guarding the entrance to a portal made of cascading water",
    "a lone astronaut discovering a blooming greenhouse on a dead moon",
    "a giant sleeping under a hill, wildflowers growing from their hair",
    "an old cartographer drawing maps of places that do not exist yet",
    "a diver descending into a sea made entirely of liquid amber",
    "a weaver whose tapestry depicts the future as it is happening",
    "a street musician playing a song that makes memories visible",
    "a woman standing at the threshold of a door made of moving water",
    "a lighthouse keeper whose light guides ships between dimensions",
    # Creatures / nature
    "a luna moth the size of a city hovering over candlelit streets",
    "a colossal whale drifting through the clouds above a medieval city",
    "a phoenix being reborn from the smouldering ashes of a library",
    "a forest in which every shadow has a life entirely its own",
    "a desert made entirely of shattered antique mirrors",
    "a river of liquid starlight flowing uphill through stone channels",
    "an island that materialises only during total solar eclipses",
    "twin moons casting double shadows over an alien salt flat",
    "a flock of paper cranes migrating across a winter sky at dusk",
    "a forest of bioluminescent trees reflected in a perfectly still lake",
    "a meadow where every flower is a different extinct species",
    "a black fox with a tail made of northern lights crossing a frozen lake",
    # Market / social scenes
    "a bazaar where merchants sell bottled human emotions",
    "a marketplace where dreamers trade memories for new nightmares",
    "an underwater concert hall packed with singing deep-sea creatures",
    "an orchestra playing silently inside the eye of a hurricane",
    "a chess game played on a board the size of a continent by giants",
    "a carnival at the end of the universe, lit by dying stars",
    "a night market where every stall sells a different kind of silence",
    # Abandoned / post-natural
    "an abandoned generation ship consumed by bioluminescent moss",
    "a sunken cathedral glimpsed through fathoms of glowing green water",
    "a city reclaimed by vines and flowering trees after centuries of silence",
    "the ruins of a space station wrapped in morning glory and moss",
]

ENVIRONMENTS = [
    "bathed in the violet light of three simultaneous moons",
    "ringed by storm clouds crackling with chains of golden lightning",
    "emerging from dense, slow-moving fog at the edge of reality",
    "surrounded by millions of glowing fireflies frozen mid-flight",
    "reflected infinitely in a surface of still, perfectly black water",
    "half-reclaimed by encroaching jungle, lianas crawling everywhere",
    "at the precise moment of a blazing sunrise over an alien horizon",
    "frozen mid-collapse, every grain of dust suspended in raking light",
    "glimpsed through a curtain of falling cherry blossoms",
    "under a sky filled with enormous floating crystalline formations",
    "dissolving at the edges into cascades of geometric copper particles",
    "at the impossible border between a snowfield and a red desert",
    "submerged under a shallow layer of perfectly transparent water",
    "consumed by glowing bioluminescent vines at the last moment of dusk",
    "at the centre of a vast natural amphitheatre of wind-carved red stone",
    "surrounded by the remnants of an ancient bonfire, still faintly glowing",
    "at the edge of a sheer cliff overlooking an ocean of slow clouds",
    "inside a narrow canyon where the rock strata glow with mineral colour",
    "at the hour when daylight and darkness are perfectly balanced",
    "seen through rain-streaked glass, the outside world blurred and soft",
    "in the long blue shadow of a glacier at the end of summer",
    "lit from below by the glow of something vast and unseen beneath",
    "surrounded by a circle of ancient standing stones at the winter solstice",
    "at the point where a river disappears underground into total darkness",
    "caught in the moment before a storm breaks, the air charged and still",
]

STYLES = [
    # Painting traditions
    "in the style of a Studio Ghibli background painting, lush and atmospheric",
    "painted in heavy impasto oils with Baroque chiaroscuro and deep shadows",
    "rendered as a loose, luminous plein-air oil sketch",
    "in the style of the Hudson River School, vast and romantically lit",
    "painted in the manner of Caspar David Friedrich, solitary and sublime",
    "illustrated with the delicate watercolour washes of Arthur Rackham",
    "painted as a lush Pre-Raphaelite oil, jewel-toned and botanically precise",
    "in the nightmarish surrealist oil style of Beksinski, raw and haunting",
    "rendered as a richly layered Symbolist painting from the 1890s",
    "in the style of an N.C. Wyeth adventure illustration, dramatic and heroic",
    "painted as a Japanese nihonga on silk, gold leaf accents and soft gradients",
    # Print and illustration
    "composed as a hyperdetailed Gustave Dore steel engraving",
    "created in the exact ligne claire style of Jean Giraud (Moebius)",
    "illustrated as a luminous Art Nouveau poster by Alphonse Mucha",
    "depicted as a bold Soviet Constructivist propaganda lithograph",
    "rendered as a hand-pulled Japanese woodblock print, flat and graphic",
    "illustrated as a vintage 1970s science fiction paperback cover",
    "depicted as a hand-lettered psychedelic 1967 concert poster",
    "drawn in precise cross-hatched ink in the tradition of Albrecht Durer",
    "illustrated as a full-page Victorian natural history plate",
    "depicted as a hand-screen-printed two-colour risograph illustration",
    # Photography
    "shot on large-format film, rich tonal range and deep focus",
    "photographed on Kodachrome slide film, saturated and grain-heavy",
    "captured on medium-format black-and-white film with wide dynamic range",
    "shot on expired 35mm Portra film, soft colours and organic grain",
    "photographed with a long exposure at blue hour, light trails and stillness",
    "captured with a vintage Hasselblad on Tri-X pushed to 3200 ISO",
    "taken with a pinhole camera, soft and dreamlike with extreme depth of field",
    # Mixed / craft
    "rendered as a hand-painted theatrical backdrop from a 1920s opera",
    "illustrated as a richly detailed medieval illuminated manuscript",
    "depicted as a stained-glass window in the High Gothic tradition",
    "designed as a bold Art Deco travel poster from the 1930s",
]

MOODS = [
    "evoking profound melancholy and quiet, aching beauty",
    "radiating a sense of ancient, utterly forgotten wonder",
    "filled with electric tension just before a great transformation",
    "exuding warmth, safety, and last-light nostalgia",
    "charged with eerie cosmic dread and awe at infinite scale",
    "bursting with joyful, barely-contained chaos and colour",
    "heavy with the accumulated weight of lost civilisations",
    "alive with spiritual transcendence and inner light",
    "wrapped in mystery, secrets barely visible at the very edges",
    "serene yet subtly unsettling, like a half-remembered dream",
    "suffused with a bittersweet longing for something just out of reach",
    "humming with quiet magic, as if the world is holding its breath",
    "carrying the stillness and gravity of a place struck by lightning",
    "dreamlike and soft, like a memory seen through frosted glass",
    "raw and honest, stripped of sentimentality, deeply human",
]

COLOR_PALETTES = [
    "palette of deep indigo, burnt sienna, and pale gold",
    "muted palette of sage green, terracotta, and off-white",
    "high-contrast palette of pure black, crimson, and silver",
    "warm palette of amber, rust, and candlelight yellow",
    "cold palette of steel blue, grey-violet, and white",
    "earthy palette of ochre, umber, and dusty rose",
    "rich palette of emerald, midnight blue, and aged bronze",
    "washed-out palette of faded lavender, cream, and moss",
    "dramatic palette of charcoal, electric teal, and copper",
    "tender palette of blush, ivory, and pale celadon green",
    "stark palette of Payne's grey, raw umber, and chalk white",
    "jewel palette of deep burgundy, forest green, and old gold",
]

# Varied quality closers — no generic AI buzzwords
CLOSERS = [
    "Fine detail throughout, strong sense of depth and atmosphere.",
    "Confident brushwork, rich surface texture, compelling composition.",
    "Precise linework, balanced tonal values, arresting focal point.",
    "Loose gestural marks, luminous light, cohesive visual language.",
    "Meticulous rendering, expressive use of shadow, timeless feel.",
    "Bold shapes, layered colour, striking negative space.",
    "Intimate scale, careful observation, quiet emotional weight.",
    "Sweeping composition, dramatic contrast, immersive atmosphere.",
]

# History file — tracks recent subject+style pairs to avoid repeats
HISTORY_FILE = BOT_DIR / "prompt_history.json"
HISTORY_SIZE = 80  # remember last 80 combos (35 subjects x 33 styles = 1155 total)


def _load_history() -> list:
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f).get("used", [])
        except Exception:
            pass
    return []


def _save_history(used: list) -> None:
    trimmed = used[-HISTORY_SIZE:]
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump({"used": trimmed}, f, indent=2)


_DESCRIPTOR_PREFIXES = [
    r"^in the (exact |)style of\s+", r"^in the manner of\s+",
    r"^painted (in|as|on|with)\s+", r"^rendered as\s+",
    r"^illustrated as\s+", r"^depicted as\s+", r"^composed as\s+",
    r"^created in\s+", r"^designed as\s+", r"^shot on\s+",
    r"^photographed (on|with|using|at)\s+", r"^captured (on|with)\s+",
    r"^taken with\s+", r"^drawn in\s+", r"^evoking\s+",
    r"^radiating\s+", r"^filled with\s+", r"^bursting with\s+",
    r"^heavy with\s+", r"^alive with\s+", r"^wrapped in\s+",
    r"^charged with\s+", r"^exuding\s+", r"^suffused with\s+",
    r"^humming with\s+", r"^carrying\s+",
]


def _shorten_descriptor(text: str, max_len: int = 45) -> str:
    """Strip common lead-in phrases and truncate at first comma for clean caption lines."""
    for p in _DESCRIPTOR_PREFIXES:
        text = re.sub(p, "", text, flags=re.IGNORECASE).strip()
    first_clause = re.split(r"[,.]", text)[0].strip()[:max_len]
    return first_clause[0].upper() + first_clause[1:] if first_clause else text[:max_len]


def _weighted_choice(items: list, weights: list | None) -> str:
    """Weighted random selection. Falls back to uniform if weights absent/mismatched."""
    if not weights or len(weights) != len(items):
        return random.choice(items)
    total = sum(weights)
    if total <= 0:
        return random.choice(items)
    r = random.uniform(0, total)
    cumulative = 0.0
    for item, w in zip(items, weights):
        cumulative += w
        if r <= cumulative:
            return item
    return items[-1]


def _build_variation_components(subject: str, env: str, n: int) -> list[dict]:
    """
    Generate N component dicts sharing the same subject+env, each with a unique
    style and mood (no repeats within a series). Records each in prompt history.
    """
    weights: dict = {}
    try:
        import engagement_learner as _el
        _data = _el.load_engagement_data()
        weights = _el.get_all_weights(_data, {
            "style":   STYLES,
            "mood":    MOODS,
            "palette": COLOR_PALETTES,
            "closer":  CLOSERS,
        })
    except Exception:
        pass

    history = _load_history()
    used_styles: set = set()
    used_moods:  set = set()
    variations:  list = []

    for _ in range(n):
        pool_s = [s for s in STYLES if s not in used_styles] or STYLES
        w_s    = [weights.get("style", [1.0] * len(STYLES))[STYLES.index(s)]
                  if s in STYLES else 1.0 for s in pool_s]
        style  = _weighted_choice(pool_s, w_s)
        used_styles.add(style)

        pool_m = [m for m in MOODS if m not in used_moods] or MOODS
        w_m    = [weights.get("mood", [1.0] * len(MOODS))[MOODS.index(m)]
                  if m in MOODS else 1.0 for m in pool_m]
        mood   = _weighted_choice(pool_m, w_m)
        used_moods.add(mood)

        palette = _weighted_choice(COLOR_PALETTES, weights.get("palette"))
        closer  = _weighted_choice(CLOSERS,        weights.get("closer"))

        variations.append({
            "subject":     subject,
            "environment": env,
            "style":       style,
            "mood":        mood,
            "palette":     palette,
            "closer":      closer,
        })
        history.append([subject[:40], style[:40]])

    _save_history(history)
    return variations


def _build_variation_prompt(c: dict) -> str:
    """Assemble the full prompt string from a variation component dict."""
    return (
        f"{c['subject'].capitalize()}, {c['environment']}. "
        f"{c['style'].capitalize()}, {c['palette']}. "
        f"{c['mood'].capitalize()}. {c['closer']}"
    )


def build_prompt() -> tuple:
    """
    Build a unique prompt. Tracks recently used subject+style combinations
    and avoids repeating them until the full library has been cycled through.

    Returns (prompt_str, components_dict) where components_dict maps each
    prompt component key to the exact value chosen (for engagement learning).
    """
    # ── Load engagement weights (graceful fallback on any error) ──────────
    weights: dict = {}
    try:
        import engagement_learner as _el
        _data = _el.load_engagement_data()
        n_posts = len(_data.get("posts", {}))
        weights = _el.get_all_weights(_data, {
            "subject":     SUBJECTS,
            "environment": ENVIRONMENTS,
            "style":       STYLES,
            "mood":        MOODS,
            "palette":     COLOR_PALETTES,
            "closer":      CLOSERS,
        })
        if n_posts >= _el.MIN_POSTS_FOR_LEARNING:
            log.info(f"[engagement] loaded weights for {n_posts} posts")
    except Exception as exc:
        log.debug(f"[engagement] weight load skipped: {exc}")

    history  = _load_history()
    used_set = set(tuple(x) for x in history)

    # Try up to 30 times to find a fresh subject+style pair
    subject = style = env = mood = palette = closer = ""
    for _ in range(30):
        subject = _weighted_choice(SUBJECTS,      weights.get("subject"))
        style   = _weighted_choice(STYLES,        weights.get("style"))
        key     = (subject[:40], style[:40])
        if key not in used_set:
            break

    env     = _weighted_choice(ENVIRONMENTS,  weights.get("environment"))
    mood    = _weighted_choice(MOODS,         weights.get("mood"))
    palette = _weighted_choice(COLOR_PALETTES, weights.get("palette"))
    closer  = _weighted_choice(CLOSERS,       weights.get("closer"))

    # Record this combination
    history.append([subject[:40], style[:40]])
    _save_history(history)

    prompt_str = (
        f"{subject.capitalize()}, {env}. "
        f"{style.capitalize()}, {palette}. "
        f"{mood.capitalize()}. {closer}"
    )
    components = {
        "subject":     subject,
        "environment": env,
        "style":       style,
        "mood":        mood,
        "palette":     palette,
        "closer":      closer,
    }
    return prompt_str, components


# ── Config ────────────────────────────────────────────────────────────────────

def load_config() -> dict:
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    cfg = {
        "chrome_profile_path": "",
        "instagram_username": "",
        "instagram_password": "",
        "last_run": None,
    }
    save_config(cfg)
    return cfg


def save_config(cfg: dict) -> None:
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4)


# ── Selenium helpers ──────────────────────────────────────────────────────────

def _clear_profile_locks(profile_dir: str) -> None:
    """Recursively remove every Chrome lock file in the profile tree."""
    root = Path(profile_dir)
    for pattern in ("**/LOCK", "**/SingletonLock", "**/SingletonCookie", "**/SingletonSocket"):
        for p in root.rglob(pattern.replace("**/", "")):
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
    else:
        log.info("No Chrome profile set — browser will open a fresh session")

    # Anti-detection
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    opts.add_argument("--window-size=1400,960")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    # Stability — disable extensions so they don't crash the session
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
    """Type text with small random pauses to look human."""
    for ch in text:
        element.send_keys(ch)
        if random.random() < 0.04:
            time.sleep(random.uniform(0.04, 0.18))


def find_first(driver, selectors: list[tuple], timeout: int = 15):
    """Try multiple (By, selector) pairs and return the first element found."""
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


# ── Image download ────────────────────────────────────────────────────────────

def download_image(driver, img_url: str, prompt: str,
                   referer: str = GROK_URL, source_name: str = "grok",
                   components: dict | None = None) -> str | None:
    """Download image (HTTP or blob:) and save to SAVE_DIR. Returns filepath."""
    now  = datetime.now()
    slug = re.sub(r"\W+", "_", prompt[:45]).strip("_")
    if components and components.get("series_id"):
        filename = f"{components['series_id']}_S{components.get('series_idx', 1)}_{slug}.png"
    else:
        filename = f"{now.strftime('%Y%m%d_%H%M%S')}_{slug}.png"
    filepath = SAVE_DIR / filename

    try:
        if img_url.startswith("blob:"):
            log.info("Extracting blob image via canvas…")
            b64 = driver.execute_script(
                """
                var img = document.querySelector("img[src='" + arguments[0] + "']");
                if (!img) return null;
                var c = document.createElement('canvas');
                c.width  = img.naturalWidth  || 1024;
                c.height = img.naturalHeight || 1024;
                c.getContext('2d').drawImage(img, 0, 0);
                return c.toDataURL('image/png').split(',')[1];
                """,
                img_url,
            )
            if not b64:
                log.error("Canvas extraction returned nothing")
                return None
            with open(filepath, "wb") as f:
                f.write(base64.b64decode(b64))

        else:
            # Transfer cookies from Selenium session so auth'd CDN URLs work
            session = requests.Session()
            for ck in driver.get_cookies():
                session.cookies.set(ck["name"], ck["value"])
            ua = driver.execute_script("return navigator.userAgent;")
            resp = session.get(
                img_url,
                headers={"User-Agent": ua, "Referer": referer},
                timeout=30,
            )
            resp.raise_for_status()
            with open(filepath, "wb") as f:
                f.write(resp.content)
            log.info(f"Downloaded {len(resp.content)//1024} KB")

        # Sanity-check: skip tiny/corrupt files
        size_kb = filepath.stat().st_size // 1024
        if size_kb < 30:
            log.warning(f"File too small ({size_kb} KB) — likely not a real image, discarding")
            filepath.unlink(missing_ok=True)
            return None

        log.info(f"Image saved → {filepath}")
        _save_sidecar(filepath, prompt, img_url, source_name, components)
        return str(filepath)

    except Exception as exc:
        log.error(f"Download failed: {exc}")
        return None


def _save_sidecar(filepath, prompt: str, url: str, source_name: str = "grok",
                  components: dict | None = None) -> None:
    meta = {
        "generated_at": datetime.now().isoformat(),
        "prompt": prompt,
        "source": url[:200],
        "source_name": source_name,
        "file": str(filepath),
    }
    if components:
        meta["components"] = components
    sidecar = Path(str(filepath).replace(".png", "_meta.json"))
    with open(sidecar, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)


# ── Core generation logic ─────────────────────────────────────────────────────

def generate_image(prompt: str, cfg: dict, components: dict | None = None) -> str | None:
    """
    Open Grok in Chrome, submit the image-generation prompt,
    wait for the result image, download it. Returns saved filepath or None.
    """
    driver = make_driver(cfg)
    try:
        log.info("Loading grok.com…")
        driver.get(GROK_URL)
        time.sleep(4)

        # ── 1. Find the text input ─────────────────────────────────────────
        input_el = find_first(driver, [
            (By.CSS_SELECTOR, "textarea"),
            (By.CSS_SELECTOR, "div[contenteditable='true']"),
            (By.XPATH, "//textarea[@placeholder]"),
            (By.CSS_SELECTOR, "div[role='textbox']"),
        ])
        if input_el is None:
            log.error("Could not find chat input — is the page loaded correctly?")
            _screenshot(driver, "no_input")
            return None

        # ── 2. Click the image-generation mode button if present ───────────
        img_mode_btns = [
            (By.XPATH, "//button[contains(translate(., 'IMAGE', 'image'), 'image')]"),
            (By.CSS_SELECTOR, "button[aria-label*='mage']"),
            (By.XPATH, "//*[contains(@aria-label,'Generate image') or contains(@aria-label,'Image')]"),
            (By.CSS_SELECTOR, "[data-testid*='image']"),
        ]
        for by, sel in img_mode_btns:
            try:
                btn = driver.find_element(by, sel)
                driver.execute_script("arguments[0].click();", btn)
                log.info(f"Clicked image mode: {sel}")
                time.sleep(1.5)
                break
            except Exception:
                pass

        # ── 3. Type the prompt ─────────────────────────────────────────────
        input_el.click()
        time.sleep(0.5)
        try:
            input_el.clear()
        except Exception:
            pass
        slow_type(input_el, prompt)
        time.sleep(1)

        # ── 4. Submit ──────────────────────────────────────────────────────
        submit_el = find_first(driver, [
            (By.CSS_SELECTOR, "button[type='submit']"),
            (By.XPATH, "//button[@aria-label='Submit message']"),
            (By.XPATH, "//button[@aria-label='Send message']"),
            (By.CSS_SELECTOR, "[data-testid='send-button']"),
        ], timeout=5)

        if submit_el:
            driver.execute_script("arguments[0].click();", submit_el)
            log.info("Submitted via button")
        else:
            input_el.send_keys(Keys.RETURN)
            log.info("Submitted via Enter")

        # ── 5. Wait for the generated image ───────────────────────────────
        # Give Grok at least 15 s to start generating before we start polling
        log.info("Waiting for Grok to generate image (up to 180 s)…")
        time.sleep(15)

        start_time = time.time()
        deadline = start_time + 165  # 15 + 165 = 180 s total
        found_url: str | None = None

        while time.time() < deadline:
            time.sleep(3)
            try:
                # Use JS to find all large images on the page at once
                result = driver.execute_script("""
                    var candidates = [];
                    var imgs = document.querySelectorAll('img');
                    for (var i = 0; i < imgs.length; i++) {
                        var img = imgs[i];
                        var src = img.src || '';
                        var w = img.naturalWidth;
                        var h = img.naturalHeight;
                        if (w >= 512 && h >= 512) {
                            candidates.push({src: src, w: w, h: h});
                        }
                    }
                    return candidates;
                """)

                if result:
                    for item in result:
                        src = item.get('src', '')
                        w   = item.get('w', 0)
                        h   = item.get('h', 0)
                        # Skip profile pictures (usually square, hosted on pbs.twimg.com profile paths)
                        if 'profile_images' in src:
                            continue
                        # Prefer known Grok image CDN domains
                        if any(k in src for k in ('grokusercontent', 'assets.grok.com', 'blob:', 'pbs.twimg')):
                            found_url = src
                            log.info(f"Generated image found ({w}x{h}): {src[:100]}")
                            break
                        # Fallback: any 512+ image that isn't a profile pic
                        if w >= 512:
                            found_url = src
                            log.info(f"Large image found ({w}x{h}): {src[:100]}")

                if found_url:
                    break

            except Exception as exc:
                log.debug(f"Poll error: {exc}")

            elapsed = int(time.time() - start_time) + 15
            if elapsed % 30 == 0:
                log.info(f"  still waiting… ({elapsed}s)")
                _screenshot(driver, f"progress_{elapsed}s")

        if not found_url:
            log.error("No image found within 120 s")
            _screenshot(driver, "timeout")
            return None

        # ── 6. Download ────────────────────────────────────────────────────
        return download_image(driver, found_url, prompt, components=components)

    except Exception as exc:
        log.exception(f"Unexpected error: {exc}")
        _screenshot(driver, "exception")
        return None

    finally:
        try:
            driver.quit()
        except Exception:
            pass


# ── Shared image-detection helper ─────────────────────────────────────────────

def _wait_for_large_image(driver, timeout: int, cdn_hints: list) -> str | None:
    """Poll for any 512px+ image matching a CDN hint, fall back to any large img."""
    start = time.time()
    while time.time() - start < timeout:
        result = driver.execute_script("""
            var hints = arguments[0];
            var imgs  = document.querySelectorAll('img');
            var fallback = null;
            for (var i = 0; i < imgs.length; i++) {
                var src = imgs[i].src || '';
                var w   = imgs[i].naturalWidth;
                var h   = imgs[i].naturalHeight;
                if (w < 512 || h < 512) continue;
                if (/profile|avatar|logo|icon|spinner/i.test(src)) continue;
                for (var j = 0; j < hints.length; j++) {
                    if (src.indexOf(hints[j]) !== -1) return {src: src, w: w, h: h};
                }
                if (!fallback || w > fallback.w) fallback = {src: src, w: w, h: h};
            }
            return fallback;
        """, cdn_hints)
        if result:
            log.info(f"  image detected ({result['w']}x{result['h']}): {result['src'][:80]}")
            return result["src"]
        time.sleep(4)
    return None


# ── Leonardo.ai generator ─────────────────────────────────────────────────────

def generate_via_leonardo(driver, prompt: str) -> str | None:
    """Submit a prompt to Leonardo.ai and return the generated image URL."""
    log.info("Leonardo.ai: loading AI Generations page…")
    driver.get(LEONARDO_URL)
    time.sleep(8)  # Heavy React app

    textarea = find_first(driver, [
        (By.CSS_SELECTOR, "textarea[placeholder*='Type a prompt' i]"),
        (By.CSS_SELECTOR, "textarea[placeholder*='prompt' i]"),
        (By.CSS_SELECTOR, "textarea"),
    ], timeout=20)
    if not textarea:
        log.error("Leonardo: prompt textarea not found")
        return None

    textarea.click()
    time.sleep(0.5)
    try:
        textarea.clear()
    except Exception:
        pass
    slow_type(textarea, prompt[:480])
    time.sleep(1)

    # ── Set image count to 2 to preserve daily tokens ─────────────────────
    try:
        count_btn = driver.find_element(
            By.XPATH,
            "(//label[contains(translate(.,'NUMBER OF IMAGES','number of images'),'number of images')]"
            "/following::button[normalize-space()='2']"
            "| //button[@data-testid='image-count-2']"
            "| //button[@aria-label='2 images'])[1]",
        )
        driver.execute_script("arguments[0].click();", count_btn)
        log.info("Leonardo: image count set to 2")
        time.sleep(0.5)
    except Exception:
        log.debug("Leonardo: image count selector not found — using default")

    gen_btn = find_first(driver, [
        (By.XPATH, "//button[normalize-space()='Generate']"),
        (By.CSS_SELECTOR, "button[aria-label*='Generate' i]"),
        (By.XPATH, "//button[contains(@data-testid,'generate')]"),
    ], timeout=12)
    if not gen_btn:
        log.error("Leonardo: Generate button not found")
        return None

    driver.execute_script("arguments[0].click();", gen_btn)
    log.info("Leonardo: generating… (up to 120 s)")
    time.sleep(12)

    return _wait_for_large_image(driver, timeout=108, cdn_hints=[
        "cdn.leonardo.ai", "production.leonardo.ai", "storage.googleapis.com",
    ])


# ── Adobe Firefly generator ───────────────────────────────────────────────────

def generate_via_firefly(driver, prompt: str) -> str | None:
    """Submit a prompt to Adobe Firefly and return the generated image URL."""
    log.info("Adobe Firefly: loading…")
    driver.get(FIREFLY_URL)
    time.sleep(6)

    prompt_el = find_first(driver, [
        (By.CSS_SELECTOR, "textarea[placeholder*='Describe' i]"),
        (By.CSS_SELECTOR, "textarea[placeholder*='image' i]"),
        (By.CSS_SELECTOR, "textarea"),
        (By.CSS_SELECTOR, "div[contenteditable='true']"),
    ], timeout=20)
    if not prompt_el:
        log.error("Firefly: prompt input not found")
        return None

    prompt_el.click()
    time.sleep(0.5)
    try:
        prompt_el.clear()
    except Exception:
        pass
    slow_type(prompt_el, prompt[:480])
    time.sleep(1)

    gen_btn = find_first(driver, [
        (By.XPATH, "//button[normalize-space()='Generate']"),
        (By.CSS_SELECTOR, "button[data-testid*='generate' i]"),
        (By.XPATH, "//button[contains(@aria-label,'Generate')]"),
    ], timeout=12)
    if not gen_btn:
        log.error("Firefly: Generate button not found")
        return None

    driver.execute_script("arguments[0].click();", gen_btn)
    log.info("Firefly: generating… (up to 90 s)")
    time.sleep(10)

    return _wait_for_large_image(driver, timeout=80, cdn_hints=[
        "firefly.adobe.com", "ffoutput", "adobeproductimages", "firefly-prod",
    ])


# ── Bing Image Creator (DALL-E 3) generator ───────────────────────────────────

def generate_via_bing(driver, prompt: str) -> str | None:
    """Submit a prompt to Bing Image Creator (DALL-E 3) and return the image URL."""
    log.info("Bing Image Creator: loading…")
    driver.get(BING_URL)
    time.sleep(4)

    prompt_el = find_first(driver, [
        (By.CSS_SELECTOR, "#sb_form_q"),
        (By.CSS_SELECTOR, "input.b_searchbox"),
        (By.CSS_SELECTOR, "textarea.b_searchbox"),
        (By.CSS_SELECTOR, "input[name='q']"),
    ], timeout=15)
    if not prompt_el:
        log.error("Bing: prompt input not found")
        return None

    prompt_el.click()
    time.sleep(0.3)
    prompt_el.clear()
    prompt_el.send_keys(prompt[:480])
    time.sleep(1)

    # Try the dedicated Create button first; fall back to Enter
    create_btn = find_first(driver, [
        (By.CSS_SELECTOR, "#create_btn_c"),
        (By.CSS_SELECTOR, "input.create_btn"),
        (By.XPATH, "//input[@value='Create' or @value='Generate']"),
        (By.XPATH, "//button[normalize-space()='Create']"),
    ], timeout=8)
    if create_btn:
        driver.execute_script("arguments[0].click();", create_btn)
    else:
        prompt_el.send_keys(Keys.RETURN)

    log.info("Bing: generating… (up to 90 s, includes page redirect)")
    time.sleep(14)

    return _wait_for_large_image(driver, timeout=76, cdn_hints=[
        "th.bing.com", "tse1.mm.bing.net", "tse2.mm.bing.net", "blob:",
    ])


# ── EaseMate.ai generator (Nano Banana model) ─────────────────────────────────

def generate_via_easemate(driver, prompt: str) -> str | None:
    """Submit a prompt to EaseMate.ai using the Nano Banana model and return the image URL."""
    log.info("EaseMate.ai: loading AI image generator…")
    driver.get(EASEMATE_URL)
    time.sleep(6)

    # ── 1. Switch to Text-to-Image tab if tabs are present ────────────────
    for by, sel in [
        (By.XPATH, "//button[contains(translate(.,'TEXT TO IMAGE','text to image'),'text to image')]"),
        (By.XPATH, "//div[contains(translate(.,'TEXT TO IMAGE','text to image'),'text to image')]"),
        (By.CSS_SELECTOR, "[data-tab='text']"),
    ]:
        try:
            tab = driver.find_element(by, sel)
            driver.execute_script("arguments[0].click();", tab)
            log.info("EaseMate: switched to Text to Image tab")
            time.sleep(2)
            break
        except Exception:
            pass

    # ── 2. Select the Nano Banana model ───────────────────────────────────
    model_selected = False

    # First try: click a visible model selector button / dropdown trigger
    model_trigger_selectors = [
        (By.XPATH, "//button[contains(translate(.,'MODEL','model'),'model')]"),
        (By.CSS_SELECTOR, "[class*='model'][class*='select'], [class*='model-selector']"),
        (By.CSS_SELECTOR, "select[name*='model' i], select[id*='model' i]"),
        (By.XPATH, "//*[contains(@aria-label,'model') or contains(@placeholder,'model')]"),
        (By.XPATH, "//button[contains(.,'GPT') or contains(.,'Model') or contains(.,'model')]"),
        (By.CSS_SELECTOR, "[class*='dropdown'][class*='model'], [data-type='model']"),
    ]

    for by, sel in model_trigger_selectors:
        try:
            el = driver.find_element(by, sel)
            driver.execute_script("arguments[0].click();", el)
            log.info(f"EaseMate: opened model selector ({sel})")
            time.sleep(2)

            # Look for Nano Banana option in dropdown
            nano_option = find_first(driver, [
                (By.XPATH, "//*[contains(translate(.,'NANO BANANA','nano banana'),'nano banana')]"),
                (By.XPATH, "//li[contains(translate(.,'NANO BANANA','nano banana'),'nano banana')]"),
                (By.XPATH, "//option[contains(translate(.,'NANO BANANA','nano banana'),'nano banana')]"),
                (By.CSS_SELECTOR, "[data-value*='nano' i], [data-value*='banana' i]"),
            ], timeout=5)

            if nano_option:
                driver.execute_script("arguments[0].click();", nano_option)
                log.info("EaseMate: selected Nano Banana model")
                time.sleep(1.5)
                model_selected = True
                break
        except Exception:
            pass

    # Second try: if it's a <select> element, set value directly
    if not model_selected:
        try:
            from selenium.webdriver.support.ui import Select
            selects = driver.find_elements(By.CSS_SELECTOR, "select")
            for sel_el in selects:
                opts = sel_el.find_elements(By.TAG_NAME, "option")
                for opt in opts:
                    if "nano" in opt.text.lower() or "banana" in opt.text.lower():
                        Select(sel_el).select_by_visible_text(opt.text)
                        log.info(f"EaseMate: selected Nano Banana via <select> ({opt.text})")
                        time.sleep(1)
                        model_selected = True
                        break
                if model_selected:
                    break
        except Exception:
            pass

    # Third try: JS-click any element whose text contains nano/banana
    if not model_selected:
        try:
            found = driver.execute_script("""
                var els = document.querySelectorAll('*');
                for (var i = 0; i < els.length; i++) {
                    var t = els[i].textContent.toLowerCase();
                    if (t.includes('nano banana') || (t.includes('nano') && t.includes('banana'))) {
                        return els[i];
                    }
                }
                return null;
            """)
            if found:
                driver.execute_script("arguments[0].click();", found)
                log.info("EaseMate: selected Nano Banana via JS text search")
                time.sleep(1.5)
                model_selected = True
        except Exception:
            pass

    if not model_selected:
        log.warning("EaseMate: could not find Nano Banana model — proceeding with current model")

    # ── 3. Enter the prompt ────────────────────────────────────────────────
    prompt_el = find_first(driver, [
        (By.CSS_SELECTOR, "textarea[placeholder*='Prompt' i]"),
        (By.CSS_SELECTOR, "textarea[placeholder*='Describe' i]"),
        (By.CSS_SELECTOR, "textarea[placeholder*='Enter' i]"),
        (By.CSS_SELECTOR, "textarea"),
        (By.CSS_SELECTOR, "div[contenteditable='true']"),
        (By.CSS_SELECTOR, "input[placeholder*='prompt' i]"),
    ], timeout=15)

    if not prompt_el:
        log.error("EaseMate: prompt input not found")
        _screenshot(driver, "easemate_no_input")
        return None

    prompt_el.click()
    time.sleep(0.5)
    try:
        prompt_el.clear()
    except Exception:
        pass
    slow_type(prompt_el, prompt[:480])
    time.sleep(1)

    # ── 4. Click Generate ──────────────────────────────────────────────────
    gen_btn = find_first(driver, [
        (By.XPATH, "//button[normalize-space()='Generate']"),
        (By.XPATH, "//button[contains(normalize-space(),'Generate')]"),
        (By.CSS_SELECTOR, "button[type='submit']"),
        (By.CSS_SELECTOR, "[class*='generate'][class*='btn'], [class*='btn'][class*='generate']"),
        (By.CSS_SELECTOR, "button[aria-label*='Generate' i]"),
    ], timeout=12)

    if not gen_btn:
        log.error("EaseMate: Generate button not found")
        _screenshot(driver, "easemate_no_button")
        return None

    driver.execute_script("arguments[0].click();", gen_btn)
    log.info("EaseMate: generating… (up to 120 s)")
    time.sleep(12)

    # ── 5. Wait for the generated image ───────────────────────────────────
    return _wait_for_large_image(driver, timeout=108, cdn_hints=[
        "easemate.ai", "easemate", "cdn.", "storage.", "output", "result",
    ])


# ── ChatGPT / DALL-E 3 generator ──────────────────────────────────────────────

def generate_via_chatgpt(driver, prompt: str) -> str | None:
    """Submit a prompt to ChatGPT and return the DALL-E 3 generated image URL."""
    log.info("ChatGPT: loading…")
    driver.get(CHATGPT_URL)
    time.sleep(6)

    # ── 1. Find the chat input ─────────────────────────────────────────────
    prompt_el = find_first(driver, [
        (By.CSS_SELECTOR, "#prompt-textarea"),
        (By.CSS_SELECTOR, "div[contenteditable='true'][data-lexical-editor]"),
        (By.CSS_SELECTOR, "div[contenteditable='true']"),
        (By.CSS_SELECTOR, "textarea[placeholder*='Message' i]"),
    ], timeout=20)
    if not prompt_el:
        log.error("ChatGPT: prompt input not found")
        return None

    # ── 2. Type the prompt, prefixed to trigger DALL-E image generation ────
    prompt_el.click()
    time.sleep(0.5)
    slow_type(prompt_el, f"Generate an image: {prompt[:450]}")
    time.sleep(1)

    # ── 3. Submit ──────────────────────────────────────────────────────────
    submit_el = find_first(driver, [
        (By.CSS_SELECTOR, "button[data-testid='send-button']"),
        (By.CSS_SELECTOR, "button[aria-label='Send prompt']"),
        (By.XPATH, "//button[@aria-label='Send message']"),
    ], timeout=5)
    if submit_el:
        driver.execute_script("arguments[0].click();", submit_el)
    else:
        prompt_el.send_keys(Keys.RETURN)
    log.info("ChatGPT: generating… (up to 120 s)")
    time.sleep(15)

    return _wait_for_large_image(driver, timeout=105, cdn_hints=[
        "files.oaiusercontent.com", "oaidalleapiprodscus", "oaidalleus",
    ])


# ── Raphael.app generator ─────────────────────────────────────────────────────

def generate_via_raphael(driver, prompt: str) -> str | None:
    """Submit a prompt to Raphael.app and return the generated image URL."""
    log.info("Raphael: loading…")
    driver.get(RAPHAEL_URL)
    time.sleep(5)

    # ── 1. Find the prompt input ───────────────────────────────────────────
    prompt_el = find_first(driver, [
        (By.CSS_SELECTOR, "textarea[placeholder*='Describe' i]"),
        (By.CSS_SELECTOR, "textarea[placeholder*='Enter' i]"),
        (By.CSS_SELECTOR, "textarea[placeholder*='prompt' i]"),
        (By.CSS_SELECTOR, "input[placeholder*='prompt' i]"),
        (By.CSS_SELECTOR, "textarea"),
    ], timeout=15)
    if not prompt_el:
        log.error("Raphael: prompt input not found")
        return None

    prompt_el.click()
    time.sleep(0.5)
    try:
        prompt_el.clear()
    except Exception:
        pass
    slow_type(prompt_el, prompt[:480])
    time.sleep(1)

    # ── 2. Click Generate ──────────────────────────────────────────────────
    gen_btn = find_first(driver, [
        (By.XPATH, "//button[normalize-space()='Generate']"),
        (By.XPATH, "//button[contains(normalize-space(),'Generate')]"),
        (By.CSS_SELECTOR, "button[type='submit']"),
        (By.CSS_SELECTOR, "[class*='generate'][class*='btn'], [class*='btn'][class*='generate']"),
    ], timeout=12)
    if not gen_btn:
        log.error("Raphael: Generate button not found")
        return None

    driver.execute_script("arguments[0].click();", gen_btn)
    log.info("Raphael: generating… (up to 120 s)")
    time.sleep(10)

    return _wait_for_large_image(driver, timeout=110, cdn_hints=[
        "raphael.app", "cdn.raphael", "storage", "output", "result",
    ])


# ── Google Gemini / Imagen generator ─────────────────────────────────────────

def generate_via_gemini(driver, prompt: str) -> str | None:
    """Submit a prompt to Google Gemini and return the Imagen-generated image URL."""
    log.info("Gemini: loading…")
    driver.get(GEMINI_URL)
    time.sleep(6)

    # ── 1. Find the chat input ─────────────────────────────────────────────
    prompt_el = find_first(driver, [
        (By.CSS_SELECTOR, "div[contenteditable='true']"),
        (By.CSS_SELECTOR, "rich-textarea div[contenteditable]"),
        (By.CSS_SELECTOR, "textarea"),
        (By.XPATH, "//div[@role='textbox']"),
    ], timeout=20)
    if not prompt_el:
        log.error("Gemini: prompt input not found")
        return None

    # ── 2. Type the prompt ─────────────────────────────────────────────────
    prompt_el.click()
    time.sleep(0.5)
    slow_type(prompt_el, f"Create an image: {prompt[:450]}")
    time.sleep(1)

    # ── 3. Submit ──────────────────────────────────────────────────────────
    submit_el = find_first(driver, [
        (By.CSS_SELECTOR, "button[aria-label='Send message']"),
        (By.CSS_SELECTOR, "button.send-button"),
        (By.XPATH, "//button[contains(@aria-label,'Send')]"),
        (By.XPATH, "//mat-icon[text()='send']/parent::button"),
    ], timeout=5)
    if submit_el:
        driver.execute_script("arguments[0].click();", submit_el)
    else:
        prompt_el.send_keys(Keys.RETURN)
    log.info("Gemini: generating… (up to 120 s)")
    time.sleep(15)

    return _wait_for_large_image(driver, timeout=105, cdn_hints=[
        "googleusercontent.com", "lh3.googleusercontent", "generativelanguage",
        "gemini", "image-generation",
    ])


# ── Source dispatch table ─────────────────────────────────────────────────────

_GENERATOR_FNS = {
    "grok":     None,                   # handled inside generate_image() directly
    "leonardo": generate_via_leonardo,
    "firefly":  generate_via_firefly,
    "easemate": generate_via_easemate,
    "chatgpt":  generate_via_chatgpt,
    "raphael":  generate_via_raphael,
    "gemini":   generate_via_gemini,
}

_SOURCE_URLS = {
    "grok":     GROK_URL,
    "leonardo": LEONARDO_URL,
    "firefly":  FIREFLY_URL,
    "easemate": EASEMATE_URL,
    "chatgpt":  CHATGPT_URL,
    "raphael":  RAPHAEL_URL,
    "gemini":   GEMINI_URL,
}


def _screenshot(driver, label: str) -> None:
    try:
        driver.save_screenshot(
            str(LOG_DIR / f"{label}_{datetime.now().strftime('%H%M%S')}.png")
        )
    except Exception:
        pass


# ── Entry points ───────────────────────────────────────────────────────────────

def _load_series_manifest() -> dict:
    if SERIES_MANIFEST.exists():
        try:
            with open(SERIES_MANIFEST, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"series": {}}


def _save_series_manifest(manifest: dict) -> None:
    with open(SERIES_MANIFEST, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)


def run_series(n: int = 3) -> list[str]:
    """
    Generate N variations of the same base subject/environment, each through a
    different AI tool. Saves a series_manifest.json entry with posted=false.
    Returns list of saved filepaths (may be fewer than N if some tools fail).
    """
    log.info("=" * 60)
    log.info(f"AI Art Bot — Series Mode ({n} variations) — {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    cfg = load_config()

    # 1. Load engagement weights for subject + environment selection
    weights: dict = {}
    try:
        import engagement_learner as _el
        _data = _el.load_engagement_data()
        weights = _el.get_all_weights(_data, {
            "subject":     SUBJECTS,
            "environment": ENVIRONMENTS,
        })
    except Exception as exc:
        log.debug(f"[engagement] weight load skipped: {exc}")

    # 2. Pick shared base subject + environment
    base_subject = _weighted_choice(SUBJECTS,      weights.get("subject"))
    base_env     = _weighted_choice(ENVIRONMENTS,  weights.get("environment"))
    log.info(f"Base subject    : {base_subject}")
    log.info(f"Base environment: {base_env}")

    # 3. Build N variation components (unique style+mood per variation)
    variations = _build_variation_components(base_subject, base_env, n)

    # 4. Assign a different tool to each variation
    series_id      = datetime.now().strftime("%Y%m%d_%H%M%S")
    shuffled       = random.sample(SOURCES, len(SOURCES))
    assigned_tools = shuffled[:n]
    log.info(f"Series ID: {series_id} — tools: {assigned_tools}")

    results: list[str] = []

    for idx, (comps, tool) in enumerate(zip(variations, assigned_tools), start=1):
        # 5. Inject series metadata
        comps["series_id"]    = series_id
        comps["series_idx"]   = idx
        comps["series_total"] = n

        prompt = _build_variation_prompt(comps)
        log.info(f"  [{idx}/{n}] {tool.upper()}: {prompt[:80]}")

        filepath: str | None = None
        try:
            if tool == "grok":
                filepath = generate_image(prompt, cfg, components=comps)
            else:
                driver = make_driver(cfg)
                try:
                    url = _GENERATOR_FNS[tool](driver, prompt)
                    if url:
                        filepath = download_image(
                            driver, url, prompt,
                            referer=_SOURCE_URLS[tool],
                            source_name=tool,
                            components=comps,
                        )
                finally:
                    try:
                        driver.quit()
                    except Exception:
                        pass
        except Exception as exc:
            log.error(f"[{tool}] variation {idx} failed: {exc}")

        if filepath:
            log.info(f"  ✓ [{tool}] Saved → {filepath}")
            results.append(filepath)
        else:
            log.warning(f"  ✗ [{tool}] variation {idx} failed")

        # Brief pause between tool calls
        if idx < n:
            time.sleep(5)

    # 6. Save manifest entry if any images were generated
    if results:
        manifest = _load_series_manifest()
        manifest["series"][series_id] = {
            "files":               [Path(fp).name for fp in results],
            "base_subject":        base_subject,
            "base_env":            base_env,
            "variation_components": variations,
            "generated_at":        datetime.now().isoformat(),
            "posted":              False,
        }
        _save_series_manifest(manifest)
        log.info(f"Series manifest saved — {len(results)}/{n} images generated")
    else:
        log.error("✗ All variations failed this series run")

    # 7. Update config
    cfg["last_run"] = datetime.now().isoformat()
    save_config(cfg)

    # 8. Auto-post to Instagram immediately after saving
    if results:
        try:
            from instagram_bot import (
                InstagramBot, load_config as _ig_load_config,
                build_series_caption, pick_unposted_series,
                mark_series_posted, load_tracker,
            )
            ig_cfg         = _ig_load_config()
            series_result  = pick_unposted_series()
            if series_result:
                s_id, s_data, s_paths = series_result
                caption  = build_series_caption(s_data)
                tracker  = load_tracker()
                bot      = InstagramBot(ig_cfg)
                log.info(f"Auto-posting series {s_id} to Instagram…")
                success, post_url = bot.post_series([str(p) for p in s_paths], caption)
                if success:
                    mark_series_posted(s_id, [str(p) for p in s_paths], tracker, post_url)
                    log.info("Series auto-posted to Instagram successfully.")
                else:
                    log.warning("Instagram auto-post failed — series saved for manual posting via: python instagram_bot.py force")
            else:
                log.warning("Auto-post: no unposted series found (unexpected)")
        except Exception as exc:
            log.warning(f"Instagram auto-post failed (non-fatal): {exc}")

    return results


def run_once() -> str | None:
    """Generate a series of 3 images. Returns the first successful filepath."""
    results = run_series(n=3)
    return results[0] if results else None


def post_to_instagram(image_path: str, caption: str, cfg: dict) -> bool:
    """
    TODO: Instagram upload — will be implemented as a separate agent.
    Placeholder so the interface is ready.
    """
    log.info(f"[Instagram] Upload pending implementation — {image_path}")
    return False


def setup_login() -> None:
    """
    One-time setup: open Chrome with the bot profile, navigate to grok.com,
    and wait for the user to log in manually via a Windows dialog.
    The session is saved to the bot profile and reused on every subsequent run.
    """
    import ctypes
    cfg = load_config()
    print()
    print("=" * 60)
    print("  GROK LOGIN SETUP")
    print("=" * 60)
    print()
    print("Chrome is opening grok.com now...")
    print("Log in with your X account, then click OK in the popup dialog.")
    print()

    driver = make_driver(cfg)
    try:
        driver.get(GROK_URL)
        # Show a Windows message box — works even when stdin is not a terminal
        ctypes.windll.user32.MessageBoxW(
            0,
            "Log in to grok.com in the Chrome window, then click OK to save your session.",
            "Grok Login Setup",
            0x00000040  # MB_ICONINFORMATION
        )
        print("Session saved to bot profile.")
        print("You can now run:  python art_bot.py run")
    finally:
        try:
            driver.quit()
        except Exception:
            pass


def fill_stock(target: int = 25) -> None:
    """Generate images back-to-back until SAVE_DIR contains at least `target` PNGs."""
    existing = len(list(SAVE_DIR.glob("*.png")))
    needed   = max(0, target - existing)
    print(f"Current images: {existing}  |  Target: {target}  |  Need: {needed} more")

    if needed == 0:
        print("Already at target — nothing to do.")
        return

    success = 0
    fail    = 0

    for i in range(1, needed + 1):
        current = len(list(SAVE_DIR.glob("*.png")))
        if current >= target:
            print(f"\nTarget reached: {current} images in folder.")
            break

        print(f"\n[{i}/{needed}]  Generating image {current + 1}…")
        result = run_once()

        if result:
            success += 1
        else:
            fail += 1
            print("  (failed — continuing to next)")

        # Brief pause between runs so Grok doesn't rate-limit
        if i < needed:
            print("  Pausing 8 s before next run…")
            time.sleep(8)

    final = len(list(SAVE_DIR.glob("*.png")))
    print(f"\nDone. {success} generated, {fail} failed. Total in folder: {final}")


_LOGIN_SITES = {
    "grok":      (GROK_URL,     "grok.com",       "Log in to grok.com with your X account"),
    "leonardo":  (LEONARDO_URL, "Leonardo.ai",    "Log in to Leonardo.ai (Google or email)"),
    "firefly":   (FIREFLY_URL,  "Adobe Firefly",  "Log in to Adobe Firefly with your Adobe account"),
    "easemate":  (EASEMATE_URL, "EaseMate.ai",    "Log in to EaseMate.ai (Google or email)"),
    "chatgpt":   (CHATGPT_URL,  "ChatGPT",        "Log in to ChatGPT with your OpenAI account"),
    "raphael":   (RAPHAEL_URL,  "Raphael.app",    "Log in to Raphael.app (Google or email)"),
    "gemini":    (GEMINI_URL,   "Google Gemini",  "Log in to Gemini with your Google account"),
}


def setup_login_site(site: str = "grok") -> None:
    """Open any supported site in the bot Chrome profile for manual login."""
    import ctypes
    info = _LOGIN_SITES.get(site.lower())
    if not info:
        print(f"Unknown site '{site}'. Choose from: {', '.join(_LOGIN_SITES)}")
        return

    url, label, instruction = info
    cfg = load_config()
    print(f"\nOpening {label} for login setup…")
    driver = make_driver(cfg)
    try:
        driver.get(url)
        ctypes.windll.user32.MessageBoxW(
            0,
            f"{instruction}, then click OK to save your session.",
            f"{label} Login Setup",
            0x00000040,
        )
        print(f"Session saved for {label}.")
    finally:
        try:
            driver.quit()
        except Exception:
            pass


def main():
    import sys
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        if cmd == "test":
            prompt, components = build_prompt()
            print("Sample prompt:")
            print(prompt)
            print("\nComponents:")
            for k, v in components.items():
                print(f"  {k}: {v[:80]}")
        elif cmd == "run":
            run_series(n=3)
        elif cmd == "series":
            n = int(sys.argv[2]) if len(sys.argv) > 2 else 3
            run_series(n=n)
        elif cmd == "login":
            # login [site [site ...]]  — one or more sites, or "all"
            sites = [s.lower() for s in sys.argv[2:]] if len(sys.argv) > 2 else ["grok"]
            if sites == ["all"]:
                sites = list(_LOGIN_SITES.keys())
            for site in sites:
                setup_login_site(site)
        elif cmd == "fill":
            target = int(sys.argv[2]) if len(sys.argv) > 2 else 25
            fill_stock(target)
        else:
            print("Usage:  python art_bot.py [run|series|fill|login|test]")
            print()
            print("  run           — generate a 3-image series across 3 different tools")
            print("  series [N]    — generate an N-image series (default 3)")
            print("  fill [N]      — generate series back-to-back until folder has N images (default 25)")
            print("  login [site]  — log in to a source site and save session")
            print("                  sites: grok, leonardo, firefly, bing, easemate, all")
            print("  test          — print a sample prompt, no browser opened")
    else:
        run_series(n=3)


if __name__ == "__main__":
    main()
