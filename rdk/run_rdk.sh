#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ -f config.env ]]; then
  set -a
  # Only use a self-created trusted config.env file; never source downloads.
  source ./config.env
  set +a
fi
exec "${LABOS_PYTHON:-.venv/bin/python}" -m labos.server
