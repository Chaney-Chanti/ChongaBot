#!/usr/bin/env bash
# Update the server to the latest code and restart. Run as the app user:
#   sudo -iu chonga ~/ChongaBot/deploy/deploy.sh
# Database migrations run automatically when the bot starts.
set -euo pipefail
cd "$(dirname "$0")/.."

git pull --ff-only
~/.local/bin/uv sync --frozen --no-dev
sudo systemctl restart chongabot
sleep 3
sudo systemctl status chongabot --no-pager | head -n 5
