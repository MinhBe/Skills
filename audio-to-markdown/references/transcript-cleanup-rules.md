# Transcript Cleanup Rules

## Preserve Meaning

- Fix spelling, punctuation, casing, and obvious speech disfluencies.
- Do not invent facts, names, dates, numbers, decisions, or commitments.
- Keep technical terms as spoken when uncertain and add a quality note.
- Mark inaudible or uncertain content with `[unclear]`.

## Speaker Handling

- Preserve diarization labels from STT when present.
- If no diarization exists, use `Speaker 1`, `Speaker 2`, etc. only when turns
  are clear from the transcript.
- Do not infer real participant names unless the audio or transcript states them.
- Put uncertain speaker attribution in quality notes.

## Style

- Convert filler-heavy speech into readable prose only in summary sections.
- Keep transcript section close to the original wording.
- For Vietnamese or mixed Vietnamese/English audio, preserve domain terms and
  code-switching instead of over-translating.

## Verification Flags

Add quality notes for:

- Low confidence segments.
- Background noise or overlapping speech.
- Missing diarization.
- Proper nouns, acronyms, numbers, URLs, and dates that may need review.
- Any fallback path that skipped normalization or STT.
