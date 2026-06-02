# Extraction Examples — Deep Work Walkthrough

This file shows the full pipeline applied to a real transcript: from content mapping to final nodes. Use it as a reference when unsure how to handle structure, granularity, or trust level decisions.

**Source:** YouTube summary video — "Deep Work" by Cal Newport  
**Source type:** youtube  
**Approximate length:** 45 minutes → `long` tier → minimum 12 leaves

---

## Step 1 — Content Mapper Output

Running `python scripts/content_mapper.py --input deep_work_transcript.txt --source-type youtube` on the demo excerpt produces:

```
[BRANCH]  Có 4 Deep Work Models  (c_4_deep_work_models)
  [LEAF  ]    [Item 1 of Có 4 Deep Work Models — label manually]
  [LEAF  ]    [Item 2 of Có 4 Deep Work Models — label manually]
  [LEAF  ]    [Item 3 of Có 4 Deep Work Models — label manually]
  [LEAF  ]    [Item 4 of Có 4 Deep Work Models — label manually]
[LEAF  ]  Deep Work là gì?  (deep_work_l_g)
[LEAF  ]  Tại sao Deep Work quan trọng?  (ti_sao_deep_work_quan_trng)
[LEAF  ]  Myelin Hypothesis  (myelin_hypothesis)
[LEAF  ]  Chiến lược Time Blocking  (chin_lc_time_blocking)
[LEAF  ]  Chain Method (Jerry Seinfeld)  (chain_method_jerry_seinfeld)
[LEAF  ]  Rest Strategy  (rest_strategy)
[LEAF  ]  Shutdown Ritual  (shutdown_ritual)
```

**Yield check:** 8 leaves from demo excerpt alone → PASS for medium tier (minimum 8). Full 45-min video would yield 12+.

**User adjustments before proceeding:**
- Rename `deep_work_l_g` → `deep_work_definition`
- Rename `tin_sao_deep_work_quan_trng` → `why_deep_work_matters`
- Rename branch to `four_deep_work_models`
- Rename item leaves: `monastic_model`, `bimodal_model`, `rhythmic_model`, `journalist_model`

---

## Step 2 — Confirmed Tree

```
deep_work_definition        [leaf, depth 1]
why_deep_work_matters       [leaf, depth 1]
myelin_hypothesis           [leaf, depth 1]
four_deep_work_models       [branch, depth 1]
├── monastic_model          [leaf, depth 2]
├── bimodal_model           [leaf, depth 2]
├── rhythmic_model          [leaf, depth 2]
└── journalist_model        [leaf, depth 2]
time_blocking_strategy      [leaf, depth 1]
chain_method                [leaf, depth 1]
rest_strategy               [leaf, depth 1]
shutdown_ritual             [leaf, depth 1]
```

Total leaves: 11. Total nodes: 12 (11 leaves + 1 branch). Yield check PASS for 45-min video.

---

## Step 3 — Per-Leaf Extraction (Worked Example: monastic_model)

**Locate in transcript:** phút 8–12, section "Có 4 Deep Work Models", item 1.

**Map argument_flow:**  
`definition → who it suits → named example (Knuth) → trade-off`

**Draft node:**

```json
{
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
    "argument_flow": "definition → who it suits → named example → trade-off",
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
    "belief_prior": null,
    "bloom_level": "remember",
    "mastery_probability": 0.0,
    "consecutive_correct": 0,
    "hint_fails_total": 0,
    "needs_restructure": false,
    "next_review": null,
    "personal_misconceptions": {}
  },
  "contradictions": []
}
```

---

## Common Decisions Explained

### Why `trust_level: INFERRED` here?

The video speaker summarizes Newport's book. The speaker's phrasing ("phù hợp nhất với người làm việc sáng tạo độc lập") is an interpretation, not a direct Newport quote. If we had the book text, we'd mark that as EXTRACTED.

### Why is the Knuth story in `anchor_story` not `extracted`?

Anchor story is for episodic memory — it makes the concept stick. Falsifiability doesn't apply to stories (Knuth not using email is a fact, not a falsifiable claim about Monastic Model). Keeping it separate prevents it from being lost during re-extraction.

### Why are "Tại sao Deep Work Quan trọng" and "Deep Work Definition" separate leaves, not one?

- `deep_work_definition` answers "what is it" — mechanism leaf
- `why_deep_work_matters` answers "why care" — motivation leaf

Different core_questions → different misconception seeds → different Socratic entry points. They could be siblings under a `deep_work_overview` branch if yield is high enough, but at 11 nodes they stay at depth 1.

### Why is `four_deep_work_models` a branch with no extraction?

A branch is a container. There is no "what is four_deep_work_models" concept — there are four specific models. Trying to write `extracted` for the branch would require repeating all four models' content. The branch exists only to hold the four leaves and express the tree structure in `children[]`.

---

## Relations Mapping (after all nodes extracted)

```
deep_work_definition
  ← prerequisites for: why_deep_work_matters, myelin_hypothesis, four_deep_work_models, time_blocking_strategy, chain_method, rest_strategy, shutdown_ritual

why_deep_work_matters
  → supports: deep_work_definition

myelin_hypothesis
  → supports: deep_work_definition, why_deep_work_matters
  ← prerequisites for: all model leaves

monastic_model / bimodal_model / rhythmic_model / journalist_model
  → examples_of: four_deep_work_models
  → contrasts_with: each other

time_blocking_strategy, chain_method, rest_strategy, shutdown_ritual
  → supports: four_deep_work_models (these are the implementation tactics)
  → cross_domain: (if math-for-ai has a focus/flow concept, link here)
```
