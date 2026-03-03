"""
AI Art Bot — Hourly Image Generator + Instagram Poster

Each run:
  1. Build a unique artistic prompt
  2. Generate image via Grok (fallback: ChatGPT)
  3. Save to Desktop/AI_Art/ with date, time, and prompt in the filename
  4. Post to Instagram with date + time + prompt as the caption
  5. Engage with 3-5 accounts (likes, comments, replies)
  6. Stop until the next hour

Run hourly via Windows Task Scheduler:
  python art_bot.py run

Manual login setup:
  python art_bot.py login [grok|chatgpt|instagram]
"""

import base64
import json
import logging
import os
import re
import random
import time
import urllib.parse
from datetime import datetime
from pathlib import Path

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# ── Paths ─────────────────────────────────────────────────────────────────────

BOT_DIR  = Path(__file__).parent
SAVE_DIR = Path(r"C:\Users\gageg\Desktop\AI_Art")
LOG_DIR  = BOT_DIR / "logs"

SAVE_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

CONFIG_FILE  = BOT_DIR / "config.json"
HISTORY_FILE = BOT_DIR / "prompt_history.json"
LOCK_FILE    = BOT_DIR / "artbot.lock"

# ── Source URLs ───────────────────────────────────────────────────────────────

GROK_URL    = "https://grok.com"
CHATGPT_URL = "https://chatgpt.com/"

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.FileHandler(
            LOG_DIR / f"bot_{datetime.now().strftime('%Y%m%d')}.log",
            encoding="utf-8",
        ),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("art_bot")


# ── Prompt library ────────────────────────────────────────────────────────────

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
    "shot on large-format film, rich tonal range and deep focus",
    "photographed on Kodachrome slide film, saturated and grain-heavy",
    "captured on medium-format black-and-white film with wide dynamic range",
    "shot on expired 35mm Portra film, soft colours and organic grain",
    "photographed with a long exposure at blue hour, light trails and stillness",
    "captured with a vintage Hasselblad on Tri-X pushed to 3200 ISO",
    "taken with a pinhole camera, soft and dreamlike with extreme depth of field",
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

HISTORY_SIZE = 80   # entries kept in prompt_history.json

# Strip common lead-in phrases for clean caption display
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
    for p in _DESCRIPTOR_PREFIXES:
        text = re.sub(p, "", text, flags=re.IGNORECASE).strip()
    first_clause = re.split(r"[,.]", text)[0].strip()[:max_len]
    return first_clause[0].upper() + first_clause[1:] if first_clause else text[:max_len]


def _load_history() -> list:
    """Load prompt history. Migrates old [subject, style] list entries to dicts."""
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                raw = json.load(f).get("used", [])
            migrated = []
            for item in raw:
                if isinstance(item, list):
                    # Old format: [subject[:40], style[:40]]
                    migrated.append({
                        "subject":     item[0] if len(item) > 0 else "",
                        "style":       item[1] if len(item) > 1 else "",
                        "full_prompt": None,
                    })
                else:
                    migrated.append(item)
            return migrated
        except Exception:
            pass
    return []


def _save_history(used: list) -> None:
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump({"used": used[-HISTORY_SIZE:]}, f, indent=2)


def build_prompt() -> tuple:
    """Build a unique prompt. Returns (prompt_str, components_dict).

    Primary path: Claude-powered agent (prompt_agent.py) — analyses the full
    recent history and generates a completely fresh concept each run.
    Fallback: random selection from the static lists below (original behaviour).
    """
    history = _load_history()

    # ── Primary: Claude prompt agent ─────────────────────────────────────────
    try:
        from prompt_agent import generate_fresh_prompt
        result = generate_fresh_prompt(history)
        if result:
            prompt_str, components = result
            history.append({
                # Full values for per-component cooldown tracking
                "subject_full":     components.get("subject_full",     components.get("subject",     "")),
                "environment_full": components.get("environment_full", components.get("environment", "")),
                "style_full":       components.get("style_full",       components.get("style",       "")),
                "mood_full":        components.get("mood_full",        components.get("mood",        "")),
                "palette_full":     components.get("palette_full",     components.get("palette",     "")),
                "closer_full":      components.get("closer_full",      components.get("closer",      "")),
                # Category rotation metadata
                "subject_category": components.get("subject_category", ""),
                "style_medium":     components.get("style_medium",     ""),
                "palette_temp":     components.get("palette_temp",     ""),
                # Legacy / caption fields
                "subject":          components.get("subject", "")[:60],
                "style":            components.get("style",   "")[:60],
                "full_prompt":      prompt_str,
                "generated_at":     datetime.now().isoformat(),
                "source":           "combinatorial",
            })
            _save_history(history)
            return prompt_str, components
    except Exception as exc:
        log.warning(f"Prompt agent unavailable ({exc}) — using random fallback.")

    # ── Fallback: random selection from static lists ──────────────────────────
    # Build a dedup set from whatever format is in history (old or new)
    used_set = set()
    for item in history:
        if isinstance(item, dict):
            used_set.add((item.get("subject", "")[:40], item.get("style", "")[:40]))
        elif isinstance(item, list) and len(item) >= 2:
            used_set.add((item[0], item[1]))

    subject = style = ""
    for _ in range(30):
        subject = random.choice(SUBJECTS)
        style   = random.choice(STYLES)
        if (subject[:40], style[:40]) not in used_set:
            break

    env     = random.choice(ENVIRONMENTS)
    mood    = random.choice(MOODS)
    palette = random.choice(COLOR_PALETTES)
    closer  = random.choice(CLOSERS)

    prompt_str = (
        f"{subject.capitalize()}, {env}. "
        f"{style.capitalize()}, {palette}. "
        f"{mood.capitalize()}. {closer}"
    )
    components = {
        "subject": subject, "environment": env, "style": style,
        "mood": mood, "palette": palette, "closer": closer,
    }

    history.append({
        "subject_full":     subject,
        "environment_full": env,
        "style_full":       style,
        "mood_full":        mood,
        "palette_full":     palette,
        "closer_full":      closer,
        "subject":          subject[:60],
        "style":            style[:60],
        "full_prompt":      prompt_str,
        "generated_at":     datetime.now().isoformat(),
        "source":           "random_fallback",
    })
    _save_history(history)
    return prompt_str, components


# ── Config ────────────────────────────────────────────────────────────────────

def load_config() -> dict:
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    cfg = {
        "chrome_profile_path": str(BOT_DIR / "chrome_profile"),
        "instagram_username": "",
        "last_run": None,
    }
    save_config(cfg)
    return cfg


def save_config(cfg: dict) -> None:
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4)


# ── Selenium helpers ──────────────────────────────────────────────────────────

def _clear_profile_locks(profile_dir: str) -> None:
    """Delete Chrome lock files and kill any lingering Chrome processes using this profile."""
    root = Path(profile_dir)

    # Kill any Chrome processes still holding the bot's profile open
    try:
        import subprocess
        profile_token = str(root).replace("\\", "\\\\")
        ps = (
            f"Get-Process chrome -ErrorAction SilentlyContinue | ForEach-Object {{"
            f" $procId = $_.Id;"
            f" try {{"
            f"  $cmd = (Get-WmiObject Win32_Process -Filter \"ProcessId=$procId\" -EA SilentlyContinue).CommandLine;"
            f"  if ($cmd -and $cmd -like '*AIArtBot*chrome_profile*') {{ $_ | Stop-Process -Force }}"
            f" }} catch {{}} }}"
        )
        subprocess.run(["powershell", "-Command", ps], capture_output=True, timeout=10)
        time.sleep(1)
    except Exception:
        pass

    # Delete singleton/lock files
    for pattern in ("LOCK", "SingletonLock", "SingletonCookie", "SingletonSocket"):
        for p in root.rglob(pattern):
            try:
                p.unlink()
            except Exception:
                pass


def make_driver(cfg: dict, headless: bool = True) -> webdriver.Chrome:
    opts = Options()
    profile = cfg.get("chrome_profile_path", "").strip()
    if profile:
        Path(profile).mkdir(parents=True, exist_ok=True)
        _clear_profile_locks(profile)
        opts.add_argument(f"--user-data-dir={profile}")
    if headless:
        # Move off-screen instead of true headless — looks like normal Chrome to websites,
        # but the window is invisible to the user (far off-screen, no taskbar focus).
        opts.add_argument("--window-position=-10000,-10000")
        opts.add_argument("--disable-gpu")
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
        if random.random() < 0.04:
            time.sleep(random.uniform(0.04, 0.18))


def find_first(driver, selectors: list, timeout: int = 15):
    for by, sel in selectors:
        try:
            el = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((by, sel))
            )
            return el
        except Exception:
            pass
    return None


def _screenshot(driver, label: str) -> None:
    try:
        driver.save_screenshot(
            str(LOG_DIR / f"{label}_{datetime.now().strftime('%H%M%S')}.png")
        )
    except Exception:
        pass


# ── Image saving ──────────────────────────────────────────────────────────────

def _save_image(driver, img_url: str, prompt: str, source: str, components: dict) -> str | None:
    """Download image and save to SAVE_DIR. Returns filepath or None."""
    now      = datetime.now()
    slug     = re.sub(r"\W+", "_", prompt[:45]).strip("_")
    filename = f"{now.strftime('%Y%m%d_%H%M%S')}_{slug}.png"
    filepath = SAVE_DIR / filename

    try:
        if img_url.startswith("blob:"):
            b64 = driver.execute_script("""
                var img = document.querySelector("img[src='" + arguments[0] + "']");
                if (!img) return null;
                var c = document.createElement('canvas');
                c.width  = img.naturalWidth  || 1024;
                c.height = img.naturalHeight || 1024;
                c.getContext('2d').drawImage(img, 0, 0);
                return c.toDataURL('image/png').split(',')[1];
            """, img_url)
            if not b64:
                log.error("Canvas extraction returned nothing")
                return None
            with open(filepath, "wb") as f:
                f.write(base64.b64decode(b64))
        else:
            session = requests.Session()
            for ck in driver.get_cookies():
                session.cookies.set(ck["name"], ck["value"])
            ua   = driver.execute_script("return navigator.userAgent;")
            resp = session.get(
                img_url,
                headers={"User-Agent": ua, "Referer": GROK_URL},
                timeout=30,
            )
            resp.raise_for_status()
            with open(filepath, "wb") as f:
                f.write(resp.content)

        size_kb = filepath.stat().st_size // 1024
        if size_kb < 30:
            log.warning(f"File too small ({size_kb} KB) — likely not a real image, discarding")
            filepath.unlink(missing_ok=True)
            return None

        # Write sidecar JSON so caption builder can read structured data
        meta = {
            "generated_at": now.isoformat(),
            "prompt":       prompt,
            "source":       source,
            "components":   components,
        }
        filepath.with_name(filepath.stem + "_meta.json").write_text(
            json.dumps(meta, indent=2), encoding="utf-8"
        )

        log.info(f"Saved → {filepath.name}  ({size_kb} KB)")
        return str(filepath)

    except Exception as exc:
        log.error(f"Image save failed: {exc}")
        filepath.unlink(missing_ok=True)
        return None


def _wait_for_large_image(driver, timeout: int, cdn_hints: list) -> str | None:
    """Poll for a 512px+ image matching a CDN hint, fall back to any large image."""
    start = time.time()
    while time.time() - start < timeout:
        result = driver.execute_script("""
            var hints    = arguments[0];
            var imgs     = document.querySelectorAll('img');
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
            log.info(f"Image detected ({result['w']}x{result['h']}): {result['src'][:80]}")
            return result["src"]
        time.sleep(4)
    return None


# ── Grok generator ────────────────────────────────────────────────────────────

def _generate_via_grok(driver, prompt: str) -> str | None:
    log.info("Grok: loading grok.com…")
    driver.get(GROK_URL)
    time.sleep(4)

    input_el = find_first(driver, [
        (By.CSS_SELECTOR, "textarea"),
        (By.CSS_SELECTOR, "div[contenteditable='true']"),
        (By.CSS_SELECTOR, "div[role='textbox']"),
    ])
    if not input_el:
        log.error("Grok: chat input not found")
        _screenshot(driver, "grok_no_input")
        return None

    # Click image-generation mode button if visible
    for by, sel in [
        (By.XPATH, "//button[contains(translate(., 'IMAGE', 'image'), 'image')]"),
        (By.CSS_SELECTOR, "button[aria-label*='mage']"),
        (By.XPATH, "//*[contains(@aria-label,'Generate image') or contains(@aria-label,'Image')]"),
    ]:
        try:
            btn = driver.find_element(by, sel)
            driver.execute_script("arguments[0].click();", btn)
            log.info("Grok: clicked image mode")
            time.sleep(1.5)
            break
        except Exception:
            pass

    # Wait up to 45s for Turnstile overlay to resolve; try clicking its checkbox each second
    for _t in range(45):
        try:
            overlay = driver.find_element(By.ID, "turnstile-widget")
            if overlay.is_displayed():
                if _t == 0:
                    log.info("Grok: Turnstile detected — attempting checkbox click…")
                try:
                    iframe = overlay.find_element(By.TAG_NAME, "iframe")
                    driver.switch_to.frame(iframe)
                    cb = driver.find_element(By.CSS_SELECTOR, "input[type='checkbox']")
                    driver.execute_script("arguments[0].click();", cb)
                    driver.switch_to.default_content()
                    log.info("Grok: Turnstile checkbox clicked — waiting to clear…")
                    time.sleep(3)
                except Exception:
                    driver.switch_to.default_content()
                    time.sleep(1)
                continue
        except Exception:
            pass
        break
    else:
        log.warning("Grok: Turnstile still present after 45s — proceeding anyway")

    driver.execute_script("arguments[0].scrollIntoView(true);", input_el)
    driver.execute_script("arguments[0].click();", input_el)
    time.sleep(0.5)
    try:
        input_el.clear()
    except Exception:
        pass
    slow_type(input_el, prompt)
    time.sleep(1)

    submit_el = find_first(driver, [
        (By.CSS_SELECTOR, "button[type='submit']"),
        (By.XPATH, "//button[@aria-label='Submit message']"),
        (By.XPATH, "//button[@aria-label='Send message']"),
        (By.CSS_SELECTOR, "[data-testid='send-button']"),
    ], timeout=5)
    if submit_el:
        driver.execute_script("arguments[0].click();", submit_el)
        log.info("Grok: submitted via button")
    else:
        input_el.send_keys(Keys.RETURN)
        log.info("Grok: submitted via Enter")

    log.info("Grok: waiting for image (up to 180 s)…")
    time.sleep(15)

    start    = time.time()
    deadline = start + 165
    found_url = None

    while time.time() < deadline:
        time.sleep(3)
        # Detect mid-generation Turnstile and try to click the checkbox inside its iframe
        try:
            overlay = driver.find_element(By.ID, "turnstile-widget")
            if overlay.is_displayed():
                try:
                    iframe = overlay.find_element(By.TAG_NAME, "iframe")
                    driver.switch_to.frame(iframe)
                    cb = driver.find_element(By.CSS_SELECTOR, "input[type='checkbox']")
                    driver.execute_script("arguments[0].click();", cb)
                    driver.switch_to.default_content()
                    log.info("Grok: clicked Turnstile checkbox — waiting to resolve…")
                    time.sleep(5)
                except Exception:
                    driver.switch_to.default_content()
                continue
        except Exception:
            pass
        try:
            result = driver.execute_script("""
                var imgs = document.querySelectorAll('img');
                var candidates = [];
                for (var i = 0; i < imgs.length; i++) {
                    var src = imgs[i].src || '';
                    var w   = imgs[i].naturalWidth;
                    var h   = imgs[i].naturalHeight;
                    if (w >= 512 && h >= 512 && src.indexOf('profile_images') === -1) {
                        candidates.push({src: src, w: w, h: h});
                    }
                }
                return candidates;
            """)
            if result:
                for item in result:
                    src = item.get("src", "")
                    if any(k in src for k in ("grokusercontent", "assets.grok.com", "blob:", "pbs.twimg", "grok.com")):
                        found_url = src
                        log.info(f"Grok: image found ({item['w']}x{item['h']}): {src[:80]}")
                        break
                if found_url:
                    break
        except Exception as exc:
            log.debug(f"Grok poll: {exc}")

        elapsed = int(time.time() - start) + 15
        if elapsed % 30 == 0:
            log.info(f"  Grok: still waiting… ({elapsed}s)")
            _screenshot(driver, f"grok_wait_{elapsed}s")

    if not found_url:
        log.error("Grok: no image found within 180 s")
        _screenshot(driver, "grok_timeout")
    return found_url


# ── ChatGPT generator ─────────────────────────────────────────────────────────

def _generate_via_chatgpt(driver, prompt: str) -> str | None:
    log.info("ChatGPT: loading chatgpt.com…")
    driver.get(CHATGPT_URL)
    time.sleep(6)

    prompt_el = find_first(driver, [
        (By.CSS_SELECTOR, "#prompt-textarea"),
        (By.CSS_SELECTOR, "div[contenteditable='true'][data-lexical-editor]"),
        (By.CSS_SELECTOR, "div[contenteditable='true']"),
        (By.CSS_SELECTOR, "textarea[placeholder*='Message' i]"),
    ], timeout=20)
    if not prompt_el:
        log.error("ChatGPT: prompt input not found")
        return None

    prompt_el.click()
    time.sleep(0.5)
    slow_type(prompt_el, f"Generate an image: {prompt[:450]}")
    time.sleep(1)

    submit_el = find_first(driver, [
        (By.CSS_SELECTOR, "button[data-testid='send-button']"),
        (By.CSS_SELECTOR, "button[aria-label='Send prompt']"),
        (By.XPATH, "//button[@aria-label='Send message']"),
    ], timeout=5)
    if submit_el:
        driver.execute_script("arguments[0].click();", submit_el)
    else:
        prompt_el.send_keys(Keys.RETURN)

    log.info("ChatGPT: waiting for image (up to 120 s)…")
    time.sleep(15)

    return _wait_for_large_image(driver, timeout=105, cdn_hints=[
        "files.oaiusercontent.com", "oaidalleapiprodscus", "oaidalleus",
    ])


# ── Pollinations generator ────────────────────────────────────────────────────

def _generate_via_pollinations(driver, prompt: str) -> str | None:
    """Download image from Pollinations.ai directly and save it. Returns 'SAVED:<path>' or None."""
    encoded = urllib.parse.quote(prompt[:500], safe="")
    url = (
        f"https://image.pollinations.ai/prompt/{encoded}"
        f"?width=1024&height=1024&nologo=true&enhance=true&model=flux"
        f"&seed={random.randint(1, 999999)}"
    )
    log.info("Pollinations: requesting image…")
    try:
        resp = requests.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
                "Referer": "https://pollinations.ai/",
            },
            timeout=120,
            stream=True,
        )
        if resp.status_code != 200:
            log.warning(f"Pollinations: HTTP {resp.status_code}")
            return None

        now  = datetime.now()
        slug = re.sub(r"[^\w]+", "_", prompt[:50]).strip("_")
        filepath = SAVE_DIR / f"{now.strftime('%Y%m%d_%H%M%S')}_{slug}.png"
        SAVE_DIR.mkdir(parents=True, exist_ok=True)
        with open(filepath, "wb") as f:
            for chunk in resp.iter_content(8192):
                f.write(chunk)

        size_kb = filepath.stat().st_size // 1024
        if size_kb < 30:
            log.warning(f"Pollinations: image too small ({size_kb} KB) — discarding")
            filepath.unlink(missing_ok=True)
            return None

        # Write sidecar meta JSON
        meta = {
            "generated_at": now.isoformat(),
            "prompt":       prompt,
            "source":       "pollinations",
            "components":   {},
        }
        filepath.with_name(filepath.stem + "_meta.json").write_text(
            json.dumps(meta, indent=2), encoding="utf-8"
        )
        log.info(f"Pollinations: saved {filepath.name} ({size_kb} KB)")
        return f"SAVED:{filepath}"
    except Exception as exc:
        log.warning(f"Pollinations: {exc}")
        return None


# ── Main image generator ──────────────────────────────────────────────────────

def generate_image(prompt: str, components: dict, cfg: dict) -> str | None:
    """Try Grok first, fall back to ChatGPT, then Pollinations. Returns saved filepath or None."""
    sources = [
        ("grok",         _generate_via_grok,         ["grokusercontent", "assets.grok.com"]),
        ("chatgpt",      _generate_via_chatgpt,       ["oaiusercontent", "oaidalleapiprodscus"]),
        ("pollinations", _generate_via_pollinations,  ["pollinations"]),
    ]
    for source, gen_fn, cdn_hints in sources:
        log.info(f"Trying {source}…")
        driver = None
        try:
            driver = make_driver(cfg)
            img_url = gen_fn(driver, prompt)
            if img_url:
                if img_url.startswith("SAVED:"):
                    filepath = img_url[6:]
                    log.info(f"Generated via {source}: {Path(filepath).name}")
                    return filepath
                filepath = _save_image(driver, img_url, prompt, source, components)
                if filepath:
                    log.info(f"Generated via {source}: {Path(filepath).name}")
                    return filepath
            log.warning(f"{source} failed — trying next source")
        except Exception as exc:
            log.error(f"{source} error: {exc}", exc_info=True)
        finally:
            if driver is not None:
                try:
                    driver.quit()
                except Exception:
                    pass

    log.error("All sources failed — no image generated this run")
    return None


# ── Main run function ─────────────────────────────────────────────────────────

def run() -> bool:
    """Generate 1 image, post to Instagram, engage. Returns True on success."""
    # Prevent overlapping runs
    if LOCK_FILE.exists():
        try:
            age_s = time.time() - LOCK_FILE.stat().st_mtime
            if age_s < 7200:
                log.warning(f"Lock file exists ({age_s:.0f}s old) — another run active. Exiting.")
                return False
            else:
                log.warning(f"Stale lock ({age_s:.0f}s) — removing and continuing.")
                LOCK_FILE.unlink()
        except Exception:
            pass

    LOCK_FILE.write_text(str(datetime.now()))
    try:
        return _run_inner()
    finally:
        try:
            LOCK_FILE.unlink()
        except Exception:
            pass


def _run_inner() -> bool:
    log.info("=" * 60)
    log.info(f"AI Art Bot — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    log.info("=" * 60)

    cfg = load_config()

    # 1. Build prompt
    prompt, components = build_prompt()
    prompt = prompt.rstrip(". ") + ". Psychedelic, 3D, Art."
    log.info(f"Prompt: {prompt[:100]}…")

    # 2. Generate image
    filepath = generate_image(prompt, components, cfg)
    if not filepath:
        log.error("Image generation failed — skipping post")
        cfg["last_run"] = datetime.now().isoformat()
        save_config(cfg)
        return False

    # 3. Post to Instagram
    posted   = False
    caption  = ""
    try:
        from instagram_bot import InstagramBot, build_caption, load_tracker, mark_posted, save_tracker
        img_path = Path(filepath)
        caption  = build_caption(img_path)
        bot      = InstagramBot(cfg)
        success, post_url = bot.post_image(img_path, caption)
        if success:
            tracker = load_tracker()
            mark_posted(tracker, img_path, post_url)
            save_tracker(tracker)
            log.info(f"Posted → {post_url or 'no URL captured'}")
            posted = True
        else:
            log.warning("Instagram post failed")
    except Exception as exc:
        log.error(f"Instagram error: {exc}")

    # 4. Engage (only after a successful post)
    if posted:
        try:
            from engagement_bot import run_post_engagement
            run_post_engagement(cfg, caption)
        except Exception as exc:
            log.warning(f"Engagement error (non-fatal): {exc}")

    cfg["last_run"] = datetime.now().isoformat()
    save_config(cfg)

    log.info("=" * 60)
    log.info(f"Run complete — {'SUCCESS' if posted else 'PARTIAL (image saved, post failed)'}")
    return posted


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    import ctypes

    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"

    if cmd == "run":
        try:
            success = run()
        except Exception as exc:
            log.critical(f"Unhandled exception in run(): {exc}", exc_info=True)
            sys.exit(2)
        sys.exit(0 if success else 1)

    elif cmd == "login":
        site = sys.argv[2].lower() if len(sys.argv) > 2 else "grok"
        urls = {
            "grok":      GROK_URL,
            "chatgpt":   CHATGPT_URL,
            "instagram": "https://www.instagram.com/",
        }
        url = urls.get(site)
        if not url:
            print(f"Unknown site '{site}'. Choose from: {', '.join(urls)}")
            sys.exit(1)
        print(f"Opening {site} for manual login…")
        cfg    = load_config()
        driver = make_driver(cfg, headless=False)
        driver.get(url)
        ctypes.windll.user32.MessageBoxW(
            0,
            f"Log in to {site} in Chrome, then click OK to save the session.",
            "Login Setup",
            0x00000040,
        )
        print("Session saved.")
        driver.quit()

    else:
        print(f"Unknown command: {cmd}")
        print("Usage: python art_bot.py [run|login [grok|chatgpt|instagram]]")
        sys.exit(1)
