# Prompts

Prompt assets live in [src/obsidian_agent/prompts](/W:/codex/codex/src/obsidian_agent/prompts).

## Layout

- `system/`: model-facing system instructions
- `output_schemas/`: structured output contracts
- `tasks/`: markdown templates rendered into notes
- `manifest.json`: current prompt asset inventory and version marker

## Versioning

- Current prompt bundle version: `v1`
- Update `manifest.json` whenever a prompt asset is added, removed, or repurposed.
- Keep task templates focused on rendering, not business logic.

## Current Assets

- `system/capture.md`
- `output_schemas/capture.json`
- `tasks/inbox_note.md.tmpl`
- `tasks/review_note.md.tmpl`
- `tasks/weekly_digest.md.tmpl`
