#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

echo "==> Python"
python3 --version

echo "==> Файлы"
[ -f .env ] && echo ".env ok" || echo ".env missing"
[ -f users.json ] && echo "users.json ok" || echo "users.json missing"
[ -f projects.json ] && echo "projects.json ok" || echo "projects.json missing"

echo "==> Claude"
if command -v claude >/dev/null 2>&1; then
  which claude
  claude --version || true
  claude auth status --text || true
else
  echo "claude не найден в PATH"
fi

echo "==> systemd"
systemctl status claude-telegram-bot --no-pager || true
