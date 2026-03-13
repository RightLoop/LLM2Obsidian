# Operations

## Required Settings

- `VAULT_ROOT`: local filesystem vault root for filesystem mode and local fallbacks
- `OBSIDIAN_MODE`: `filesystem`, `rest`, or `auto`
- `OBSIDIAN_API_URL`: required for `rest` or `auto`
- `OBSIDIAN_API_KEY`: required for authenticated Obsidian Local REST API access
- `LLM_PROVIDER`: `deepseek`, `openai`, or `auto`
- `DEEPSEEK_API_KEY` or `OPENAI_API_KEY`: provider credential

## Runtime Behavior

- `OBSIDIAN_MODE=filesystem` writes directly under `VAULT_ROOT`.
- `OBSIDIAN_MODE=rest` writes to the vault currently opened by Obsidian.
- `OBSIDIAN_MODE=auto` prefers REST and falls back to filesystem if REST calls fail.
- `DRY_RUN=true` returns planned write actions instead of mutating notes.
- HTTP integrations use bounded retries and configurable timeout settings.

## Recommended Local Workflow

1. Copy `.env.example` to `.env`.
2. Set `LLM_PROVIDER=deepseek`.
3. Set `OBSIDIAN_MODE=auto`.
4. Set `OBSIDIAN_API_URL`, `OBSIDIAN_API_KEY`, and `VAULT_ROOT`.
5. Run `python scripts/seed_demo_data.py` if you want sample notes.
6. Start the API with `uvicorn obsidian_agent.app:create_app --factory --reload`.
7. Call `/maintenance/reindex` before search or related-note checks.

## Dry-Run Semantics

- Capture endpoints return `action_preview` when Inbox note creation is skipped.
- `POST /review/{id}/apply` returns `status=dry_run` with a preview when note mutation is skipped.
- `POST /maintenance/weekly-digest` returns `status=dry_run` with a preview when digest creation is skipped.

## Verification

- `ruff check src tests scripts --select F,E9,B`
- `python -m compileall src scripts`
- Run targeted smoke requests against your local vault or the demo vault.
