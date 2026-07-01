# GitHub Actions или systemd?

## Коротко

- **systemd** — запускает Telegram-бота постоянно на VPS.
- **GitHub Actions** — обновляет код на VPS после push в GitHub.

Не стоит запускать Telegram-бота прямо в GitHub Actions: workflow не предназначен для вечного процесса 24/7.

## Рекомендуемая схема

```text
GitHub repo
↓ push
GitHub Actions
↓ ssh на VPS
cd /home/claudebot/claude-telegram-vps-bot
↓
git pull
↓
systemctl restart claude-telegram-bot
```

## Когда хватит ручного обновления

Если бот для тебя и 1–2 человек, можно вообще не делать GitHub Actions. Достаточно:

```bash
ssh root@SERVER_IP
su - claudebot
cd /home/claudebot/claude-telegram-vps-bot
git pull
./scripts/install.sh
exit
systemctl restart claude-telegram-bot
```
