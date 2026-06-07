# SQLi GAN Survey Report Template

Use this Markdown structure for the default output. Write in Vietnamese when the
user is Vietnamese. Keep the report focused on reproduction and minimal edits.

## Executive Summary

- Scope surveyed:
- Best candidate clone per method:
- Dataset replacement readiness:
- Biggest blockers before smoke run:
- Hardware feasibility for 20GB RAM / RTX 3050 4GB:

## Dataset Snapshot

Summarize profiler results for:

| Dataset file | Text column | Label column | Rows | Label distribution | Empty text | Invalid labels | Duplicate notes |
|---|---|---|---:|---|---:|---:|---|

State that profiling is read-only and no training adapter has been created yet.

## Per-Model Survey

Use one subsection per method.

### [Method] - [Chosen Clone]

| Item | Finding |
|---|---|
| Local path | |
| Entrypoint | |
| Original input | |
| Input format/schema | |
| Intermediate data forms | |
| Model input tensor/vector | |
| Generator architecture | |
| Discriminator architecture | |
| Training phases/objectives | |
| Generated output | |
| Decode/evaluate path | |
| Hard-coded blockers | |

Pipeline:

```text
Raw/original data
  -> ...
```

Where the SQLi datasets would enter:

- Required conversion before training:
- Minimal file/config changes:
- What should remain unchanged for reproduction:
- Smoke-run recommendation:

## Cross-Model Comparison

| Method | Original data unit | SQLi replacement unit | Adapter needed | Minimal code change risk | Smoke-run feasibility |
|---|---|---|---|---|---|

## Needed Before Dataset Replacement

List only changes needed before training can run. Do not include performance
upgrades.

## Do Not Change For Reproduction

List architecture/training pieces that should remain as-is during the first
reproduction pass.

## 10 Improvement Directions

### Survey First

1. Tách dataset adapter khỏi training loop: [current evidence / unknowns]
2. Chuẩn hóa schema `text,label,source`: [current evidence / unknowns]
3. SQL tokenizer chung, export riêng từng GAN: [current evidence / unknowns]
4. SeqGAN thay toy `TargetLSTM` bằng SQL token-id: [current evidence / unknowns]
5. LeakGAN `.npy` token-id theo `seq_len/vocab/batch`: [current evidence / unknowns]
6. TextGAN PTB-style corpus files: [current evidence / unknowns]
7. CTGAN feature table instead of raw text: [current evidence / unknowns]

### Accepted Minimal-Change Directions

8. Đưa path/input/config ra CLI hoặc config file.
9. Thêm smoke-run mode cho RTX 3050 4GB: epoch nhỏ, sample nhỏ, batch thấp,
   CPU fallback, không full training mặc định.
10. Giữ hoặc tạo decode mapping để token-id output chuyển ngược thành SQL
    payload đọc được.

## Next Step Before Training

Recommend one next action only. Usually: finish dataset adapter design after
this survey, then run one smoke-run model first.
