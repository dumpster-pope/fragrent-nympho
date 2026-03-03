"""
AIArtBot Daily Monitor & Self-Healing Agent

Runs once per day (default: 11 PM via Windows Task Scheduler).

What it checks and fixes each run:
  1. Stale lock files       — cleared so nothing stays blocked
  2. Zombie Chrome/driver   — killed, profile locks cleared
  3. Scheduler task         — verifies AIArtBot_Hourly is active; re-registers if broken
  4. Today's logs           — counts ERROR/CRITICAL lines, surfaces the worst ones
  5. Daily health           — checks that 24 images were generated and posted today
  6. Unposted images        — any PNG in AI_Art not yet on Instagram → force-posts them
  7. Image quality          — removes posts with suspiciously small or corrupt images

Results logged to:    AIArtBot/logs/monitor_YYYYMMDD.log
Rolling 30-day report: AIArtBot/monitor_report.json

Run manually: python monitor_agent.py
"""

import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────

BOT_DIR      = Path(__file__).parent
SAVE_DIR     = Path(r"C:\Users\gageg\Desktop\AI_Art")
LOG_DIR      = BOT_DIR / "logs"
LOCK_FILE    = BOT_DIR / "artbot.lock"
REGISTER_PS1 = BOT_DIR / "register_task.ps1"
REPORT_FILE  = BOT_DIR / "monitor_report.json"

LOG_DIR.mkdir(exist_ok=True)

# ── Constants ──────────────────────────────────────────────────────────────────

TASK_NAME       = "AIArtBot_Hourly"
EXPECTED_DAILY  = 12          # 1 image per 2 hours × 12 runs per day
LOW_WATER_MARK  = 9           # flag day as unhealthy if fewer than this were posted
MIN_AGE_MINUTES = 90          # skip images newer than this (bot may still be working)
MAX_FORCE_POSTS = 6           # cap force-posts per monitor run
FORCE_POST_DELAY = 75         # seconds between consecutive force-posts
MIN_IMAGE_SIZE_KB = 50        # images smaller than this are considered corrupt/placeholder

# ── Logging ────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.FileHandler(
            LOG_DIR / f"monitor_{datetime.now().strftime('%Y%m%d')}.log",
            encoding="utf-8",
        ),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("monitor")


# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _load_tracker() -> dict:
    tracker_file = BOT_DIR / "posted_tracker.json"
    if tracker_file.exists():
        try:
            with open(tracker_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"posted": [], "daily_counts": {}, "post_urls": {}}


def _pid_running(pid: int) -> bool:
    try:
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
            capture_output=True, text=True, timeout=5,
        )
        return str(pid) in result.stdout
    except Exception:
        return True


def _artbot_running() -> bool:
    if LOCK_FILE.exists():
        try:
            age = time.time() - LOCK_FILE.stat().st_mtime
            if age < 7200:
                return True
        except Exception:
            pass
    return False


def _wait_for_artbot(max_wait: int = 300) -> None:
    if not _artbot_running():
        return
    log.info(f"art_bot is running — waiting up to {max_wait}s…")
    deadline = time.time() + max_wait
    while time.time() < deadline:
        time.sleep(20)
        if not _artbot_running():
            log.info("art_bot finished — proceeding.")
            return
    log.warning("art_bot did not finish within wait window — proceeding anyway.")


# ══════════════════════════════════════════════════════════════════════════════
#  STEP 1 — STALE LOCK FILES
# ══════════════════════════════════════════════════════════════════════════════

def clear_stale_locks() -> list[str]:
    cleared = []
    if LOCK_FILE.exists():
        try:
            age = time.time() - LOCK_FILE.stat().st_mtime
            if age >= 7200:
                LOCK_FILE.unlink()
                cleared.append(LOCK_FILE.name)
                log.info(f"Cleared stale lock: {LOCK_FILE.name}  (age {age:.0f}s)")
        except Exception as exc:
            log.warning(f"Could not clear lock: {exc}")
    return cleared


# ══════════════════════════════════════════════════════════════════════════════
#  STEP 2 — ZOMBIE CHROME / CHROMEDRIVER CLEANUP
# ══════════════════════════════════════════════════════════════════════════════

CHROME_PROFILE = BOT_DIR / "chrome_profile"


def cleanup_zombie_chrome() -> dict:
    killed_drivers = []
    killed_chrome  = []
    cleared_locks  = []

    # Kill all ChromeDriver processes
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-Process -Name chromedriver -ErrorAction SilentlyContinue | "
             "Select-Object Id | ConvertTo-Json"],
            capture_output=True, text=True, timeout=10,
        )
        if result.stdout.strip():
            items = json.loads(result.stdout.strip())
            if isinstance(items, dict):
                items = [items]
            for item in items:
                pid = item.get("Id")
                if pid:
                    subprocess.run(
                        ["powershell", "-NoProfile", "-Command",
                         f"Stop-Process -Id {pid} -Force -ErrorAction SilentlyContinue"],
                        timeout=5,
                    )
                    killed_drivers.append(pid)
                    log.info(f"Killed ChromeDriver PID {pid}")
    except Exception as exc:
        log.warning(f"ChromeDriver cleanup error: {exc}")

    # Kill bot-owned Chrome processes (those launched with AIArtBot profile)
    try:
        wmi_script = (
            "Get-WmiObject Win32_Process -Filter \"name='chrome.exe'\" | "
            "Where-Object { $_.CommandLine -like '*AIArtBot*' } | "
            "Select-Object ProcessId | ConvertTo-Json"
        )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", wmi_script],
            capture_output=True, text=True, timeout=15,
        )
        if result.stdout.strip():
            items = json.loads(result.stdout.strip())
            if isinstance(items, dict):
                items = [items]
            for item in items:
                pid = item.get("ProcessId")
                if pid:
                    subprocess.run(
                        ["powershell", "-NoProfile", "-Command",
                         f"Stop-Process -Id {pid} -Force -ErrorAction SilentlyContinue"],
                        timeout=5,
                    )
                    killed_chrome.append(pid)
                    log.info(f"Killed bot Chrome PID {pid}")
    except Exception as exc:
        log.warning(f"Bot Chrome cleanup error: {exc}")

    # Clear Chrome profile lock files
    if CHROME_PROFILE.exists():
        for pattern in ("LOCK", "SingletonLock", "SingletonCookie", "SingletonSocket"):
            for p in CHROME_PROFILE.rglob(pattern):
                try:
                    p.unlink()
                    cleared_locks.append(p.name)
                except Exception:
                    pass
        if cleared_locks:
            log.info(f"Cleared {len(cleared_locks)} Chrome profile lock file(s).")

    return {
        "drivers_killed": killed_drivers,
        "chrome_killed":  killed_chrome,
        "locks_cleared":  len(cleared_locks),
    }


# ══════════════════════════════════════════════════════════════════════════════
#  STEP 3 — SCHEDULER TASK
# ══════════════════════════════════════════════════════════════════════════════

def check_scheduler() -> dict:
    result = {
        "task_exists":         False,
        "state":               "Unknown",
        "last_run":            None,
        "last_result":         None,
        "next_run":            None,
        "hours_since_last_run": None,
        "healthy":             False,
    }
    try:
        info_json = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command",
             f"Get-ScheduledTaskInfo -TaskName '{TASK_NAME}' | "
             "Select-Object LastRunTime, LastTaskResult, NextRunTime | ConvertTo-Json"],
            text=True, timeout=20,
        )
        info = json.loads(info_json.strip())
        result["task_exists"] = True
        result["last_run"]    = str(info.get("LastRunTime", ""))
        result["last_result"] = info.get("LastTaskResult")
        result["next_run"]    = str(info.get("NextRunTime", ""))

        state_out = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command",
             f"(Get-ScheduledTask -TaskName '{TASK_NAME}').State"],
            text=True, timeout=10,
        ).strip()
        result["state"] = state_out

        try:
            raw = result["last_run"]
            if "/Date(" in raw:
                ms      = int(raw.split("(")[1].split(")")[0].split("+")[0].split("-")[0])
                last_dt = datetime.fromtimestamp(ms / 1000)
            else:
                last_dt = datetime.fromisoformat(raw[:19])
            hours_ago = (datetime.now() - last_dt).total_seconds() / 3600
            result["hours_since_last_run"] = round(hours_ago, 1)
        except Exception:
            pass

        last_result  = result["last_result"]
        ran_recently = (result["hours_since_last_run"] or 999) <= 2
        result["healthy"] = (
            result["state"] in ("Ready", "Running") and
            last_result in (0, 267009, 267011) and
            ran_recently
        )

    except subprocess.CalledProcessError:
        log.warning(f"Scheduler task '{TASK_NAME}' not found.")
    except Exception as exc:
        log.warning(f"Scheduler check error: {exc}")

    return result


def fix_scheduler(scheduler_info: dict) -> bool:
    if scheduler_info.get("healthy"):
        return True
    if not REGISTER_PS1.exists():
        log.error(f"Cannot fix scheduler: {REGISTER_PS1} not found.")
        return False
    log.warning(
        f"Scheduler unhealthy (state={scheduler_info.get('state')}, "
        f"last_result={scheduler_info.get('last_result')}) — re-registering…"
    )
    try:
        result = subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(REGISTER_PS1)],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            log.info("Scheduler task re-registered successfully.")
            return True
        log.error(f"Re-registration failed (exit {result.returncode}): {result.stderr[:300]}")
        return False
    except Exception as exc:
        log.error(f"Re-registration exception: {exc}")
        return False


# ══════════════════════════════════════════════════════════════════════════════
#  STEP 4 — LOG ERROR SCAN
# ══════════════════════════════════════════════════════════════════════════════

def check_logs_for_errors() -> dict:
    today  = datetime.now().strftime("%Y%m%d")
    result = {"error_count": 0, "critical_count": 0, "warning_count": 0, "recent_errors": []}

    for log_file in [LOG_DIR / f"bot_{today}.log", LOG_DIR / f"instagram_{today}.log"]:
        if not log_file.exists():
            continue
        try:
            lines = log_file.read_text(encoding="utf-8", errors="replace").splitlines()
            for line in lines:
                if " CRITICAL " in line:
                    result["critical_count"] += 1
                    result["recent_errors"].append(f"[CRITICAL] {line.strip()}")
                elif " ERROR " in line:
                    result["error_count"] += 1
                    result["recent_errors"].append(f"[ERROR] {line.strip()}")
                elif " WARNING " in line:
                    result["warning_count"] += 1
        except Exception as exc:
            log.warning(f"Could not read {log_file.name}: {exc}")

    result["recent_errors"] = [e[:200] for e in result["recent_errors"][-15:]]
    return result


# ══════════════════════════════════════════════════════════════════════════════
#  STEP 5 — DAILY HEALTH
# ══════════════════════════════════════════════════════════════════════════════

def check_daily_health(tracker: dict) -> dict:
    now       = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    yest_str  = (now - timedelta(days=1)).strftime("%Y-%m-%d")

    day_start      = now.replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    generated_today = sum(1 for p in SAVE_DIR.glob("*.png") if p.stat().st_mtime >= day_start)

    daily_counts   = tracker.get("daily_counts", {})
    posted_today   = daily_counts.get(today_str, 0)
    posted_yest    = daily_counts.get(yest_str, 0)
    total_images   = sum(1 for _ in SAVE_DIR.glob("*.png"))
    total_posted   = len(tracker.get("posted", []))
    unposted_total = total_images - total_posted

    healthy = posted_today >= LOW_WATER_MARK or (now.hour < 20 and generated_today > 0)

    return {
        "date":             today_str,
        "generated_today":  generated_today,
        "posted_today":     posted_today,
        "posted_yesterday": posted_yest,
        "total_images":     total_images,
        "total_posted":     total_posted,
        "unposted_total":   unposted_total,
        "target_daily":     EXPECTED_DAILY,
        "healthy":          healthy,
    }


# ══════════════════════════════════════════════════════════════════════════════
#  STEP 6 — UNPOSTED IMAGES
# ══════════════════════════════════════════════════════════════════════════════

def find_unposted_images(tracker: dict) -> list[Path]:
    """Return PNG files in AI_Art not yet in the tracker, oldest-first, skipping very recent."""
    posted_set = set(tracker.get("posted", []))
    cutoff     = time.time() - MIN_AGE_MINUTES * 60
    return [
        p for p in sorted(SAVE_DIR.glob("*.png"), key=lambda x: x.stat().st_mtime)
        if p.name not in posted_set and p.stat().st_mtime <= cutoff
    ]


def force_post_unposted(unposted: list[Path]) -> dict:
    """Force-post up to MAX_FORCE_POSTS unposted images."""
    results = {
        "images_queued": len(unposted),
        "attempted":     0,
        "succeeded":     0,
        "failed":        0,
    }
    if not unposted:
        return results

    try:
        sys.path.insert(0, str(BOT_DIR))
        from art_bot import load_config
        from instagram_bot import InstagramBot, build_caption, load_tracker, mark_posted, save_tracker

        cfg     = load_config()
        bot     = InstagramBot(cfg)
        tracker = load_tracker()

        to_post = min(len(unposted), MAX_FORCE_POSTS)
        results["attempted"] = to_post

        for i, img_path in enumerate(unposted[:to_post]):
            log.info(f"Force-post {i + 1}/{to_post}: {img_path.name}")
            try:
                caption  = build_caption(img_path)
                success, post_url = bot.post_image(img_path, caption)
                if success:
                    mark_posted(tracker, img_path, post_url)
                    save_tracker(tracker)
                    results["succeeded"] += 1
                    log.info(f"  Succeeded → {post_url or 'no URL'}")
                else:
                    results["failed"] += 1
                    log.warning("  Post failed — stopping force-post loop.")
                    break
            except Exception as exc:
                log.error(f"  force_post exception: {exc}")
                results["failed"] += 1
                break

            if i < to_post - 1:
                log.info(f"  Pausing {FORCE_POST_DELAY}s before next post…")
                time.sleep(FORCE_POST_DELAY)

    except Exception as exc:
        log.error(f"Force-post setup failed: {exc}")
        results["failed"] = results["attempted"] or len(unposted)

    return results


# ══════════════════════════════════════════════════════════════════════════════
#  STEP 7 — IMAGE QUALITY CHECK
# ══════════════════════════════════════════════════════════════════════════════

def check_image_quality() -> dict:
    """
    Scan AI_Art for suspiciously small PNGs (likely placeholder or corrupt images).
    Returns a list of bad files and removes their tracker entries so they can be
    re-generated on the next hourly run.
    """
    bad_files = []
    for png in SAVE_DIR.glob("*.png"):
        size_kb = png.stat().st_size // 1024
        if size_kb < MIN_IMAGE_SIZE_KB:
            bad_files.append(png.name)
            log.warning(f"Quality check: small/corrupt image ({size_kb} KB) → {png.name}")

    if bad_files:
        # Remove bad files from the posted tracker so they won't block future posts
        try:
            from instagram_bot import load_tracker, save_tracker
            tracker = load_tracker()
            tracker["posted"] = [f for f in tracker.get("posted", []) if f not in bad_files]
            save_tracker(tracker)
            log.info(f"Removed {len(bad_files)} bad image(s) from posted tracker.")
        except Exception as exc:
            log.warning(f"Could not update tracker for bad images: {exc}")

        # Delete the files themselves
        for fname in bad_files:
            for ext in (".png", "_meta.json"):
                p = SAVE_DIR / (fname.replace(".png", ext))
                try:
                    if p.exists():
                        p.unlink()
                        log.info(f"Deleted bad file: {p.name}")
                except Exception as exc:
                    log.warning(f"Could not delete {p.name}: {exc}")

    return {"bad_files": bad_files, "count": len(bad_files)}


# ══════════════════════════════════════════════════════════════════════════════
#  REPORT
# ══════════════════════════════════════════════════════════════════════════════

def write_report(report: dict) -> None:
    try:
        existing: list = []
        if REPORT_FILE.exists():
            try:
                existing = json.loads(REPORT_FILE.read_text(encoding="utf-8"))
                if not isinstance(existing, list):
                    existing = []
            except Exception:
                existing = []
        existing.append(report)
        REPORT_FILE.write_text(json.dumps(existing[-30:], indent=2), encoding="utf-8")
        log.info(f"Report written → {REPORT_FILE.name}")
    except Exception as exc:
        log.error(f"Failed to write report: {exc}")


def _print_summary(report: dict) -> None:
    h = report["checks"].get("daily_health", {})
    s = report["checks"].get("scheduler", {})
    l = report["checks"].get("logs", {})
    u = report["checks"].get("unposted", {})
    q = report["checks"].get("quality", {})
    f = report["fixes"]

    sep = "-" * 60
    log.info("")
    log.info(sep)
    log.info("  MONITOR SUMMARY")
    log.info(sep)
    log.info(f"  Date             : {h.get('date', '?')}")
    log.info(f"  Generated today  : {h.get('generated_today', '?')}")
    log.info(f"  Posted today     : {h.get('posted_today', '?')} / {h.get('target_daily', 24)} target")
    log.info(f"  Posted yesterday : {h.get('posted_yesterday', '?')}")
    log.info(f"  Unposted total   : {h.get('unposted_total', '?')}")
    log.info(f"  Scheduler state  : {s.get('state', '?')}")
    log.info(f"  Hours since run  : {s.get('hours_since_last_run', '?')}")
    log.info(f"  Log errors       : {l.get('error_count', 0)}")
    log.info(f"  Unposted found   : {u.get('count', 0)}")
    log.info(f"  Bad images found : {q.get('count', 0)}")
    log.info(f"  Force-posted     : {f.get('force_posted', {}).get('succeeded', 0)}")
    log.info(sep)
    if report["overall_healthy"]:
        log.info("  STATUS: HEALTHY — all checks passed")
    else:
        log.info(f"  STATUS: {len(report['issues'])} ISSUE(S) FOUND")
        for issue in report.get("issues", []):
            log.warning(f"    * {issue}")
    log.info(sep)
    log.info("")


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main() -> int:
    now = datetime.now()
    log.info("=" * 65)
    log.info(f"AIArtBot Monitor Agent  —  {now.strftime('%Y-%m-%d %H:%M:%S')}")
    log.info("=" * 65)

    report: dict = {
        "run_at":          now.isoformat(),
        "checks":          {},
        "fixes":           {},
        "overall_healthy": True,
        "issues":          [],
    }

    # ── Step 1: Clear stale locks ──────────────────────────────────────────
    log.info("[1/7]  Checking lock files…")
    cleared = clear_stale_locks()
    report["fixes"]["cleared_locks"] = cleared
    if cleared:
        log.info(f"       Cleared: {cleared}")

    # ── Step 2: Chrome zombie cleanup ──────────────────────────────────────
    log.info("[2/7]  Cleaning up zombie Chrome/ChromeDriver processes…")
    chrome_cleanup = cleanup_zombie_chrome()
    report["fixes"]["chrome_cleanup"] = chrome_cleanup
    log.info(
        f"       Drivers killed: {len(chrome_cleanup['drivers_killed'])}  "
        f"Chrome killed: {len(chrome_cleanup['chrome_killed'])}  "
        f"Locks cleared: {chrome_cleanup['locks_cleared']}"
    )

    # ── Step 3: Scheduler task ─────────────────────────────────────────────
    log.info("[3/7]  Checking scheduler task…")
    sched = check_scheduler()
    report["checks"]["scheduler"] = sched
    log.info(
        f"       State: {sched['state']}  |  "
        f"Last result: {sched['last_result']}  |  "
        f"Since last run: {sched.get('hours_since_last_run', '?')}h"
    )
    if not sched.get("healthy"):
        issue = (
            f"Scheduler '{TASK_NAME}' unhealthy — "
            f"state={sched.get('state')}, last_result={sched.get('last_result')}, "
            f"hours_since_run={sched.get('hours_since_last_run', '?')}"
        )
        report["issues"].append(issue)
        report["overall_healthy"] = False
        fixed = fix_scheduler(sched)
        report["fixes"]["scheduler_reregistered"] = fixed
        if fixed:
            log.info("       Scheduler re-registered.")

    # ── Step 4: Log errors ─────────────────────────────────────────────────
    log.info("[4/7]  Scanning today's logs for errors…")
    log_check = check_logs_for_errors()
    report["checks"]["logs"] = log_check
    log.info(
        f"       Errors: {log_check['error_count']}  "
        f"Critical: {log_check['critical_count']}  "
        f"Warnings: {log_check['warning_count']}"
    )
    if log_check["critical_count"] > 0 or log_check["error_count"] > 15:
        report["issues"].append(
            f"High error rate — {log_check['error_count']} errors, "
            f"{log_check['critical_count']} critical"
        )
        report["overall_healthy"] = False

    # ── Step 5: Daily health ───────────────────────────────────────────────
    log.info("[5/7]  Checking daily generation / post counts…")
    tracker = _load_tracker()
    health  = check_daily_health(tracker)
    report["checks"]["daily_health"] = health
    log.info(f"       Generated today  : {health['generated_today']}")
    log.info(f"       Posted today     : {health['posted_today']} / {EXPECTED_DAILY} target")
    log.info(f"       Posted yesterday : {health['posted_yesterday']}")
    log.info(f"       Unposted total   : {health['unposted_total']}")
    if not health["healthy"]:
        report["issues"].append(
            f"Low post count: {health['posted_today']} posted today "
            f"(target {EXPECTED_DAILY}, minimum {LOW_WATER_MARK})"
        )
        report["overall_healthy"] = False

    # ── Step 6: Unposted images ────────────────────────────────────────────
    log.info("[6/7]  Scanning AI_Art folder for unposted images…")
    unposted = find_unposted_images(tracker)
    report["checks"]["unposted"] = {
        "count": len(unposted),
        "files": [p.name for p in unposted[:20]],
    }
    log.info(f"       Found {len(unposted)} unposted image(s) (older than {MIN_AGE_MINUTES} min).")

    if unposted:
        report["issues"].append(f"{len(unposted)} image(s) not yet posted to Instagram")
        report["overall_healthy"] = False
        _wait_for_artbot()
        capped = min(len(unposted), MAX_FORCE_POSTS)
        log.info(f"       Force-posting up to {capped} image(s)…")
        post_results = force_post_unposted(unposted)
        report["fixes"]["force_posted"] = post_results
        log.info(
            f"       Result — attempted: {post_results['attempted']}  "
            f"succeeded: {post_results['succeeded']}  "
            f"failed: {post_results['failed']}"
        )
    else:
        log.info("       All images are posted — nothing to recover.")

    # ── Step 7: Image quality check ────────────────────────────────────────
    log.info("[7/7]  Checking image quality…")
    quality = check_image_quality()
    report["checks"]["quality"] = quality
    if quality["count"] > 0:
        report["issues"].append(
            f"{quality['count']} corrupt/placeholder image(s) found and removed"
        )
        report["overall_healthy"] = False
        log.warning(f"       Removed {quality['count']} bad image(s): {quality['bad_files']}")
    else:
        log.info("       All images pass quality check.")

    # ── Summary + report ───────────────────────────────────────────────────
    _print_summary(report)
    write_report(report)

    return 0 if report["overall_healthy"] else 1


if __name__ == "__main__":
    sys.exit(main())
