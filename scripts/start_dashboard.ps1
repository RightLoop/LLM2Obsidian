$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not (Test-Path ".venv")) {
  python -m venv .venv
}

& .\.venv\Scripts\python.exe -m pip install -e .[dev]
& .\.venv\Scripts\python.exe -m uvicorn obsidian_agent.app:create_app --factory --reload
