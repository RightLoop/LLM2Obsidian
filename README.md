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
- `UI_ADMIN_TOKEN=change-this-token`
- `LLM_PROVIDER=deepseek`
- `EMBEDDINGS_PROVIDER=deterministic`
- `OBSIDIAN_MODE=auto`

Mode notes:
- `OBSIDIAN_MODE=filesystem` reads and writes directly under `VAULT_ROOT`.
- `OBSIDIAN_MODE=rest` writes to the vault currently opened by Obsidian Local REST API.
- `OBSIDIAN_MODE=auto` prefers REST and falls back to filesystem.
- `OBSIDIAN_VERIFY_SSL` now defaults to `true`; only disable it for local self-signed Obsidian setups.
- `LLM_PROVIDER=ollama` enables a local Ollama chat model.
- `EMBEDDINGS_PROVIDER=ollama` enables Ollama embeddings while preserving deterministic fallback in tests.

3. Seed the demo vault if you want local sample data.

```bash
python scripts/seed_demo_data.py
```

4. Start the API.

```bash
uvicorn obsidian_agent.app:create_app --factory --reload
```

Or on Windows, start the local dashboard with one script:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start_dashboard.ps1
```

Then open `http://127.0.0.1:8000/`.
The UI page is public, but all `/ui/api/*` actions require the `X-Admin-Token` header. The dashboard stores that token in browser local storage after you enter it once.

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
- `POST /smart/error-capture`
- `POST /smart/node-pack`
- `POST /smart/teach`
- `GET /smart/related-nodes`

## Delivery Notes

- Vault writes go through `ObsidianService` only.
- `DRY_RUN=true` returns action previews for write paths instead of mutating the vault.
- Prompt assets live under `src/obsidian_agent/prompts/` and are tracked by `manifest.json`.
- The built-in control panel is served from `/` and `/ui`.
- The control panel can edit `.env`, reload runtime settings, seed demo data, reindex, capture text, run smart C-error capture, preview node packs, build teaching packs, search notes, inspect review items, and run maintenance jobs.
- `/capture/url` blocks loopback and private-network targets to reduce SSRF risk.

See [docs/operations.md](/W:/codex/codex/docs/operations.md), [docs/api.md](/W:/codex/codex/docs/api.md), and [docs/prompts.md](/W:/codex/codex/docs/prompts.md) for details.
