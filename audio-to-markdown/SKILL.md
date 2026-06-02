---
name: audio-to-markdown
description: Convert audio recordings into structured Markdown with normalized audio, local-first speech-to-text, transcript cleanup, speaker/participant inference, summary, key points, recommendations, action items, and quality notes. Use when the user asks to transcribe audio, create meeting notes or minutes from recordings, summarize interviews or lectures from audio, or turn voice recordings into Markdown.
---

# Audio To Markdown

Create a usable, quality-gated Markdown document from audio, not just a raw
transcript.

## Workflow

1. If the user did not force local or cloud, run
   `python Skill\model-runtime-advisor\scripts\inspect_runtime.py --workload stt`
   first. Use its verdict to choose a pipeline.
2. Normalize audio with `scripts/normalize_audio.py` when `ffmpeg` is available:
   mono, 16 kHz, stable volume, WAV output.
3. Run STT:
   - Prefer installed local `faster-whisper`.
   - Fall back to installed OpenAI Whisper.
   - If no local STT engine exists, ask before installing or using a cloud API.
4. For long audio, use chunked transcription. Retry/fallback should be recorded
   per model/chunk; do not silently switch engines.
5. Run quality checks before analysis:
   - `usable`: render full notes.
   - `needs_review`: render full notes with warnings.
   - `failed_stt_quality_gate`: render only failure report, raw sample, metrics,
     fallback attempts, and rerun guidance.
6. Repair common Vietnamese mojibake (for example `Ã`, `Ä`, `áº`, `á»`, `Æ`,
   or replacement characters) when confidence is high or medium, and note the
   repair in quality notes.
7. Clean transcript using `references/transcript-cleanup-rules.md`.
8. Apply the output schema from `assets/audio-markdown-template.md`.
9. Use `references/summary-profiles.md` for profile-specific formatting.
10. Include quality notes: uncertain words, missing speakers, noisy audio,
   dependency gaps, and whether the transcript needs human review.

## Commands

```powershell
python Skill\model-runtime-advisor\scripts\inspect_runtime.py --workload stt --audio-minutes 90
python Skill\audio-to-markdown\scripts\audio_to_markdown.py --input recording.mp3 --output recording.md --profile meeting
python Skill\audio-to-markdown\scripts\audio_to_markdown.py --input recording.m4a --output notes.md --profile research_meeting --emit-analysis --language vi
python Skill\audio-to-markdown\scripts\normalize_audio.py --input recording.m4a --output normalized.wav
python Skill\audio-to-markdown\scripts\audio_to_markdown.py --input recording.wav --transcript existing.txt --output notes.md
```

## Defaults

- Use `profile=general` unless the request says meeting, minutes, action items,
  participants, decisions, or follow-up.
- Use `profile=research_meeting` for meetings with an advisor/supervisor,
  thesis guidance, research critique, or lab-review recordings.
- Treat `model-runtime-advisor` as the owner of hardware, CUDA/GPU, `ffmpeg`,
  STT package, and model-cache checks.
- Prefer local STT when the advisor reports `local-ready` or `local-limited` and
  the needed engine is already installed.
- Do not install packages, download models, or call cloud APIs without user
  approval.
- Default local fallback order is `faster-whisper medium`, `faster-whisper small`,
  `faster-whisper large-v3` if cached/available, then installed OpenAI Whisper.
- If transcription cannot run, produce a quality failure report with metadata,
  pipeline status, missing items, fallback attempts, and next steps.

## Output Requirements

The final Markdown should include:

- Metadata and pipeline configuration.
- Quality status and quality metrics.
- Participants or speaker labels when available or inferable.
- Edited transcript with timestamps when STT supplies them.
- Summary.
- Key points.
- Recommendations.
- Action items.
- Risks, open questions, and quality notes.

When the transcript is machine-generated, avoid presenting uncertain text as
perfect. Mark unclear spans with `[unclear]` or a quality note.

For `failed_stt_quality_gate`, do not generate full summary, key points,
recommendations, or action items. The output should be a clear failure report
with enough evidence to decide how to rerun transcription.

For `research_meeting`, include advisor questions, required revisions, weak
points raised, unanswered questions, next actions, next meeting checklist, and
evidence-based action items when quality does not fail.

Action items should include owner, timestamp, evidence sentence, and confidence.
Do not use `Unassigned` as the default owner. Use `Student` when a speaker can
be inferred from phrases like "em phải", "cần", "lần sau", "giải thích", or
"chuẩn bị"; otherwise use `Unclear`.
