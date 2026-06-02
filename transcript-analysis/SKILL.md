---
name: transcript-analysis
description: Extract structured knowledge (JSON nodes) from raw transcripts (books, articles, videos) using a 2-stage learning system.
---

# transcript-analysis

## Workflow

### 1. Setup & Preprocess
- Ensure the domain folder and `knowledge-graph.json` exist.
- If the work involves audio transcription, local LLMs, OCR, VLMs, CUDA/GPU,
  or model-cache checks, delegate runtime inspection to:
  ```bash
  python Skill/model-runtime-advisor/scripts/inspect_runtime.py --workload stt
  ```
- If transcript has timestamps `[MM:SS]`, run:
  ```bash
  python scripts/preprocess_transcript.py --input transcript.txt --output clean.txt
  ```

### 2. Content Mapping (GATE)
Generate the conceptual tree and confirm with the user.
```bash
python scripts/content_mapper.py --input clean.txt --source-type {type}
```
**Gate: Backbone Audit**. Verify load-bearing concepts are in the tree. Reference [references/source-types.md](references/source-types.md) for yield rules.

### 3. Per-Leaf Extraction
For each leaf node, extract details following the schema in [assets/node-schema.json](assets/node-schema.json).
- **Extracted**: Mirror source format.
- **Other fields**: Must use full Vietnamese diacritics. See [references/language-rules.md](references/language-rules.md).
- **Scientific Papers**: Apply the **Hybrid Framework** (Phần A-I). See [references/source-types.md](references/source-types.md).

### 4. Validate & Write
```bash
python scripts/validate_node.py --node {key}.json
python scripts/write_node.py --domain {domain} --concept {key} --node {key}.json
```

### 5. Relations & Dossier
- Map `prerequisites`, `examples_of`, `contrasts_with`.
- Generate the Learning Dossier using [assets/dossier-template.md](assets/dossier-template.md).

---

## Guidelines
- **Granularity**: See [references/granularity-guide.md](references/granularity-guide.md).
- **Language**: All generated Vietnamese MUST have diacritics. See [references/language-rules.md](references/language-rules.md).
- **Source Rules**: Reference [references/source-types.md](references/source-types.md) for specific extraction patterns (YouTube, Book, Academic Paper).
- **Examples**: See [references/extraction-examples.md](references/extraction-examples.md) for a full Deep Work walkthrough.
