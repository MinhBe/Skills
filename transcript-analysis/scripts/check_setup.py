"""
check_setup.py — Verify environment before running transcript-analysis skill.

Usage:
  python check_setup.py
  python check_setup.py --domain book
  python check_setup.py --quiet
"""

import argparse
import importlib
import json
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

EXHIBIT_ROOT = Path(r"C:\Projects\Dashboard\5. Exhibit")
KNOWN_DOMAINS = ["mandarin", "math-for-ai", "ai-concept", "skill-creator", "book"]

G = "\033[92m"   # green
Y = "\033[93m"   # yellow
R = "\033[91m"   # red
X = "\033[0m"    # reset

results: list[tuple[str, str, str]] = []


def chk(status: str, name: str, detail: str = ""):
    results.append((status, name, detail))


def python_version():
    v = sys.version_info
    if v >= (3, 10):
        chk("PASS", f"Python {v.major}.{v.minor}.{v.micro}", ">=3.10 required")
    else:
        chk("FAIL", f"Python {v.major}.{v.minor}.{v.micro}",
            "Need Python >=3.10 — upgrade your Python installation")


def stdlib_modules():
    for mod in ["json", "pathlib", "argparse", "datetime", "shutil", "tempfile"]:
        try:
            importlib.import_module(mod)
            chk("PASS", f"stdlib: {mod}", "")
        except ImportError:
            chk("FAIL", f"stdlib: {mod}", "Should always be available — check your Python installation")


def exhibit_root():
    if EXHIBIT_ROOT.exists():
        chk("PASS", "5. Exhibit root", str(EXHIBIT_ROOT))
    else:
        chk("FAIL", "5. Exhibit root",
            f"Path not found: {EXHIBIT_ROOT}\nCreate it or adjust EXHIBIT_ROOT in this script")


def domain_path(domain: str):
    path = EXHIBIT_ROOT / domain
    graph = path / "knowledge-graph.json"

    if not path.exists():
        chk("FAIL", f"Domain: {domain}",
            f"Folder not found: {path}\nCreate it first")
        return

    if not graph.exists():
        chk("FAIL", f"Domain: {domain} graph",
            f"knowledge-graph.json missing at: {graph}")
        return

    try:
        with open(graph, encoding="utf-8") as f:
            data = json.load(f)
        node_count = len(data.get("nodes", {}))
        chk("PASS", f"Domain: {domain}", f"{node_count} node(s) in graph")
    except json.JSONDecodeError as e:
        chk("FAIL", f"Domain: {domain} graph", f"Invalid JSON: {e}")


def optional_tool(name: str, test_cmd: list[str], install_hint: str):
    try:
        result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            version = result.stdout.strip().split("\n")[0][:60]
            chk("WARN_OK", f"Optional: {name}", version)
        else:
            chk("WARN", f"Optional: {name}", install_hint)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        chk("WARN", f"Optional: {name}", install_hint)


def print_results(quiet: bool):
    print(f"\n{'='*58}")
    print("  transcript-analysis  SETUP CHECK")
    print(f"{'='*58}\n")

    fail_count = warn_count = 0

    for status, name, detail in results:
        if status == "FAIL":
            fail_count += 1
            color = R
            tag = "FAIL"
        elif status == "WARN":
            warn_count += 1
            color = Y
            tag = "WARN"
        else:
            color = G
            tag = "PASS"

        if quiet and status not in ("FAIL", "WARN"):
            continue

        print(f"  {color}[{tag}]{X}  {name}")
        if detail:
            for line in detail.split("\n"):
                print(f"         {line}")

    print(f"\n{'='*58}")
    if fail_count == 0 and warn_count == 0:
        print(f"  {G}All checks passed. Ready to extract.{X}\n")
    elif fail_count == 0:
        print(f"  {Y}{warn_count} warning(s). Optional tools missing — core is ready.{X}\n")
    else:
        print(f"  {R}{fail_count} failure(s). Fix FAIL items before proceeding.{X}\n")

    return fail_count


def main():
    parser = argparse.ArgumentParser(description="Verify setup for transcript-analysis skill")
    parser.add_argument("--domain", help="Also verify this specific domain path")
    parser.add_argument("--quiet", action="store_true", help="Only show FAIL and WARN")
    args = parser.parse_args()

    python_version()
    stdlib_modules()
    exhibit_root()

    if args.domain:
        domain_path(args.domain)
    else:
        for d in KNOWN_DOMAINS:
            domain_path(d)

    optional_tool(
        "yt-dlp",
        ["yt-dlp", "--version"],
        "pip install yt-dlp  (for downloading YouTube transcripts)"
    )
    optional_tool(
        "faster-whisper",
        ["python", "-c", "import faster_whisper; print(faster_whisper.__version__)"],
        "pip install faster-whisper  (for audio transcription)"
    )

    fail_count = print_results(args.quiet)
    sys.exit(1 if fail_count > 0 else 0)


if __name__ == "__main__":
    main()
