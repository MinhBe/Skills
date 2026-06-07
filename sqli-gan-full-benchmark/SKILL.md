---
name: sqli-gan-full-benchmark
description: Run or plan full-dataset SQLi GAN clone benchmarks for the retained 18-clone pipeline. Use this skill whenever the user asks to repeat the Modified_SQL_Dataset full benchmark flow on sqli.csv, sqliv2.csv, SQLiV3_normalize.csv, or another SQLi CSV dataset; includes prepare/validate/smoke-clones/modernize-legacy/metrics/WAF/report/timeline workflow, acceptance checks, and observation-only WAF constraints.
---

# SQLi GAN Full Benchmark

Use this skill to replicate the proven full-dataset benchmark workflow from
`clone_smoke_18_modified_full` onto another SQLi dataset. The workflow is
designed for the retained 18 clone set under `D:\GAN_Final\Product\GAN_Methods`.

## Core Rules

- Do not edit raw datasets or clone model core files.
- Do not optimize generated payloads from WAF outcomes; WAF is observation-only.
- Use CSV `prefixed_raw_generated_payload` for WAF input, never raw JSONL audit.
- Treat `SQLiV3_normalize.csv` as a cleaned derivative; do not rewrite `SQLiV3.csv`.
- Use `--full` for full dataset runs and record `actual_rows` as `N`.

## Dataset Selection

Read `references/remaining-datasets.md` when choosing among the remaining
datasets or when adding adapter source specs.

Default remaining full-run targets:

| Dataset | Source name | Run id |
|---|---|---|
| `sqli.csv` | `sqli.csv` | `clone_smoke_18_sqli_full` |
| `sqliv2.csv` | `sqliv2.csv` | `clone_smoke_18_sqliv2_full` |
| `SQLiV3_normalize.csv` | `SQLiV3_normalize.csv` | `clone_smoke_18_sqliv3_normalized_full` |

Before running `SQLiV3_normalize.csv`, confirm the adapter has a `SourceSpec`
for that exact source name. If not, add the source spec and a focused adapter
test first.

## Run Workflow

Run from `D:\GAN_Final\Product\GAN_Methods`.

1. Prepare and validate:

```powershell
python -m sqli_smoke_pipeline.cli prepare --run-id <RUN_ID> --source <SOURCE_NAME> --full
python -m sqli_smoke_pipeline.cli validate --run-id <RUN_ID>
```

2. Read `N = prepare_summary.actual_rows`.

3. Generate all retained clone outputs:

```powershell
python -m sqli_smoke_pipeline.cli smoke-clones --run-id <RUN_ID> --scope survey23 --max-records <N> --mode standard --timeout-min 30
python -m sqli_smoke_pipeline.cli modernize-legacy --run-id <RUN_ID> --max-records <N> --timeout-seconds 300
python -m sqli_smoke_pipeline.cli metrics --run-id <RUN_ID> --benchmark offline --max-records <N>
```

4. Run WAF if Docker/ModSecurity is ready:

```powershell
python -m sqli_smoke_pipeline.cli waf status --target modsecurity-local
python -m sqli_smoke_pipeline.cli waf-benchmark --run-id <RUN_ID> --target modsecurity-local --max-records <18*N>
python -m sqli_smoke_pipeline.cli report --run-id <RUN_ID> --include-clone-matrix
```

For long `smoke-clones`, `metrics`, or `waf-benchmark` runs, launch the command
in the background with logs under `<run>/command_logs/` and poll process/artifact
status. Do not start duplicate runs while an existing process is active.

## Acceptance Checks

After each full run:

- `reports/clone_status_matrix.csv`: 18 rows, all `passed_generated`, all
  `generated_rows=N`.
- `reports/metrics_summary.csv`: 18 rows, all `row_count=N`,
  `prefix_coverage=1.0`, `jsonl_raw_audit_coverage=1.0`.
- `waf/modsecurity_input_payloads.csv`: `18*N` rows if WAF completed.
- `waf/modsecurity_code_summary.csv`: 18 rows with per-clone
  `block_rate` and `bypass_rate`.
- `waf/modsecurity_benchmark_manifest.json`: status `completed`, or a precise
  blocked/failed status if Docker/WAF is unavailable.

Use the bundled acceptance checker when artifacts exist:

```powershell
python D:\GAN_Final\.skill\sqli-gan-full-benchmark\scripts\check_full_run_acceptance.py `
  --run-root D:\GAN_Final\Product\GAN_Methods\Runs\sqli_clone_benchmark\<RUN_ID> `
  --expected-rows <N> `
  --expect-waf
```

## Timeline Updates

When a run completes or is blocked, update:

- `Timeline/Recovery.md`
- `Timeline/sqli_gan_timeline.md`
- `Timeline/sqli_gan_timeline_events.csv`
- The relevant improvement document under `Timeline/`.

Record dataset source, usable row count, clone count, metrics status, WAF input
row count, WAF unique probes, per-code summary path, and any blocked reason.
