# Learning Dossier — {source_name}

**Domain:** {domain}  
**Source type:** {source_type}  
**Extracted:** {extraction_date}  
**Total nodes:** {total_nodes} ({branch_count} branches, {leaf_count} leaves)

---

## Tổng hợp

{opening_context_1_to_3_sentences}

{source_name} là {content_type} về {topic} từ {author_or_channel}. Luận điểm cốt lõi là {one_sentence_thesis}. Dossier này cover {leaf_count} concepts, trọng tâm là {backbone_node_1}, {backbone_node_2}, và {backbone_node_3}. Sau khi học, bạn có thể {capability_verb} {specific_outcome}.

---

## Mục lục

<!-- Luôn generate, kể cả khi < 6 nodes. Mục lục là bắt buộc. -->
<!-- ý chính = 1 câu bài học / takeaway (câu TRẢ LỜI, không phải câu HỎI) -->

1. **{concept_key}** — {y_chinh_1_cau} _({bloom_target})_
2. **{concept_key}** — {y_chinh_1_cau} _({bloom_target})_

---

## Concept Tree

```
{tree_ascii}
```

---

## Nodes

<!-- Repeat this block for each leaf node, ordered by depth then position in source -->

---

### {concept_key} · depth {depth_level}

**Parent:** {parent_concept}  
**Bloom target:** {bloom_target}  
**Source section:** {source_section}  
**Trust:** {trust_level} {flags}

**Core question:**  
{core_question}

**Argument flow:**  
{argument_flow}

**Extracted:**  
{extracted}

**Inferred (if any):**  
{inferred}

**Anchor story:**  
{anchor_story}

**Falsifiability:**  
{falsifiability}

---

#### Three-tier explanation

**Child (analogy):**  
{tiers.child}

**Student (mechanism):**  
{tiers.student}

**Expert (trade-offs):**  
{tiers.expert}

---

#### Misconception seeds

- {misconception_seeds[0]}
- {misconception_seeds[1]}
<!-- add more if present -->

**Transfer question:**  
{transfer_question}

---

#### Dig deeper

| Level | Question |
|---|---|
| Apply | {dig_deeper_questions.apply} |
| Analyze | {dig_deeper_questions.analyze} |
| Evaluate | {dig_deeper_questions.evaluate} |
| Create | {dig_deeper_questions.create} |

---

#### Next actions

1. {next_actions[0]}
2. {next_actions[1]}
<!-- add more if present -->

**Open questions left unresolved by source:**  
- {open_questions[0]}

---

#### Relations

- **Prerequisites:** {relations.prerequisites}
- **Examples of:** {relations.examples_of}
- **Contrasts with:** {relations.contrasts_with}
- **Supports:** {relations.supports}
- **Cross-domain:** {relations.cross_domain}

---

<!-- end node block -->

---

## Yield Summary

| Check | Value |
|---|---|
| Source type | {source_type} |
| Word count | {word_count} |
| Tier | {yield_tier} (short/medium/long) |
| Minimum required | {minimum_yield} |
| Actual leaf nodes | {leaf_count} |
| Status | {yield_status} |

---

## Thuật ngữ

<!-- Optional section. Chỉ include nếu có ≥3 English terms được giữ nguyên. -->
<!-- Mục đích: document quyết định giữ tiếng Anh hay dịch để đảm bảo consistency trong Socratic session. -->

| Thuật ngữ | Giữ tiếng Anh vì | Tương đương tiếng Việt (nếu có) |
|---|---|---|
| {english_term} | {reason: proper noun / no clean translation / domain standard} | {viet_equivalent_or_none} |

---

## Next Steps

- [ ] Run `python scripts/validate_node.py --node {concept_key}.json` for each node
- [ ] Run `python scripts/write_node.py --domain {domain} --concept {concept_key} --node {concept_key}.json` for each node
- [ ] Map `relations` across all nodes once extraction is complete
- [ ] First Socratic session: `next_review` = extraction date (review immediately)
