#!/usr/bin/env bash
. .venv/Scripts/activate
uvicorn obsidian_agent.app:create_app --factory --reload
