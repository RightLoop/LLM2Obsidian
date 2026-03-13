# LLM2Obsidian

Local-first knowledge ingestion and review workflows for Obsidian.

## Quick Start

1. Create a virtual environment and install dependencies.

```bash
python -m venv .venv
. .venv/Scripts/activate
pip install -e .[dev]
```

2. Copy the environment file.

```bash
copy .env.example .env
```

Recommended defaults:
- `LLM_PROVIDER=deepseek`
- `OBSIDIAN_MODE=auto`

Mode notes:
- `OBSIDIAN_MODE=filesystem` reads and writes directly under `VAULT_ROOT`.
- `OBSIDIAN_MODE=rest` writes to the vault currently opened by Obsidian Local REST API.
- `OBSIDIAN_MODE=auto` prefers REST and falls back to filesystem.

3. Seed the demo vault if you want local sample data.

```bash
python scripts/seed_demo_data.py
```

4. Start the API.

```bash
uvicorn obsidian_agent.app:create_app --factory --reload
```

5. Run static checks.

```bash
ruff check src tests scripts
python -m compileall src scripts
```

## Main Endpoints

- `POST /capture/text`
- `POST /capture/url`
- `POST /capture/clipboard`
- `POST /capture/pdf-text`
- `GET /search`
- `GET /notes/related`
- `POST /review/generate`
- `GET /review/pending`
- `POST /review/{id}/approve`
- `POST /review/{id}/reject`
- `POST /review/{id}/apply`
- `POST /maintenance/reindex`
- `GET /maintenance/orphans`
- `GET /maintenance/duplicates`
- `GET /maintenance/metadata-issues`
- `POST /maintenance/weekly-digest`

## Delivery Notes

- Vault writes go through `ObsidianService` only.
- `DRY_RUN=true` returns action previews for write paths instead of mutating the vault.
- Prompt assets live under `src/obsidian_agent/prompts/` and are tracked by `manifest.json`.

See [docs/operations.md](/W:/codex/codex/docs/operations.md), [docs/api.md](/W:/codex/codex/docs/api.md), and [docs/prompts.md](/W:/codex/codex/docs/prompts.md) for details.
