# GitHub Actions vs systemd

Для этого проекта GitHub Actions не запускает Telegram-бота 24/7.

Правильная схема:

```text
systemd на VPS — держит бота запущенным постоянно
GitHub Actions — только обновляет код на VPS после push
```

Папка бота на нашем VPS:

```text
/home/tsoillc/claude-telegram-vps-bot
```

Пользователь VPS:

```text
tsoillc
```

Команды ручного обновления на VPS:

```bash
cd /home/tsoillc/claude-telegram-vps-bot
git pull --ff-only
./scripts/install.sh
sudo systemctl restart claude-telegram-bot
sudo systemctl status claude-telegram-bot --no-pager
```

Для GitHub Actions в Secrets:

```text
VPS_HOST = IP сервера
VPS_USER = tsoillc
VPS_SSH_KEY = приватный SSH-ключ
BOT_DIR = /home/tsoillc/claude-telegram-vps-bot
```
