# Source Types — Extraction Differences

## Why Source Type Matters

Structure determines what gets extracted and how. A YouTube summary video front-loads conclusions. A book builds an argument over chapters. An academic article leads with method and buries claims in results. The same concept will appear in a different position, at a different trust level, with different evidence quality depending on source type.

Getting the wrong extraction pattern means you either over-trust claims (YouTube speaker opinion treated as research evidence) or under-extract structure (book chapter treated as a single leaf).

---

## YouTube Summary Video

**Typical structure:**  
Hook → Problem framing → N solutions or steps (numbered) → Evidence for each → CTA

**Extraction rules:**
- N numbered solutions/steps = N leaf nodes. This is the primary source of structure — follow the speaker's own enumeration.
- Speaker's personal experience stories → `trust_level: INFERRED`, flag `PERSONAL EXPERIENCE`
- Speaker cites a study or named author → `trust_level: EXTRACTED`, flag `CITED SOURCE`
- Hook and problem framing → part of `argument_flow` on the first leaf, not a separate leaf
- CTA (call to action at end) → `next_actions` on the relevant leaf, not a leaf of its own

**Bloom target default:** `apply` (videos are optimized for behavior change, not deep analysis)

**Common mistake:** Treating the entire video as one concept because the title is one concept ("Deep Work"). The title names the domain (or a branch), not the extractable unit.

**Minimum yield:** 10-min video ≥3 nodes, 30-min ≥8 nodes

---

## Book (Full) or Book Summary Video

**Typical structure:**  
Thesis → Evidence chapters (each chapter = sub-argument) → Conclusion + implications

**Extraction rules:**
- Each chapter or named section = at minimum one leaf, often a branch with children
- Named frameworks or models always split to individual leaves (one per item in the framework)
- Author's personal anecdotes → `anchor_story` on relevant leaf, `flags: ["ANECDOTAL"]`
- Peer-reviewed citations → `flags: ["PEER REVIEWED"]`, higher falsifiability standard
- Book conclusion/synthesis = separate leaf if it contains an argument not in chapters

**Bloom target default:** `analyze` (books build arguments, readers expected to evaluate claim strength)

**Depth guidance:**
- Book title → domain or branch at depth 1
- Major section / chapter theme → branch at depth 1
- Named concept within a chapter → leaf at depth 2
- Sub-mechanism of a concept → leaf at depth 3 (only if independently learnable)

**Minimum yield:** Full book ≥20 leaves, chapter summary ≥5 leaves

---

## Academic Article / Technical Blog Post

**Typical structure:**  
Abstract → Method → Results → Discussion → Limitations

**Extraction rules:**
- Abstract = `core_question` + overview `extracted`
- Method section = mechanism leaf(es) if the method is a learnable concept
- Results = evidence for claims; affects `falsifiability` and `trust_level` of related leaves
- Limitations section = `open_questions` + falsifiability challenge
- Speculation in discussion → `trust_level: INFERRED`, `flags: ["SPECULATIVE"]`

**Bloom target default:** `understand` or `analyze` (articles present evidence; reader must assess)

**Higher falsifiability standard than YouTube/book:**  
For each extracted claim, explicitly state what the article's own results would have needed to show to disprove it. Limitations section often provides this directly.

**Minimum yield:** Short post ≥3 leaves, full article ≥5 leaves

---

## Podcast

**Typical structure:**  
Interview or monologue; often informal and non-linear

**Extraction rules:**
- Identify anchor claims: statements the guest repeats or emphasizes
- Ignore filler, hedging ("I think maybe…"), and tangents
- Named frameworks or tools mentioned = leaf if explained sufficiently; `open_questions` if only mentioned
- `trust_level: INFERRED` unless guest cites explicit source
- `source_section` = timestamp range where concept is discussed

**Bloom target default:** `understand` (podcasts rarely have enough depth for apply/analyze without supplementary reading)

**Minimum yield:** 30-min podcast ≥3 leaves, 60-min ≥6 leaves

---

## Mixed Source (e.g., video that summarizes a book)

Use the **tighter** standard: apply book extraction depth rules, but apply YouTube trust level rules (speaker is summarizing, not the primary source). Add `flags: ["SECONDARY SOURCE"]` to all nodes. If you have access to the primary source, mark claims from the video as `INFERRED` and re-extract from primary as `EXTRACTED`.

---

## Scientific Paper (Hybrid Analysis)

**Typical structure:**  
Abstract → Introduction → Related Work → Methodology → Experiments → Results → Discussion/Conclusion

**Extraction rules (The Hybrid Framework):**
This source type requires a 9-part analysis (Phần A-I) combined with standard leaf extraction.

### Analysis Blueprint (Phần A-I):
- **Phần A: Thông Tin Cơ Bản & Phân Loại**: Metadata + GAN Taxonomy (Type, Family, Divergence).
- **Phần B: Dữ Liệu**: Data Pipeline deep-dive (Dataset, Preprocessing, Features).
- **Phần C: Kiến Trúc Mô Hình**: Architecture Blueprint (Generator/Discriminator details).
- **Phần D: Training Configuration**: Optimizers, Loss Functions, Hyperparameters.
- **Phần E: Beyond Baselines**: Key modifications and "X-Factor" innovation.
- **Phần F: Ablation & Experiments**: Research questions and causal analysis.
- **Phần G: Stability & Mode Collapse**: Countermeasures and observed issues.
- **Phần H: Kết Quả & Đánh Giá**: Quantitative and Qualitative analysis.
- **Phần I: Đánh Giá Cá Nhân**: Strengths, weaknesses, and actionable insights.

### Extraction Rules:
- **Abstract** = `core_question` + overview `extracted`.
- **Methodology** = Primary mechanism leaf nodes.
- **X-Factor** = Must be a standalone leaf node (Depth-1).
- **Results/Discussion** = Influence `falsifiability` and `trust_level` of related leaves.
- **Trust Level**: `EXTRACTED` for methodology and reported results. `INFERRED` for author's discussion/speculation.
- **Bloom target default**: `analyze` or `evaluate`.

**Minimum yield:** Full paper ≥8 leaves, Technical report ≥4 leaves.

---

## Trust Level Decision

| Situation | trust_level |
|---|---|
| Speaker quotes exactly from a document you can verify | EXTRACTED |
| Speaker paraphrases a study or author | EXTRACTED (flag CITED SOURCE) |
| Speaker states their own opinion or experience | INFERRED (flag PERSONAL EXPERIENCE) |
| Claude synthesizes across multiple statements | INFERRED |
| Claim is in source but Claude rephrased significantly | INFERRED |

When in doubt, use INFERRED. It is better to mark a genuine quote as INFERRED than to mark a paraphrase as EXTRACTED.

---

## Language Rules

### Vietnamese with Diacritics

All Claude-generated text must use full Vietnamese diacritics (có dấu), regardless of whether the input source has them.

- `extracted` field: mirror source format — OK if undiacriticized (verbatim quote)
- All other fields: `inferred`, `tiers.*`, `core_question`, `misconception_seeds`, `transfer_question`, `anchor_story`, `falsifiability`, `dig_deeper_questions`, `next_actions` → **phải có dấu**

**Why this matters:** ASR transcripts from YouTube are often undiacriticized. Claude has copy-behavior: when the input lacks diacritics, the output tends to as well. This is a behavioral failure, not a capability gap — Claude can write properly diacriticized Vietnamese. The fix is explicit instruction.

### English Term Preservation

Keep English when:
- Proper nouns: "Deep Work", "Flow state", "Monastic Model"
- Widely-used technical terms with no clean translation: "neuroplasticity", "amygdala", "negativity bias", "HPA axis"
- The speaker or source uses the English term as the primary name (e.g., book titles)
- Translating would cause ambiguity or loss of precision in the domain

Translate when:
- Common vocabulary: "book" → "cuốn sách", "chapter" → "chương", "method" → "phương pháp"
- The Vietnamese term is established and more precise than the English in context
- The term appears only once and translation adds no confusion

**Mixed language is natural and correct** for Vietnamese learners engaging with English-language source material. Do not force either direction.
