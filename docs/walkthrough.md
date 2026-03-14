# Local Walkthrough

This walkthrough exercises the project against a local Obsidian setup or the demo vault.

## 1. Prepare Environment

```bash
copy .env.example .env
python scripts/seed_demo_data.py
```

Set at least:
- `UI_ADMIN_TOKEN=change-this-token`
- `LLM_PROVIDER=deepseek`
- `DEEPSEEK_API_KEY=...`
- `OBSIDIAN_MODE=auto`
- `OBSIDIAN_API_URL=...`
- `OBSIDIAN_API_KEY=...`
- `VAULT_ROOT=...`

Optional local-model settings:
- `LLM_PROVIDER=ollama`
- `EMBEDDINGS_PROVIDER=ollama`
- `OLLAMA_BASE_URL=http://127.0.0.1:11434`

## 2. Start the API

```bash
uvicorn obsidian_agent.app:create_app --factory --reload
```

Or on Windows:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start_dashboard.ps1
```

Then open `http://127.0.0.1:8000/` to use the built-in control panel.
Enter `UI_ADMIN_TOKEN` in the page once so the dashboard can call `/ui/api/*`.

## 3. Build Local Indexes

```bash
curl -X POST http://127.0.0.1:8000/maintenance/reindex
```

## 4. Capture a Note

```bash
curl -X POST http://127.0.0.1:8000/capture/text ^
  -H "Content-Type: application/json" ^
  -d "{\"title\":\"C Pointer Ownership\",\"text\":\"Pointer ownership in C should be explicit and documented.\"}"
```

## 5. Run Smart C Error Capture

```bash
curl -X POST http://127.0.0.1:8000/smart/error-capture ^
  -H "Content-Type: application/json" ^
  -d "{\"title\":\"sizeof vs strlen\",\"prompt\":\"I treated sizeof(arr) as the string length.\",\"code\":\"char arr[] = \\\"abc\\\"; printf(\\\"%zu\\\", sizeof(arr));\",\"user_analysis\":\"I assumed sizeof returns visible characters.\",\"language\":\"c\"}"
```

This creates an Error Node note under the configured smart error folder and records a local `knowledge_nodes` / `error_occurrences` entry.
The same call now also creates or reuses supporting Concept and Pitfall nodes under the smart nodes folder.

To preview mined relations around that node:

```bash
curl -X POST http://127.0.0.1:8000/smart/node-pack ^
  -H "Content-Type: application/json" ^
  -d "{\"node_key\":\"error/sizeof-vs-strlen\",\"top_k\":5}"
```

To generate a teaching-oriented explanation from that relation pack:

```bash
curl -X POST http://127.0.0.1:8000/smart/teach ^
  -H "Content-Type: application/json" ^
  -d "{\"node_key\":\"error/sizeof-vs-strlen\",\"top_k\":5}"
```

To inspect nearby smart nodes without generating a teaching pack:

```bash
curl "http://127.0.0.1:8000/smart/related-nodes?node_key=error/sizeof-vs-strlen&top_k=5"
```

To rebuild relations and create a review artifact instead of mutating the note directly:

```bash
curl -X POST http://127.0.0.1:8000/smart/relink ^
  -H "Content-Type: application/json" ^
  -d "{\"node_key\":\"error/sizeof-vs-strlen\",\"top_k\":5,\"create_review\":true,\"dry_run\":false}"
```

## 6. Generate and Apply a Review

1. Call `POST /review/generate` with the new Inbox note path.
2. Call `POST /review/{id}/approve`.
3. Call `POST /review/{id}/apply`.

## 7. Run Maintenance

- `GET /maintenance/duplicates`
- `GET /maintenance/orphans`
- `GET /maintenance/metadata-issues`
- `POST /maintenance/weekly-digest`

## 8. Safe Trial Mode

Set `DRY_RUN=true` before starting the API if you want previews without modifying the vault.
