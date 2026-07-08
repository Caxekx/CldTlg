#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "==> Создаю Python venv"
python3 -m venv venv

# shellcheck disable=SC1091
source venv/bin/activate

echo "==> Ставлю зависимости"
pip install --upgrade pip
pip install -r requirements.txt

echo "==> Создаю рабочие конфиги, если их ещё нет"
if [ ! -f .env ]; then
  cp .env.example .env
  echo "Создан .env — заполни BOT_TOKEN, ADMIN_IDS, CLAUDE_BINARY при необходимости"
fi

if [ ! -f users.json ]; then
  cp users.example.json users.json
  echo "Создан users.json — вставь реальные Telegram ID"
fi

if [ ! -f projects.json ]; then
  cp projects.example.json projects.json
  echo "Создан projects.json — проверь пути проектов"
fi

mkdir -p logs
mkdir -p /home/tsoillc/projects/rubrik /home/tsoillc/projects/avia-bot /home/tsoillc/projects/chelsea 2>/dev/null || true

echo "==> Готово"
echo "Дальше: nano .env, nano users.json, nano projects.json, потом: ./scripts/run_once.sh"
