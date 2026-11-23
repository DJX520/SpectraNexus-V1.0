#!/usr/bin/env bash
# Install user-level systemd service for the extracted directory; no root modifications.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$(pwd)"
mkdir -p "$HOME/.config/systemd/user"
cat > "$HOME/.config/systemd/user/labos5.service" <<UNIT
[Unit]
Description=LabOS V5 RDK X5 local experiment server
After=network.target
[Service]
Type=simple
WorkingDirectory=$ROOT
ExecStart=/bin/bash $ROOT/run_rdk.sh
Restart=on-failure
RestartSec=5
[Install]
WantedBy=default.target
UNIT
systemctl --user daemon-reload
systemctl --user enable --now labos5.service
systemctl --user status labos5.service --no-pager
printf '\n请用 journalctl --user -u labos5.service -f 查看日志。\n'
