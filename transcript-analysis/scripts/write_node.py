"""
write_node.py — Safe atomic write of a knowledge node to knowledge-graph.json.

Usage:
  python write_node.py --domain book --concept monastic_model --node node.json
  python write_node.py --domain ai-concept --concept gradient_descent --node node.json --mode update
  python write_node.py --list --domain book     # list existing nodes

Modes:
  add    (default) — fail if concept already exists (forces explicit intent)
  update           — merge: keep existing learner_state, replace source_content
"""

import argparse
import json
import sys
import tempfile
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

EXHIBIT_ROOT = Path(r"C:\Projects\Dashboard\5. Exhibit")

# validate_node is a sibling script — import its validate function
sys.path.insert(0, str(Path(__file__).parent))
try:
    from validate_node import validate
    VALIDATOR_AVAILABLE = True
except ImportError:
    VALIDATOR_AVAILABLE = False


def load_graph(domain: str) -> dict:
    path = EXHIBIT_ROOT / domain / "knowledge-graph.json"
    if not path.exists():
        print(f"ERROR: knowledge-graph.json not found at {path}", file=sys.stderr)
        print(f"       Run check_setup.py first to verify domain paths.", file=sys.stderr)
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_graph(domain: str, graph: dict):
    path = EXHIBIT_ROOT / domain / "knowledge-graph.json"
    # Atomic write: write to temp file then rename
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent,
        suffix=".tmp", delete=False
    ) as tmp:
        json.dump(graph, tmp, ensure_ascii=False, indent=2)
        tmp_path = Path(tmp.name)
    tmp_path.replace(path)


def diff_summary(old_node: dict | None, new_node: dict) -> list[str]:
    lines = []
    if old_node is None:
        lines.append("  + New node added")
        sc = new_node.get("source_content", {})
        lines.append(f"    source: {sc.get('source_name', '?')} [{sc.get('source_type', '?')}]")
        lines.append(f"    section: {sc.get('source_section', '?')}")
        lines.append(f"    depth_level: {new_node.get('depth_level', '?')}")
        lines.append(f"    bloom_target: {new_node.get('bloom_target', '?')}")
        seeds = sc.get("misconception_seeds", [])
        lines.append(f"    misconception_seeds: {len(seeds)}")
    else:
        lines.append("  ~ Node updated")
        old_sc = old_node.get("source_content", {})
        new_sc = new_node.get("source_content", {})
        if old_sc.get("extracted") != new_sc.get("extracted"):
            lines.append("    ↻ source_content.extracted changed")
        if old_sc.get("tiers") != new_sc.get("tiers"):
            lines.append("    ↻ source_content.tiers changed")
        if old_sc.get("misconception_seeds") != new_sc.get("misconception_seeds"):
            lines.append("    ↻ misconception_seeds changed")
        lines.append("    ✓ learner_state preserved from existing node")
    return lines


def main():
    parser = argparse.ArgumentParser(description="Write a knowledge node to knowledge-graph.json")
    parser.add_argument("--domain", help="Target domain (e.g. book, ai-concept)")
    parser.add_argument("--concept", help="Snake_case concept key (e.g. monastic_model)")
    parser.add_argument("--node", help="Path to node JSON file")
    parser.add_argument("--mode", choices=["add", "update"], default="add",
                        help="add: fail if exists | update: merge with existing")
    parser.add_argument("--list", action="store_true", help="List existing nodes in domain")
    parser.add_argument("--skip-validate", action="store_true",
                        help="Skip schema validation (not recommended)")
    args = parser.parse_args()

    if not args.domain:
        parser.print_help()
        sys.exit(1)

    graph = load_graph(args.domain)

    # --list mode
    if args.list:
        nodes = graph.get("nodes", {})
        if not nodes:
            print(f"No nodes in domain '{args.domain}' yet.")
        else:
            print(f"\nNodes in '{args.domain}' ({len(nodes)} total):\n")
            for key, node in nodes.items():
                bl = node.get("learner_state", {}).get("bloom_level", "?")
                bt = node.get("bloom_target", "?")
                dl = node.get("depth_level", "?")
                sc = node.get("source_content", {})
                src = sc.get("source_name", "?")
                print(f"  {key}")
                print(f"    depth={dl}  bloom={bl}/{bt}  source={src}")
        return

    if not args.concept or not args.node:
        print("ERROR: --concept and --node are required for write operations.", file=sys.stderr)
        sys.exit(1)

    # Load node JSON
    node_path = Path(args.node)
    if not node_path.exists():
        print(f"ERROR: Node file not found: {node_path}", file=sys.stderr)
        sys.exit(1)

    with open(node_path, encoding="utf-8") as f:
        try:
            new_node = json.load(f)
        except json.JSONDecodeError as e:
            print(f"ERROR: Invalid JSON in {node_path}: {e}", file=sys.stderr)
            sys.exit(1)

    # Validate
    if not args.skip_validate and VALIDATOR_AVAILABLE:
        errors = validate(new_node)
        if errors:
            print(f"  ✗  VALIDATION FAILED — {len(errors)} issue(s):\n")
            for e in errors:
                print(f"     • {e}")
            print(f"\n  Fix the node JSON first, or use --skip-validate to bypass.\n")
            sys.exit(1)
        print("  ✓  Validation passed")
    elif not VALIDATOR_AVAILABLE:
        print("  ⚠  validate_node.py not found — skipping validation")

    # Ensure domain matches
    if new_node.get("domain") and new_node["domain"] != args.domain:
        print(f"ERROR: node.domain='{new_node['domain']}' does not match --domain='{args.domain}'", file=sys.stderr)
        sys.exit(1)

    nodes = graph.setdefault("nodes", {})
    existing = nodes.get(args.concept)

    if args.mode == "add" and existing is not None:
        print(f"  ✗  FAIL — concept '{args.concept}' already exists in '{args.domain}'.")
        print(f"     Use --mode update to replace source_content while keeping learner_state.")
        print(f"     Use --list to see all existing nodes.\n")
        sys.exit(1)

    if args.mode == "update" and existing is not None:
        # Preserve learner_state from existing node
        new_node["learner_state"] = existing.get("learner_state", new_node.get("learner_state", {}))
        # Preserve existing contradictions
        existing_contradictions = existing.get("contradictions", [])
        if existing_contradictions:
            new_node["contradictions"] = existing_contradictions + new_node.get("contradictions", [])

    diff = diff_summary(existing, new_node)
    nodes[args.concept] = new_node
    save_graph(args.domain, graph)

    print(f"\n  Written: {args.domain} / {args.concept}")
    for line in diff:
        print(line)

    total = len(nodes)
    print(f"\n  Graph now has {total} node(s) in '{args.domain}'.")
    print(f"  Path: {EXHIBIT_ROOT / args.domain / 'knowledge-graph.json'}\n")


if __name__ == "__main__":
    main()
