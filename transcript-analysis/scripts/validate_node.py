"""
validate_node.py — Validate a knowledge node against required schema before writing.

Usage:
  python validate_node.py --node node.json
  python validate_node.py --demo          # run on built-in valid demo node
  python validate_node.py --demo --verbose
"""

import argparse
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REQUIRED_TOP = [
    "domain", "bloom_target", "depth_level", "parent_concept",
    "source_content", "learner_state", "contradictions"
]
REQUIRED_SOURCE = [
    "source_type", "source_name", "source_section", "trust_level", "flags",
    "argument_flow", "core_question", "extracted", "anchor_story", "falsifiability",
    "tiers", "misconception_seeds", "transfer_question", "dig_deeper_questions",
    "next_actions", "open_questions", "last_reextracted"
]
REQUIRED_TIERS = ["child", "student", "expert"]
REQUIRED_DIG_DEEPER = ["apply", "analyze", "evaluate", "create"]
REQUIRED_LEARNER_STATE = [
    "belief_prior", "bloom_level", "mastery_probability", "consecutive_correct",
    "hint_fails_total", "needs_restructure", "next_review", "personal_misconceptions"
]
VALID_SOURCE_TYPES = {"book", "youtube", "article", "podcast", "other"}
VALID_TRUST_LEVELS = {"EXTRACTED", "INFERRED"}
VALID_BLOOM = {"remember", "understand", "apply", "analyze", "evaluate"}

DEMO_NODE = {
    "domain": "book",
    "bloom_target": "apply",
    "depth_level": 2,
    "parent_concept": "four_deep_work_models",
    "children": [],
    "source_content": {
        "source_type": "youtube",
        "source_name": "Better Book Summaries — Deep Work",
        "source_section": "phút 8–12",
        "trust_level": "INFERRED",
        "flags": ["PERSONAL EXPERIENCE"],
        "argument_flow": "hook → problem → mechanism → example → application",
        "core_question": "Khi nào nên dùng Monastic Model và ai phù hợp nhất?",
        "extracted": "Monastic Model là loại Deep Work triệt để nhất: loại bỏ hoàn toàn mọi shallow obligation để chỉ tập trung vào một mục tiêu duy nhất.",
        "inferred": "Phù hợp nhất với người làm việc sáng tạo độc lập, không phụ thuộc collaboration liên tục.",
        "anchor_story": "Cal Newport nhắc đến Donald Knuth — nhà toán học nổi tiếng không dùng email từ 1990 để tập trung vào nghiên cứu.",
        "falsifiability": "Nếu claim 'loại bỏ hoàn toàn distraction' sai, các ví dụ về Monastic practitioners sẽ cho thấy họ vẫn có regular interruptions. Không tìm được evidence ngược chiều trong transcript.",
        "tiers": {
            "child": "Giống như vào phòng riêng, đóng cửa, chỉ làm một việc cho đến khi xong — không ai được làm phiền.",
            "student": "Monastic Model yêu cầu loại bỏ hoàn toàn shallow commitments để maximize thời gian deep work. Phù hợp khi output chỉ phụ thuộc vào chất lượng tư duy, không phải collaboration.",
            "expert": "Optimal allocation strategy cho knowledge workers với high cognitive leverage và low coordination dependency. Trade-off chính: extreme depth vs social capital erosion."
        },
        "misconception_seeds": [
            "Monastic nghĩa là không giao tiếp với ai bao giờ — sai, chỉ là trong work sessions",
            "Model này áp dụng được cho mọi người — không, cần công việc có high independence"
        ],
        "transfer_question": "Bạn là data scientist cần xây model phức tạp trong 3 tuần. Mô tả cách thiết kế schedule theo Monastic Model và identify 2 loại commitment cần từ chối.",
        "dig_deeper_questions": {
            "apply": "Nếu áp dụng Monastic Model 1 tuần, loại communication nào bạn loại bỏ đầu tiên?",
            "analyze": "So sánh Monastic Model với Bimodal Model — khi nào Monastic tốt hơn?",
            "evaluate": "Monastic Model có trade-offs gì với career growth trong môi trường corporate?",
            "create": "Thiết kế 'Monastic Week' schedule cho một software engineer trong team."
        },
        "next_actions": [
            "Thử 1 ngày monastic: tắt Slack, đóng email, chỉ làm 1 task quan trọng nhất",
            "List 3 shallow commitment có thể loại bỏ trong tháng tới",
            "Đọc interview của Donald Knuth về lý do không dùng email"
        ],
        "open_questions": [
            "Transcript không giải thích cách re-engage với team sau Monastic periods",
            "Chưa rõ threshold nào của collaboration dependency để model này hoạt động"
        ],
        "last_reextracted": "2026-05-14"
    },
    "relations": {
        "prerequisites": ["deep_work_definition"],
        "examples_of": "four_deep_work_models",
        "contrasts_with": ["journalist_model"],
        "supports": ["deep_work_definition"],
        "cross_domain": []
    },
    "learner_state": {
        "belief_prior": None,
        "bloom_level": "remember",
        "mastery_probability": 0.0,
        "consecutive_correct": 0,
        "hint_fails_total": 0,
        "needs_restructure": False,
        "next_review": None,
        "personal_misconceptions": {}
    },
    "contradictions": []
}


def _diacritic_ratio(text: str) -> float:
    """Return fraction of word tokens that lack diacritics.

    Extracts letter-only tokens (Unicode, no punctuation/digits) of 3+ chars.
    A token is 'plain' if it is pure ASCII (no tone marks or vowel modifications).
    A high ratio (>0.50) in Claude-generated fields signals copy-behavior from
    an undiacriticized ASR source. Real undiacriticized Vietnamese runs ~80-90%.
    Legitimate English technical terms in Vietnamese text run ~25-40%.
    """
    import re
    tokens = [m for m in re.findall(r"[^\W\d_]+", text) if len(m) >= 3]
    if not tokens:
        return 0.0
    plain = sum(1 for t in tokens if t.isascii())
    return plain / len(tokens)


_DIACRITIC_THRESHOLD = 0.50
_GENERATED_FIELDS = [
    ("source_content.inferred", lambda sc: sc.get("inferred", "")),
    ("source_content.tiers.child", lambda sc: sc.get("tiers", {}).get("child", "")),
    ("source_content.tiers.student", lambda sc: sc.get("tiers", {}).get("student", "")),
    ("source_content.tiers.expert", lambda sc: sc.get("tiers", {}).get("expert", "")),
    ("source_content.core_question", lambda sc: sc.get("core_question", "")),
    ("source_content.transfer_question", lambda sc: sc.get("transfer_question", "")),
]


def validate(node: dict) -> list[str]:
    errors = []
    warnings = []

    def err(msg: str):
        errors.append(msg)

    def warn(msg: str):
        warnings.append("[WARN] " + msg)

    # Top-level fields
    for f in REQUIRED_TOP:
        if f not in node:
            err(f"MISSING  top-level field: '{f}'")

    # bloom_target
    bt = node.get("bloom_target")
    if bt and bt not in VALID_BLOOM:
        err(f"INVALID  bloom_target='{bt}' — must be one of {sorted(VALID_BLOOM)}")

    # depth_level must be int
    dl = node.get("depth_level")
    if dl is not None and not isinstance(dl, int):
        err(f"INVALID  depth_level: must be int, got {type(dl).__name__}")

    # source_content
    sc = node.get("source_content")
    if not isinstance(sc, dict):
        err("INVALID  source_content: must be an object")
    else:
        for f in REQUIRED_SOURCE:
            if f not in sc:
                err(f"MISSING  source_content.{f}")

        st = sc.get("source_type")
        if st and st not in VALID_SOURCE_TYPES:
            err(f"INVALID  source_content.source_type='{st}' — must be one of {sorted(VALID_SOURCE_TYPES)}")

        tl = sc.get("trust_level")
        if tl and tl not in VALID_TRUST_LEVELS:
            err(f"INVALID  source_content.trust_level='{tl}' — must be EXTRACTED or INFERRED")

        if not sc.get("extracted"):
            err("EMPTY    source_content.extracted — must have actual content")

        tiers = sc.get("tiers", {})
        if isinstance(tiers, dict):
            for t in REQUIRED_TIERS:
                if not tiers.get(t):
                    err(f"MISSING/EMPTY  source_content.tiers.{t}")
        else:
            err("INVALID  source_content.tiers: must be an object")

        dd = sc.get("dig_deeper_questions", {})
        if isinstance(dd, dict):
            for q in REQUIRED_DIG_DEEPER:
                if not dd.get(q):
                    err(f"MISSING/EMPTY  dig_deeper_questions.{q}")
        else:
            err("INVALID  dig_deeper_questions: must be an object")

        seeds = sc.get("misconception_seeds", [])
        if not isinstance(seeds, list) or len(seeds) < 2:
            err("INVALID  misconception_seeds: must be list with >=2 items")
        else:
            seed_text = " ".join(seeds)
            if _diacritic_ratio(seed_text) > _DIACRITIC_THRESHOLD:
                warn("misconception_seeds appears undiacriticized — check for copy-behavior from ASR source")

        if not sc.get("transfer_question"):
            err("EMPTY    source_content.transfer_question")

        # Diacritic check on all generated fields
        for field_name, getter in _GENERATED_FIELDS:
            text = getter(sc)
            if text and _diacritic_ratio(text) > _DIACRITIC_THRESHOLD:
                warn(f"{field_name} appears undiacriticized — Vietnamese text should have full diacritics")

    # learner_state
    ls = node.get("learner_state")
    if not isinstance(ls, dict):
        err("INVALID  learner_state: must be an object")
    else:
        for f in REQUIRED_LEARNER_STATE:
            if f not in ls:
                err(f"MISSING  learner_state.{f}")
        bl = ls.get("bloom_level")
        if bl and bl not in VALID_BLOOM:
            err(f"INVALID  learner_state.bloom_level='{bl}'")

    # contradictions must be list
    if "contradictions" in node and not isinstance(node["contradictions"], list):
        err("INVALID  contradictions: must be an array")

    return errors, warnings


def main():
    parser = argparse.ArgumentParser(description="Validate a knowledge node before writing")
    parser.add_argument("--node", help="Path to node JSON file")
    parser.add_argument("--demo", action="store_true", help="Run on built-in demo node")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    if args.demo:
        node = DEMO_NODE
        print("Validating built-in demo node (should PASS)...\n")
    elif args.node:
        path = Path(args.node)
        if not path.exists():
            print(f"ERROR: File not found: {path}", file=sys.stderr)
            sys.exit(1)
        with open(path, encoding="utf-8") as f:
            try:
                node = json.load(f)
            except json.JSONDecodeError as e:
                print(f"ERROR: Invalid JSON in {path}: {e}", file=sys.stderr)
                sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)

    errors, warnings = validate(node)

    if warnings:
        print(f"  [!]  {len(warnings)} warning(s):\n")
        for w in warnings:
            print(f"     • {w}")
        print()

    if not errors:
        domain = node.get("domain", "?")
        print(f"  ✓  PASS — node is valid  [{domain}]")
        if warnings:
            print("     Warnings above do not block writing — but review before publishing.")
        else:
            print("     Ready to write via write_node.py")
        print()
        sys.exit(0)
    else:
        print(f"  ✗  FAIL — {len(errors)} issue(s):\n")
        for e in errors:
            print(f"     • {e}")
        print()
        sys.exit(1)


if __name__ == "__main__":
    main()
