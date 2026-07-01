#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

git pull --ff-only || true
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart claude-telegram-bot
sudo systemctl status claude-telegram-bot --no-pager
