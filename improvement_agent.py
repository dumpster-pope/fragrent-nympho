"""
Improvement Agent — Autonomous improvement loop for AIArtBot.

Runs every 6 hours (via Task Scheduler). Each cycle:
  1. Lock check
  2. Regression check
  3. Triage / category selection
  4. Research
  5. Proposal generation
  6. Complexity gate (HIGH → manual queue)
  7. Sandbox + test suite (9 tests)
  8. Deploy on pass / discard on fail
  9. Teardown + logging

CLI:
  python improvement_agent.py run
  python improvement_agent.py status
  python improvement_agent.py review
  python improvement_agent.py approve <id>
  python improvement_agent.py rollback
"""

import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────

BOT_DIR       = Path(__file__).parent
IMP_DIR       = BOT_DIR / "improvement"
LOCK_FILE     = BOT_DIR / "improvement.lock"
LOG_FILE      = IMP_DIR / "improvement_log.json"
STATE_FILE    = IMP_DIR / "improvement_state.json"
PENDING_FILE  = IMP_DIR / "pending_proposals.json"

IMP_DIR.mkdir(exist_ok=True)

# ── Logging ───────────────────────────────────────────────────────────────────

LOG_DIR = BOT_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)-28s  %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / "improvement_agent.log", encoding="utf-8"),
    ],
)
log = logging.getLogger("improvement_agent")

# ── Constants ─────────────────────────────────────────────────────────────────

LOCK_MAX_AGE   = 4 * 3600   # 4 hours
LOG_MAX_CYCLES = 100
CATEGORIES     = ["PROMPT_EXPAND", "API_SCOUT", "ENGAGEMENT_TUNE", "BUG_FIX", "FEATURE_PROPOSE"]


# ── Lock management ───────────────────────────────────────────────────────────

def _acquire_lock() -> bool:
    if LOCK_FILE.exists():
        age = time.time() - LOCK_FILE.stat().st_mtime
        if age < LOCK_MAX_AGE:
            log.warning(f"Lock file exists and is {age/3600:.1f}h old — aborting")
            return False
        log.info("Stale lock file found — removing")
    LOCK_FILE.write_text(str(os.getpid()))
    return True


def _release_lock() -> None:
    if LOCK_FILE.exists():
        LOCK_FILE.unlink()


# ── Log helpers ───────────────────────────────────────────────────────────────

def _load_log() -> list[dict]:
    if LOG_FILE.exists():
        try:
            return json.loads(LOG_FILE.read_text())
        except Exception:
            pass
    return []


def _save_log(cycles: list[dict]) -> None:
    LOG_FILE.write_text(json.dumps(cycles[-LOG_MAX_CYCLES:], indent=2))


def _load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {cat: {"last_run": 0, "last_deploy_commit": None} for cat in CATEGORIES}


def _save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2))


def _load_pending() -> list[dict]:
    if PENDING_FILE.exists():
        try:
            return json.loads(PENDING_FILE.read_text())
        except Exception:
            pass
    return []


def _save_pending(proposals: list[dict]) -> None:
    PENDING_FILE.write_text(json.dumps(proposals, indent=2))


# ── Category runner ───────────────────────────────────────────────────────────

def _run_category(category: str) -> dict | None:
    """Run the appropriate category handler and return a proposal."""
    if category == "PROMPT_EXPAND":
        from improvement.categories.prompt_expander import run
    elif category == "API_SCOUT":
        from improvement.categories.api_scout import run
    elif category == "ENGAGEMENT_TUNE":
        from improvement.categories.engagement_tuner import run
    elif category == "BUG_FIX":
        from improvement.categories.bug_fixer import run
    elif category == "FEATURE_PROPOSE":
        from improvement.categories.feature_proposer import run
    else:
        log.error(f"Unknown category: {category}")
        return None
    return run()


# ── Main cycle ────────────────────────────────────────────────────────────────

def run_cycle() -> dict:
    """Execute a full improvement cycle. Returns cycle summary dict."""
    cycle_id  = str(uuid.uuid4())[:8]
    started   = datetime.utcnow().isoformat() + "Z"
    log.info(f"=== Improvement cycle {cycle_id} started ===")

    cycle = {
        "cycle_id":   cycle_id,
        "started":    started,
        "finished":   None,
        "categories": [],
        "proposals":  [],
        "deployed":   [],
        "failed":     [],
        "skipped":    [],
        "error":      None,
    }

    # ── Step 1: Lock ──────────────────────────────────────────────────────────
    if not _acquire_lock():
        cycle["error"] = "lock_active"
        cycle["finished"] = datetime.utcnow().isoformat() + "Z"
        return cycle

    try:
        # ── Step 2: Regression check ──────────────────────────────────────────
        from improvement.rollback import check_and_rollback
        if check_and_rollback():
            log.warning("Rolled back last improvement commit — skipping this cycle")
            cycle["error"] = "regression_rollback"
            return cycle

        # ── Step 3-4: Triage + category selection ─────────────────────────────
        from improvement.analyzer import select_categories
        selected, state = select_categories(n=2)
        cycle["categories"] = selected
        log.info(f"Categories selected: {selected}")

        # ── Step 5-12: Per-category loop ──────────────────────────────────────
        for category in selected:
            log.info(f"--- Processing {category} ---")
            proposal = None
            try:
                # Research + proposal
                proposal = _run_category(category)
            except Exception as e:
                log.error(f"Category {category} failed: {e}")
                cycle["failed"].append({"category": category, "reason": str(e)})
                continue

            if proposal is None:
                log.info(f"No proposal generated for {category}")
                cycle["skipped"].append(category)
                state.setdefault(category, {})["last_run"] = time.time()
                continue

            proposal["category"] = category
            proposal["id"] = str(uuid.uuid4())[:8]
            cycle["proposals"].append({"id": proposal["id"], "category": category,
                                        "description": proposal.get("description", "")})

            # ── Step 8: Complexity gate ────────────────────────────────────────
            complexity = proposal.get("complexity", "LOW").upper()
            manual     = proposal.get("manual_review_required", False)
            files      = proposal.get("files", [])

            if complexity == "HIGH" or manual or len(files) >= 3:
                log.info(f"HIGH complexity or manual flag — queuing for manual review")
                pending = _load_pending()
                pending.append(proposal)
                _save_pending(pending)
                cycle["skipped"].append(f"{category}(HIGH→manual)")
                state.setdefault(category, {})["last_run"] = time.time()
                continue

            # ── Step 9: Sandbox ────────────────────────────────────────────────
            from improvement import sandbox as sb
            sandbox_path = None
            try:
                sandbox_path = sb.create()
                applied = sb.apply_changes(proposal, sandbox_path)
                if not applied:
                    log.warning(f"Failed to apply changes for {category}")
                    cycle["failed"].append({"category": category, "reason": "apply_failed"})
                    state.setdefault(category, {})["last_run"] = time.time()
                    continue

                # ── Step 10: Test suite ────────────────────────────────────────
                from improvement.tester import run_all
                all_passed, results = run_all(proposal, sandbox_path)
                pass_count = sum(1 for r in results if r["passed"])
                log.info(f"Tests: {pass_count}/9 passed")

                # ── Step 11: Deploy or reject ──────────────────────────────────
                if all_passed:
                    from improvement.deployer import deploy
                    commit = deploy(proposal, sandbox_path)
                    if commit:
                        log.info(f"Deployed {category} → {commit}")
                        cycle["deployed"].append({"category": category,
                                                   "commit": commit,
                                                   "description": proposal.get("description", "")})
                        state.setdefault(category, {})["last_run"]            = time.time()
                        state.setdefault(category, {})["last_deploy_commit"]  = commit
                    else:
                        log.error(f"Deploy failed for {category}")
                        cycle["failed"].append({"category": category, "reason": "deploy_failed"})
                else:
                    failed_tests = [r["name"] for r in results if not r["passed"]]
                    log.warning(f"Tests failed for {category}: {failed_tests}")
                    cycle["failed"].append({"category": category,
                                            "reason": f"tests_failed: {failed_tests}"})
                    state.setdefault(category, {})["last_run"] = time.time()

            finally:
                # ── Step 12: Teardown ──────────────────────────────────────────
                sb.teardown()

        # Save updated state
        _save_state(state)

    except Exception as e:
        log.error(f"Cycle error: {e}", exc_info=True)
        cycle["error"] = str(e)
    finally:
        _release_lock()

    cycle["finished"] = datetime.utcnow().isoformat() + "Z"
    log.info(
        f"=== Cycle {cycle_id} done — "
        f"deployed={len(cycle['deployed'])}, "
        f"failed={len(cycle['failed'])}, "
        f"skipped={len(cycle['skipped'])} ==="
    )

    # Persist log
    cycles = _load_log()
    cycles.append(cycle)
    _save_log(cycles)

    return cycle


# ── CLI ───────────────────────────────────────────────────────────────────────

def cmd_run() -> None:
    cycle = run_cycle()
    print(json.dumps(cycle, indent=2))


def cmd_status(n: int = 5) -> None:
    cycles = _load_log()
    if not cycles:
        print("No cycles recorded yet.")
        return
    for c in cycles[-n:]:
        deployed = ", ".join(d["category"] for d in c.get("deployed", [])) or "none"
        failed   = ", ".join(f["category"] for f in c.get("failed",   [])) or "none"
        print(
            f"[{c.get('started','?')[:19]}]  {c['cycle_id']}  "
            f"deployed={deployed}  failed={failed}  err={c.get('error') or '-'}"
        )


def cmd_review() -> None:
    pending = _load_pending()
    if not pending:
        print("No pending proposals.")
        return
    for p in pending:
        print(f"  [{p.get('id', '?')}] {p.get('category', '?')}: {p.get('description', '')}")
        if p.get("feature_name"):
            print(f"           Feature: {p['feature_name']}")
        if p.get("approach"):
            print(f"           Approach: {p['approach'][:120]}")
        print()


def cmd_approve(proposal_id: str) -> None:
    pending = _load_pending()
    match = [p for p in pending if p.get("id") == proposal_id]
    if not match:
        print(f"No proposal with id '{proposal_id}'")
        return

    proposal = match[0]
    complexity = proposal.get("complexity", "HIGH").upper()

    if complexity == "HIGH" or proposal.get("manual_review_required"):
        # Force complexity down for manual approval
        proposal["complexity"] = "MEDIUM"
        proposal.pop("manual_review_required", None)

    files = proposal.get("files", [])
    if not files:
        print("Proposal has no files to apply — cannot approve")
        return

    print(f"Approving: [{proposal['id']}] {proposal.get('description', '')}")

    from improvement import sandbox as sb
    sandbox_path = sb.create()
    try:
        applied = sb.apply_changes(proposal, sandbox_path)
        if not applied:
            print("Failed to apply changes to sandbox")
            return

        from improvement.tester import run_all
        all_passed, results = run_all(proposal, sandbox_path)
        for r in results:
            status = "PASS" if r["passed"] else "FAIL"
            print(f"  [{status}] {r['name']}: {r['message']}")

        if all_passed:
            from improvement.deployer import deploy
            commit = deploy(proposal, sandbox_path)
            if commit:
                print(f"Deployed → {commit}")
                pending = [p for p in pending if p.get("id") != proposal_id]
                _save_pending(pending)
            else:
                print("Deploy failed")
        else:
            print("Tests failed — not deployed")
    finally:
        sb.teardown()


def cmd_rollback() -> None:
    from improvement.rollback import manual_rollback
    ok = manual_rollback()
    print("Rolled back last improvement commit." if ok else "No improvement commit found.")


def main() -> None:
    args = sys.argv[1:]
    if not args or args[0] == "run":
        cmd_run()
    elif args[0] == "status":
        n = int(args[1]) if len(args) > 1 else 5
        cmd_status(n)
    elif args[0] == "review":
        cmd_review()
    elif args[0] == "approve":
        if len(args) < 2:
            print("Usage: improvement_agent.py approve <id>")
            sys.exit(1)
        cmd_approve(args[1])
    elif args[0] == "rollback":
        cmd_rollback()
    else:
        print(f"Unknown command: {args[0]}")
        print("Usage: improvement_agent.py [run|status|review|approve <id>|rollback]")
        sys.exit(1)


if __name__ == "__main__":
    main()
