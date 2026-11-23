#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
if [[ ! -f config.env ]]; then cp config.env.example config.env; fi
mkdir -p data
printf '\n完成。运行: bash run_rdk.sh\n'
