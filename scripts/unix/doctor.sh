#!/usr/bin/env bash
cd "$(dirname "$0")/../.." || exit 1
source .venv/bin/activate 2>/dev/null
python3 -m src.cli doctor "$@"
