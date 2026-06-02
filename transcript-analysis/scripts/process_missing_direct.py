"""
process_missing_direct.py — Process missing transcripts by importing
content_mapper and preprocess_transcript modules directly (avoiding
subprocess encoding issues on Windows).
"""

import json
import sys
from pathlib import Path

# Add scripts dir to path so we can import the modules
SCRIPTS_DIR = Path(
    r"C:\Projects\Dashboard\6. Vault\Skill\transcript-analysis\scripts"
)
sys.path.insert(0, str(SCRIPTS_DIR))

sys.stdout.reconfigure(encoding="utf-8")

# Direct import of skill modules
import preprocess_transcript
import content_mapper

SOURCE_DIR = Path(r"C:\Projects\Dashboard\1. Capture\Better_Version")
CLEAN_DIR = SOURCE_DIR / "clean"
TREE_DIR = SOURCE_DIR / "trees"
OUTPUT_DIR = Path(r"C:\Projects\Dashboard\4. Blueprint\Books")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Known missing files - find them by checking which md files lack a tree
all_md = sorted(SOURCE_DIR.glob("*_Fast.md"))
missing = []
for md_path in all_md:
    base_name = md_path.stem
    tree_path = TREE_DIR / f"{base_name}.tree.json"
    if not tree_path.exists():
        missing.append(md_path)

print(f"Found {len(missing)} files without tree files.\n")

count_ok = 0
for md_path in missing:
    base_name = md_path.stem
    clean_path = CLEAN_DIR / f"{base_name}.txt"
    tree_path = TREE_DIR / f"{base_name}.tree.json"
    video_title = base_name.replace("_Fast", "").replace("_", " ")

    print(f"Processing: {base_name[:70]}...", flush=True)

    # Step 1.5: Preprocess — read file, preprocess, write clean
    try:
        raw_text = md_path.read_text(encoding="utf-8")
        cleaned = preprocess_transcript.preprocess(raw_text)
        clean_path.write_text(cleaned, encoding="utf-8")
        print(f"  Preprocessed OK ({len(cleaned.split())} words)", flush=True)
    except Exception as e:
        print(f"  PREPROCESS ERROR: {e}", flush=True)
        continue

    # Step 2: Content mapper — run in-process, capture output
    try:
        word_count = len(cleaned.split())
        source_type = "youtube"

        # Build tree
        nodes = content_mapper.build_tree(cleaned, source_type)
        leaf_count = content_mapper.count_leaves(nodes)

        # Title hint parsing
        title_n = 0
        title_hint = ""
        if video_title:
            title_n, title_hint = content_mapper.parse_title_hint(video_title)

        # Minimum yield check
        min_nodes_override = None
        if title_n:
            min_nodes_override = title_n

        if min_nodes_override:
            minimum = min_nodes_override
            status = "PASS" if leaf_count >= minimum else "WARN"
            detail = f"{leaf_count} leaves {'>=' if status == 'PASS' else '<'} {minimum} (from title)"
        else:
            status, detail = content_mapper.yield_check(
                leaf_count, source_type, word_count
            )

        result = {
            "source_type": source_type,
            "word_count": word_count,
            "estimated_leaf_nodes": leaf_count,
            "title_hint_n": title_n if title_n else None,
            "minimum_yield_check": f"{status}: {detail}",
            "tree": [n.to_dict() for n in nodes],
        }

        tree_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(
            f"  OK — {leaf_count} leaves, {word_count} words [{status}]",
            flush=True,
        )
        count_ok += 1

    except Exception as e:
        print(f"  MAPPER ERROR: {e}", flush=True)
        import traceback

        traceback.print_exc()
        continue

print(f"\n{'='*60}")
print(f"Done: {count_ok}/{len(missing)} trees generated successfully.")

# Now re-run dossier generation for these new files
if count_ok > 0:
    print(f"\nRe-running dossier generation for new files...\n")

    # Import the generate_dossiers module
    sys.path.insert(0, str(SCRIPTS_DIR))
    import generate_dossiers

    success = 0
    for md_path in missing:
        base_name = md_path.stem
        tree_path = TREE_DIR / f"{base_name}.tree.json"
        if not tree_path.exists():
            continue

        dossier = generate_dossiers.generate_dossier(base_name, md_path)
        if dossier is None:
            continue

        video_title = generate_dossiers.extract_video_title(base_name)
        safe_name = generate_dossiers.sanitize_filename(video_title)
        out_path = OUTPUT_DIR / f"{safe_name}.md"

        counter = 1
        while out_path.exists():
            out_path = OUTPUT_DIR / f"{safe_name}_{counter}.md"
            counter += 1

        out_path.write_text(dossier, encoding="utf-8")
        success += 1
        print(f"  Dossier written: {out_path.name}")

    print(f"\nGenerated {success} new dossiers.")
