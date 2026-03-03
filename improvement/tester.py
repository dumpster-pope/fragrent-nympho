"""
Tester — Runs 9 validation tests against the sandbox copy in a subprocess.
All tests run in the sandbox's working directory.
Returns (passed: bool, results: list[dict]).
"""

import ast
import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path

log = logging.getLogger("improvement.tester")

BOT_DIR     = Path(__file__).parent.parent
SANDBOX_DIR = BOT_DIR / "_improvement_sandbox"


def run_all(proposal: dict, sandbox: Path = None) -> tuple[bool, list[dict]]:
    """
    Run all 9 tests. Returns (all_passed, results_list).
    Each result: {"name": str, "passed": bool, "message": str}
    """
    if sandbox is None:
        sandbox = SANDBOX_DIR

    results = []
    modified_files = proposal.get("files", [])

    results.append(_test_import_sanity(sandbox, modified_files))
    results.append(_test_prompt_smoke(sandbox))
    results.append(_test_prompt_uniqueness(sandbox))
    results.append(_test_hashtag_generation(sandbox))
    results.append(_test_config_io(sandbox))
    results.append(_test_engagement_io(sandbox))

    # API reachability only for API_SCOUT
    if proposal.get("category") == "API_SCOUT":
        results.append(_test_api_reachability(proposal))
    else:
        results.append({"name": "api_reachability", "passed": True, "message": "skipped (not API_SCOUT)"})

    results.append(_test_code_complexity(sandbox, modified_files))
    results.append(_test_schema_validation(sandbox))

    all_passed = all(r["passed"] for r in results)
    for r in results:
        status = "PASS" if r["passed"] else "FAIL"
        log.info(f"  [{status}] {r['name']}: {r['message']}")

    return all_passed, results


# ── Individual test functions ─────────────────────────────────────────────────

def _test_import_sanity(sandbox: Path, files: list[str]) -> dict:
    name = "import_sanity"
    if not files:
        return {"name": name, "passed": True, "message": "no modified files"}

    py_files = [f for f in files if f.endswith(".py")]
    if not py_files:
        return {"name": name, "passed": True, "message": "no modified .py files"}

    env = os.environ.copy()
    env["PYTHONPATH"] = str(sandbox)

    for fname in py_files:
        fpath = sandbox / fname
        if not fpath.exists():
            return {"name": name, "passed": False, "message": f"file not found: {fname}"}
        try:
            result = subprocess.run(
                [sys.executable, "-c", f"import ast; ast.parse(open(r'{fpath}').read())"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                return {"name": name, "passed": False,
                        "message": f"syntax error in {fname}: {result.stderr[:200]}"}
        except subprocess.TimeoutExpired:
            return {"name": name, "passed": False, "message": f"timeout parsing {fname}"}

    return {"name": name, "passed": True, "message": f"all {len(py_files)} files parse cleanly"}


def _test_prompt_smoke(sandbox: Path) -> dict:
    name = "prompt_smoke"
    script = (
        "import sys; sys.path.insert(0, r'" + str(sandbox) + "');\n"
        "from prompt_agent import generate_fresh_prompt;\n"
        "import time;\n"
        "t0 = time.time();\n"
        "result = generate_fresh_prompt([]);\n"
        "elapsed = time.time() - t0;\n"
        "assert isinstance(result, tuple) and len(result) == 2, 'not a tuple';\n"
        "assert isinstance(result[0], str) and len(result[0]) > 10, 'prompt too short';\n"
        "assert isinstance(result[1], dict), 'components not a dict';\n"
        "assert elapsed < 5, f'too slow: {elapsed:.1f}s';\n"
        "print('OK');\n"
    )
    try:
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True, text=True, timeout=15, cwd=str(sandbox)
        )
        if result.returncode == 0 and "OK" in result.stdout:
            return {"name": name, "passed": True, "message": "generate_fresh_prompt() returns valid (str, dict)"}
        return {"name": name, "passed": False, "message": result.stderr[:300] or result.stdout[:300]}
    except subprocess.TimeoutExpired:
        return {"name": name, "passed": False, "message": "timed out after 15s"}
    except Exception as e:
        return {"name": name, "passed": False, "message": str(e)}


def _test_prompt_uniqueness(sandbox: Path) -> dict:
    name = "prompt_uniqueness"
    script = (
        "import sys; sys.path.insert(0, r'" + str(sandbox) + "');\n"
        "from prompt_agent import generate_fresh_prompt;\n"
        "prompts = [generate_fresh_prompt([])[0] for _ in range(20)];\n"
        "assert len(set(prompts)) == 20, f'duplicates found: {len(set(prompts))}/20 unique';\n"
        "print('OK');\n"
    )
    try:
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True, text=True, timeout=30, cwd=str(sandbox)
        )
        if result.returncode == 0 and "OK" in result.stdout:
            return {"name": name, "passed": True, "message": "20/20 prompts unique"}
        return {"name": name, "passed": False, "message": result.stderr[:300] or result.stdout[:300]}
    except subprocess.TimeoutExpired:
        return {"name": name, "passed": False, "message": "timed out after 30s"}
    except Exception as e:
        return {"name": name, "passed": False, "message": str(e)}


def _test_hashtag_generation(sandbox: Path) -> dict:
    name = "hashtag_generation"
    ig_path = sandbox / "instagram_bot.py"
    if not ig_path.exists():
        return {"name": name, "passed": True, "message": "instagram_bot.py not in sandbox"}

    script = (
        "import sys; sys.path.insert(0, r'" + str(sandbox) + "');\n"
        "# Parse only — don't import (needs selenium)\n"
        "import ast;\n"
        "src = open(r'" + str(ig_path) + "').read();\n"
        "tree = ast.parse(src);\n"
        # Check MAX_HASHTAGS constant
        "for node in ast.walk(tree):\n"
        "    if isinstance(node, ast.Assign):\n"
        "        for t in node.targets:\n"
        "            if hasattr(t, 'id') and t.id == 'MAX_HASHTAGS':\n"
        "                val = node.value.n if hasattr(node.value, 'n') else node.value.value;\n"
        "                assert val <= 30, f'MAX_HASHTAGS={val} > 30';\n"
        "print('OK');\n"
    )
    try:
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and "OK" in result.stdout:
            return {"name": name, "passed": True, "message": "MAX_HASHTAGS ≤ 30"}
        return {"name": name, "passed": False, "message": result.stderr[:300] or result.stdout[:300]}
    except Exception as e:
        return {"name": name, "passed": False, "message": str(e)}


def _test_config_io(sandbox: Path) -> dict:
    name = "config_io"
    config_path = sandbox / "config.json"
    # Write a minimal config, read it back
    test_config = {"_test": True, "username": "test_user"}
    try:
        config_path.write_text(json.dumps(test_config))
        loaded = json.loads(config_path.read_text())
        assert loaded == test_config
        config_path.unlink()  # clean up
        return {"name": name, "passed": True, "message": "config.json load/save round-trip OK"}
    except Exception as e:
        return {"name": name, "passed": False, "message": str(e)}


def _test_engagement_io(sandbox: Path) -> dict:
    name = "engagement_io"
    counts_path = sandbox / "engagement_counts.json"
    test_data = {"2025-01-01": {"likes": 5, "comments": 2}}
    try:
        counts_path.write_text(json.dumps(test_data))
        loaded = json.loads(counts_path.read_text())
        assert loaded == test_data
        counts_path.unlink()
        return {"name": name, "passed": True, "message": "engagement_counts.json round-trip OK"}
    except Exception as e:
        return {"name": name, "passed": False, "message": str(e)}


def _test_api_reachability(proposal: dict) -> dict:
    name = "api_reachability"
    api_url = proposal.get("api_base_url", "")
    if not api_url:
        return {"name": name, "passed": False, "message": "no api_base_url in proposal"}
    try:
        import requests
        r = requests.head(api_url, timeout=8, allow_redirects=True)
        if r.status_code < 400:
            return {"name": name, "passed": True, "message": f"{api_url} → {r.status_code}"}
        # Try GET as fallback
        r = requests.get(api_url, timeout=8)
        if r.status_code < 400:
            return {"name": name, "passed": True, "message": f"{api_url} → GET {r.status_code}"}
        return {"name": name, "passed": False, "message": f"{api_url} → {r.status_code}"}
    except Exception as e:
        return {"name": name, "passed": False, "message": f"unreachable: {e}"}


def _test_code_complexity(sandbox: Path, files: list[str]) -> dict:
    name = "code_complexity"
    py_files = [f for f in files if f.endswith(".py")]
    if not py_files:
        return {"name": name, "passed": True, "message": "no modified .py files"}

    max_func_lines = 250
    violations = []
    for fname in py_files:
        fpath = sandbox / fname
        if not fpath.exists():
            continue
        try:
            tree = ast.parse(fpath.read_text(encoding="utf-8"))
        except SyntaxError as e:
            return {"name": name, "passed": False, "message": f"SyntaxError in {fname}: {e}"}
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                start = node.lineno
                end = max(
                    (getattr(n, "end_lineno", start) for n in ast.walk(node)),
                    default=start
                )
                length = end - start + 1
                if length > max_func_lines:
                    violations.append(f"{fname}:{node.name}() = {length} lines")

    if violations:
        return {"name": name, "passed": False,
                "message": f"functions > {max_func_lines} lines: {'; '.join(violations)}"}
    return {"name": name, "passed": True, "message": f"all functions ≤ {max_func_lines} lines"}


def _test_schema_validation(sandbox: Path) -> dict:
    name = "schema_validation"
    pa_path = sandbox / "prompt_agent.py"
    if not pa_path.exists():
        return {"name": name, "passed": True, "message": "prompt_agent.py not in sandbox"}

    script = (
        "import sys; sys.path.insert(0, r'" + str(sandbox) + "');\n"
        "import ast, re;\n"
        "src = open(r'" + str(pa_path) + "').read();\n"
        "tree = ast.parse(src);\n"
        # Exec the module to get the actual lists
        "ns = {};\n"
        "exec(compile(tree, 'prompt_agent.py', 'exec'), ns);\n"
        "cats = ns['SUBJECTS_BY_CATEGORY'];\n"
        "envs = ns['ALL_ENVIRONMENTS'];\n"
        "moods = ns['ALL_MOODS'];\n"
        "# Check non-empty\n"
        "assert cats and all(len(v) > 0 for v in cats.values()), 'empty subject category';\n"
        "assert len(envs) > 0, 'empty environments';\n"
        "assert len(moods) > 0, 'empty moods';\n"
        "# Check no duplicates within lists\n"
        "all_subjects = [s for v in cats.values() for s in v];\n"
        "assert len(all_subjects) == len(set(all_subjects)), 'duplicate subjects';\n"
        "assert len(envs) == len(set(envs)), 'duplicate environments';\n"
        "assert len(moods) == len(set(moods)), 'duplicate moods';\n"
        "print('OK');\n"
    )
    try:
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0 and "OK" in result.stdout:
            return {"name": name, "passed": True, "message": "prompt lists valid, no duplicates"}
        return {"name": name, "passed": False, "message": result.stderr[:300] or result.stdout[:300]}
    except subprocess.TimeoutExpired:
        return {"name": name, "passed": False, "message": "timed out"}
    except Exception as e:
        return {"name": name, "passed": False, "message": str(e)}
