# Model Scan Checklist

Use this checklist while surveying each cloned GAN repository. Keep findings
grounded in local code paths and avoid recommending model upgrades.

## Files To Inspect

For each candidate clone, inspect these file types in order:

1. README, usage notes, clone manifest notes.
2. Entrypoint: `main.py`, `train.py`, notebook, CLI, or package module.
3. Dataloader and preprocessing: files named `data*`, `loader*`, `encode*`,
   `preprocess*`, `utils*`.
4. Config: JSON, flags, constants, hard-coded file names.
5. Model definitions: generator, discriminator, target/oracle, rollout,
   sampler, decoder.
6. Output/evaluation: sample generation, decode, BLEU, loss print, checkpoint.

## Input Contract Fields

Record these fields for every surveyed clone:

- Method and clone path.
- Chosen entrypoint and command shown by repo.
- Original dataset path or default file names.
- Input data type: CSV, text file, token-id text file, `.npy`, `DataFrame`,
  tensor, or synthetic oracle.
- Raw schema: column names, labels, discrete/continuous columns, line format.
- Intermediate format after preprocessing.
- Model input shape and dtype.
- Vocabulary assumptions: special tokens, max vocab, unknown token, start/end
  token, padding.
- Sequence assumptions: `seq_len`, truncation, padding, batch size, dropped last
  batch behavior.
- Output format: generated token ids, text, table rows, checkpoints, metrics.
- Hard-coded assumptions that block dataset replacement.

## Pipeline Trace Format

Use this compact style for each model:

```text
Raw data
  -> preprocessing step: data form after step
  -> model input step: tensor/vector form
  -> training step: loss/objective used
  -> generation step: output form
  -> decode/evaluate step: readable form or metric
```

Name exact file/function references when they matter for minimal changes.

## Method-Specific Prompts

Use these questions while reading code:

- CTGAN: Does the code expect `pandas.DataFrame` or ndarray? Which columns are
  discrete? How are continuous columns transformed? Is text valid input or does
  it need feature extraction first?
- SeqGAN: Does the code train on synthetic oracle data or real data? Does the
  dataloader read space-separated integer token ids? Where are `VOCAB_SIZE`,
  `g_sequence_len`, `POSITIVE_FILE`, and sample output defined?
- TextGAN: Does the code expect corpus files split into train/valid/test? How
  is vocab built? Does TensorFlow version constrain reproduction?
- LeakGAN: Does the dataloader read `.npy` arrays? Which config files define
  `vocab_size`, `seq_len`, `batch_size`, generated sample count, and file paths?

## Minimal Change Rules

- Prefer a separate adapter script over editing model internals.
- Prefer changing config/path constants over changing training logic.
- Keep the original generator/discriminator architecture unchanged unless it
  cannot accept any dataset-compatible input.
- For the laptop target, recommend smoke-run values before full training values.
- Mark ideas as "survey first" when the current code has not yet proven them
  necessary.
