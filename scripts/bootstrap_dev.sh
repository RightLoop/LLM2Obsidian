#!/usr/bin/env bash
python -m venv .venv
. .venv/Scripts/activate
pip install -e .[dev]
