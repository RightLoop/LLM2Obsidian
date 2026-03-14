# Phase E/F Final Acceptance

Generated on: 2026-03-14

## Scope

This round used real providers only:

- DeepSeek API full replay: `output/quality-tuning-rounds/20260314-174957-deepseek-quality-replay.json`
- Ollama local model full replay: `output/quality-tuning-rounds/20260314-174957-ollama-quality-replay.json`
- DeepSeek post-fix spot check: `output/quality-tuning-rounds/20260314-175943-deepseek-quality-replay.json`
- Ollama post-fix spot check: `output/quality-tuning-rounds/20260314-180031-ollama-quality-replay.json`

The replay set is the fixed 24-sample C-language regression corpus in
`tests/fixtures/quality_tuning/c_language_error_samples.json`.

## What Changed

This phase closed two goals:

1. Unified language and node style
   - Error extraction now emits clean Simplified Chinese fallback content.
   - Support node titles were expanded into stable Chinese knowledge-card labels.
   - Concept reuse no longer collapses different Chinese titles into the same node.

2. Established real replay acceptance
   - Replays now run in isolated sqlite/vector/vault sandboxes by default.
   - Replay artifacts include provider-specific filenames to avoid overwrite.
   - The full 24-sample set was executed against both DeepSeek and the local `Qwen14B-fixed:latest`.

## Real Findings

### DeepSeek

- Full 24-sample replay completed successfully.
- Average expected-concept coverage across the corpus: `0.792`
- Quality after tuning is clearly better on:
  - `sizeof vs strlen`
  - `arr vs &arr`
  - `function parameter decay`
  - `char* vs char[]`
- Remaining issue pattern:
  - the model still likes to add adjacent concepts beyond the expected minimum set
  - this raises recall, but also introduces some extra noise

### Ollama (`Qwen14B-fixed:latest`)

- Full 24-sample replay completed successfully.
- Average expected-concept coverage across the corpus: `0.625`
- The local model still frequently returns extremely short structured output (`{}`-like responses).
- Current quality is acceptable only because the fallback path is now much stronger.
- Practical conclusion:
  - local Ollama is good enough as a low-cost structured-first pass
  - DeepSeek remains the better provider for higher-fidelity extraction

## Verified Fixes

The final spot checks confirmed these issues are now fixed with real outputs:

- `sizeof(arr)` samples now recover `sizeof / strlen / null-terminator` correctly.
- `arr` vs `&arr` no longer reuses unrelated null-terminator nodes.
- `char*` vs `char[]` no longer collapses into duplicate `char*` support nodes.
- Support node titles such as `内存分配容量` and `字符串结尾空字符` now follow the Chinese knowledge-card style.

## Residual Issues

These are no longer blockers, but they are the next quality targets:

- DeepSeek still injects some extra adjacent concepts beyond the expected set.
- Ollama structured extraction is unstable enough that fallback quality matters more than model quality.
- Title wording is now clearer, but still not close enough to use exact-string title matching as a regression metric.

## Release Judgment

Phase E/F is complete.

The system now has:

- a real replay-based tuning loop
- a stable Chinese output baseline
- provider-backed validation with both DeepSeek and local Ollama
- materially lower node/relink noise than the earlier rounds

Recommended next step:

- keep DeepSeek as the preferred extraction provider
- keep Ollama as the local fallback path
- start a new tuning round focused on:
  - trimming DeepSeek extra-concept noise
  - improving Ollama JSON compliance
  - adding stronger corpus-level scoring beyond concept coverage
