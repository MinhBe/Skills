---
name: sqli-gan-survey
description: Survey cloned GAN repositories for SQL injection reproduction before modifying or training them. Use this skill when the user asks to inspect CTGAN, SeqGAN, TextGAN, or LeakGAN code for original input contracts, data pipeline steps, intermediate data formats, minimal dataset replacement changes, smoke-run feasibility, or how the Modified_SQL_Dataset and Kaggle_SQL_Injection_Dataset would fit into the cloned code without upgrading model architecture.
---

# SQLi GAN Survey

Use this skill to produce a reproduction-oriented survey report before changing
GAN code or transforming datasets. The goal is to understand the cloned code as
it is, identify the least invasive places to replace the dataset, and keep the
work focused on reproducibility rather than model improvement.

## Default Scope

Survey only these method folders unless the user expands scope:

- `D:\GAN_Final\Product\GAN_Methods\CTGAN`
- `D:\GAN_Final\Product\GAN_Methods\SeqGAN`
- `D:\GAN_Final\Product\GAN_Methods\TextGAN`
- `D:\GAN_Final\Product\GAN_Methods\LeakGAN`

Treat these SQLi datasets as the replacement candidates:

- `D:\GAN_Final\Product\Dataset\Modified_SQL_Dataset\Modified_SQL_Dataset.csv`
- `D:\GAN_Final\Product\Dataset\Kaggle_SQL_Injection_Dataset\sqli.csv`
- `D:\GAN_Final\Product\Dataset\Kaggle_SQL_Injection_Dataset\sqliv2.csv`
- `D:\GAN_Final\Product\Dataset\Kaggle_SQL_Injection_Dataset\SQLiV3.csv`

Hardware assumption for feasibility notes: laptop with about 20GB RAM and RTX
3050 4GB VRAM. Recommend CPU fallback, small batch sizes, tiny epoch counts, and
smoke runs. Do not recommend full training as the default next action.

## Workflow

1. Read the repo manifest if present, especially
   `D:\GAN_Final\Product\GAN_Methods\clone_manifest.md`, to identify cloned
   variants and likely entrypoints.
2. For each of the 4 method folders, choose the most reproducible local clone
   before surveying deeply. Prefer clones with clear README, entrypoint,
   dataloader/config, and generator/discriminator code.
3. Inspect, in this order:
   - README or usage notes
   - main training entrypoint
   - dataloader/preprocessing code
   - config or hard-coded constants
   - generator and discriminator definitions
   - sample/decode/evaluate scripts
4. Record the original input contract exactly:
   file path, column names, text format, numeric format, tensor shape, dtype,
   vocabulary assumptions, `seq_len`, batch assumptions, labels, and generated
   output format.
5. Trace the original pipeline step by step. For every step, name the data form,
   for example CSV, plain text lines, token-id lines, `.npy`, `DataFrame`,
   one-hot/continuous matrix, `LongTensor`, logits, sampled token ids, decoded
   text.
6. Compare the original input contract with the SQLi datasets. Explain where the
   new datasets can enter the pipeline and what conversion would be needed
   before training.
7. Identify minimal reproduction changes only. Prefer dataset adapter, config
   path, smoke-run flags, and decode mapping changes. Avoid architecture changes,
   new objectives, new evaluators, or performance tuning unless the user asks.
8. Write the final report in Markdown using
   `references/survey-report-template.md`.

## Required Report Decisions

Always separate these three categories:

- **Observed from code**: facts directly found in local files.
- **Needed before dataset replacement**: transformations or config changes that
  must happen before training can run.
- **Do not change for reproduction**: original architecture or training logic
  that should be preserved to keep the survey reproduction-focused.

If a fact is not discoverable from code, mark it as unknown and say which file
or experiment would resolve it.

## Minimal-Change Improvement Policy

Include these 10 directions in the report. Mark 1-7 as "survey first" and do not
present them as accepted implementation changes until the code survey supports
them. Mark 8-10 as accepted minimal-change directions.

1. Survey whether dataset adapter logic can be separated from the training loop.
2. Survey whether an internal `text,label,source` schema is enough for all four
   methods.
3. Survey whether one SQL tokenizer can feed method-specific export formats.
4. Survey whether SeqGAN can replace toy `TargetLSTM` data with SQL token-id
   data while preserving training logic.
5. Survey whether LeakGAN can consume SQL token-id `.npy` with its fixed
   `seq_len`, `vocab_size`, and batch behavior.
6. Survey whether TextGAN requires PTB-style `train/valid/test.txt` corpus files.
7. Survey whether CTGAN should receive tabular SQL features instead of raw text.
8. Move hard-coded paths and input settings into CLI arguments or config files.
9. Add a smoke-run mode for RTX 3050 4GB: tiny epochs, small sample count, small
   batch, CPU fallback, and no full training by default.
10. Preserve or create decode mapping so token-id outputs can be converted back
    into readable SQL payloads.

## Dataset Profiling

Before proposing dataset conversions, run the read-only profiler when useful:

```powershell
python D:\GAN_Final\.skill\sqli-gan-survey\scripts\profile_sqli_datasets.py
```

The profiler prints row counts, inferred text/label columns, label
distribution, empty text, invalid labels, and duplicates. It does not create
training adapters and does not modify source datasets.

## Resources

- Read `references/model-scan-checklist.md` before inspecting model code.
- Use `references/survey-report-template.md` as the default report structure.
- Use `scripts/profile_sqli_datasets.py` for dataset schema/quality profiling.
- Use `scripts/self_test.py` to sanity-check the skill resources.
