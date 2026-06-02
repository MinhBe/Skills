# Granularity Guide — Branch vs Leaf Rules

## The Core Question

Before splitting, ask: **"If I taught this as one unit, would the learner be able to hold the whole thing?"**

- Yes → Leaf. Teach it as one node.
- No, because it contains distinct independent mechanisms → Split into children.

A branch is not a concept. It is a container. Only leaves get 3-tier explanations, misconception seeds, and transfer questions.

---

## Decision Table

| Signal in transcript | Action |
|---|---|
| "Có N loại / cách / bước / nguyên tắc / model" | N leaf nodes |
| "N types / ways / steps / methods / strategies" | N leaf nodes |
| "First … Second … Third …" (enumeration) | Each item = leaf |
| "1. … 2. … 3. …" numbered list | Each item = leaf |
| ≥ 2 distinct mechanisms that can fail independently | Split |
| ≥ 2 distinct use cases with different conditions | Split |
| Concept name requires "and" to describe | Split |
| Named framework (e.g. "Monastic Model", "SMART goals") | Leaf per named item |
| One mechanism + one story + one application | Leaf — do not split |
| Story or analogy with no independent mechanism | Leaf — store in anchor_story |
| Sub-point is "evidence for" not "alternative to" | Keep as part of parent leaf |
| Cannot be taught without the parent | Keep as part of parent leaf |

---

## Depth Limits

- **depth_level 1**: Top-level concept or framework. Often a branch.
- **depth_level 2**: Named sub-concept within a framework. Usually a leaf.
- **depth_level 3**: Sub-sub-concept. Rarely needed — reconsider if you reach here frequently.
- **depth_level 4**: Stop. If you need depth 4, re-examine whether depth 1 was actually a leaf.

Maximum useful depth is 3. Deep trees signal over-splitting or poor initial content mapping.

---

## Minimum Yield

Minimum leaf count by source type and length:

| Source type | Short (<500 words) | Medium (500–2000 words) | Long (>2000 words) |
|---|---|---|---|
| YouTube | 3 | 8 | 12 |
| Book summary | 5 | 12 | 20 |
| Article | 3 | 5 | 8 |
| Podcast | 3 | 6 | 10 |

If yield check returns WARN: check whether branch nodes can be further split, or whether the transcript genuinely has low concept density (valid — proceed with fewer nodes).

---

## Examples of Correct Splitting

**Deep Work — 4 Models (branch → 4 leaves)**
```
four_deep_work_models [branch, depth 1]
├── monastic_model      [leaf, depth 2]
├── bimodal_model       [leaf, depth 2]
├── rhythmic_model      [leaf, depth 2]
└── journalist_model    [leaf, depth 2]
```
Why: Each model has distinct application conditions, distinct trade-offs, can be independently misunderstood.

**Deep Work — Time Blocking (leaf)**
```
time_blocking_strategy  [leaf, depth 1]
```
Why: One mechanism (block calendar before others can fill it), one application (protect deep work slots), no independently learnable sub-parts.

---

## Examples of Wrong Splitting

**Wrong:** Splitting "why Deep Work matters" into "economic reason" + "neurological reason" + "historical reason" at depth 2.  
**Why wrong:** These are three arguments for the same claim, not three independent learnable concepts. The learner needs all three to evaluate the claim — splitting prevents that.  
**Correct:** One leaf `why_deep_work_matters` with argument_flow that maps all three.

**Wrong:** Splitting "Myelin Hypothesis" into "what myelin is" + "how deliberate practice grows myelin".  
**Why wrong:** "What myelin is" is definitional background, not a standalone concept. Keep as one leaf; the definition lives in tiers.child.  
**Correct:** One leaf `myelin_hypothesis` with `extracted` covering the full mechanism.

---

## When to Stop Splitting

Stop when the candidate child node:
1. Has no misconceptions of its own (all misconceptions belong to the parent)
2. Has no independent transfer question (you'd have to reference the parent to ask one)
3. Cannot fail independently of its siblings

If all three conditions are met — keep it inside the parent leaf.

---

## Backbone / Load-bearing Concepts

Not all leaf nodes are equally important. Before confirming the tree (Step 2 gate), identify which concepts are **load-bearing** — if removed, other concepts in the tree lose their explanation.

**Backbone node signals:**
- Appears in the source title or explicit thesis statement
- Other concepts reference it as WHY they work (mechanism underpinning other nodes)
- Source explicitly calls it "cơ chế", "lý do cốt lõi", "foundation", "mechanism", "the reason why"
- If you removed it from the tree, learner could memorize the other nodes but not understand them

**Supporting node signals:**
- Adds depth or examples but the other nodes still make sense without it
- Is "evidence for" another node, not "explanation of" another node
- Source discusses it briefly (1–3 lines vs. 10+ lines)

**Example from Deep Work:**
```
Myelin Hypothesis [BACKBONE] — explains WHY deliberate practice builds skill
  → All 4 models + time blocking + chain method are applications of this mechanism
  → Without this node, learner treats the 4 models as arbitrary tips, not grounded principles

Why Deep Work matters [BACKBONE] — motivation layer; without it, models lack context

4 Deep Work models [BRANCH + BACKBONE] — the primary structural content

Time Blocking, Chain Method, Shutdown Ritual [SUPPORTING] — implementation tactics
  → Valuable, but learner can understand Deep Work without these
```

**Backbone verification at Step 2:**
After content_mapper produces the tree, ask:
1. Does the source title promise N items? Are all N present?
2. Is there a mechanism node (explains WHY) — not just WHAT?
3. Is there a motivation node (explains WHY IT MATTERS)?
4. Are there any nodes that other nodes silently depend on but aren't in the tree?

If any answer is "no" → add the missing node before confirming tree.

