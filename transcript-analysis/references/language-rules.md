# Language Rules — Vietnamese & English

## Vietnamese with Diacritics (Tiếng Việt Có Dấu)

All Claude-generated text MUST use full Vietnamese diacritics (có dấu), regardless of whether the input source has them. This is critical because ASR transcripts (from YouTube/Podcasts) often lack diacritics, and mirroring that lack makes the knowledge base unprofessional and hard to read.

### Fields to Diacriticize:
- `inferred`: Synthesis and summaries.
- `tiers.child`, `tiers.student`, `tiers.expert`: Explanations.
- `core_question`: Entry point question.
- `misconception_seeds`: Learning challenges.
- `transfer_question`, `anchor_story`, `falsifiability`, `dig_deeper_questions`, `next_actions`.
- **Dossier content**: Summary, Table of Contents, and Metadata.

### Exception:
- `extracted` field: Mirror source format exactly. If the source quote is undiacriticized, keep it as is to maintain faithfulness to the raw data.

---

## English Term Retention

Keep English terms when they represent proper nouns, domain standards, or technical concepts that lose precision when translated.

### Rules for Retention:
1. **Proper Nouns**: Book titles ("Deep Work"), method names ("HEAL method"), framework names ("Flow state").
2. **Scientific/Technical Terms**: "neuroplasticity", "amygdala", "HPA axis", "negativity bias".
3. **Domain Standards**: "Mode collapse", "Wasserstein distance", "GAN", "Transformer".
4. **Ambiguity Prevention**: If a Vietnamese translation sounds forced, unnatural, or breaks recognition in the professional community, keep the English term.

### Rules for Translation:
1. **Common Vocabulary**: "book" → "cuốn sách", "chapter" → "chương", "method" → "phương pháp".
2. **Established Equivalents**: "learning" → "học tập", "logic" → "lập luận".

---

## Vietnamese Prose Review (Substep 7.5)

Before finalizing any output, perform this review:

### 7.5a — Diacritic Sweep
Scan all generated fields. Check for common ASR-mirroring errors:
- `nao bo` → `não bộ`
- `toan bo` → `toàn bộ`
- `cam xuc` → `cảm xúc`
- `hoc tap` → `học tập`

### 7.5b — English Retention Audit
If a term is kept in English, ensure it is added to the **Thuật ngữ** table in the dossier if it appears ≥3 times.

### 7.5c — Grammar & Tone
- Ensure sentences are complete (subject + verb).
- Use logical connectives ("Do đó...", "Cụ thể là...").
- Maintain an explanatory (not just instructional) tone.
- `tiers.child` must be jargon-free and analogy-driven.
