# Claude Telegram VPS Bot — Ubuntu 24.04 / Timeweb / user `tsoillc`

Это закрытый Telegram-бот для тебя и небольшой команды. Он живёт на VPS, запускает Claude Code внутри выбранной папки проекта и возвращает ответ в Telegram.

Текущая сборка уже адаптирована под вашу фактическую схему:

```text
Пользователь VPS: tsoillc
Домашняя папка: /home/tsoillc
Папка бота: /home/tsoillc/claude-telegram-vps-bot
Папки проектов: /home/tsoillc/projects/...
Claude Code установлен через npm: /home/tsoillc/.npm-global/bin/claude
```

## Как это работает

```text
Telegram
↓
закрытый бот
↓
VPS Ubuntu 24.04
↓
Claude Code
↓
выбранная папка проекта
```

Команды в Telegram:

```text
/start — инструкция
/id — узнать Telegram ID
/projects — список проектов
/use rubrik — выбрать проект
/where — показать активный проект
/ask текст — спросить без изменения файлов
/plan текст — получить план
/code текст — разрешить Claude менять файлы
```

## 1. Проверяем текущую папку и Claude Code

В терминале Ubuntu:

```bash
cd ~
pwd
whoami
which claude
claude auth status --text
```

Ожидаемо:

```text
/home/tsoillc
tsoillc
/home/tsoillc/.npm-global/bin/claude
```

Если `claude auth status --text` показывает, что логин есть, идём дальше.

## 2. Создаём папки проектов

```bash
cd ~
mkdir -p projects/rubrik projects/avia-bot projects/chelsea
ls projects
```

Должно быть:

```text
avia-bot  chelsea  rubrik
```

## 3. Проверяем доверие Claude к конкретной папке проекта

Не запускаем Claude из `/home/tsoillc`, потому что это слишком широкая папка.

Делаем так:

```bash
cd ~/projects/rubrik
claude
```

Если Claude спросит, доверяешь ли папке, тут можно выбрать:

```text
1. Yes, I trust this folder
```

Потом выйди из Claude:

```text
/exit
```

или `Ctrl + C`.

## 4. Как загрузить этот репозиторий на VPS

### Вариант А — через GitHub repo

```bash
cd ~
git clone GITHUB_REPO_URL claude-telegram-vps-bot
cd ~/claude-telegram-vps-bot
```

`GITHUB_REPO_URL` замени на ссылку своего репозитория.

### Вариант Б — через архив

Если скачала zip на VPS в папку Downloads:

```bash
cd ~/Downloads
unzip claude-telegram-vps-bot.zip -d ~
cd ~/claude-telegram-vps-bot
```

Проверь:

```bash
pwd
ls
```

Ожидаемо:

```text
/home/tsoillc/claude-telegram-vps-bot
bot.py  scripts  systemd  requirements.txt  .env.example  users.example.json  projects.example.json
```

## 5. Устанавливаем зависимости бота

```bash
cd ~/claude-telegram-vps-bot
chmod +x scripts/install.sh scripts/run_once.sh scripts/check.sh scripts/update.sh
./scripts/install.sh
```

Скрипт создаст:

```text
venv/
.env
users.json
projects.json
logs/
```

## 6. Настраиваем `.env`

Открыть файл:

```bash
nano .env
```

Заполнить:

```env
BOT_TOKEN=PASTE_TELEGRAM_BOT_TOKEN_HERE
ADMIN_IDS=PASTE_YOUR_TELEGRAM_ID_HERE
MAX_PROMPT_CHARS=6000
CLAUDE_TIMEOUT_SECONDS=900
CLAUDE_MAX_TURNS_ASK=6
CLAUDE_MAX_TURNS_CODE=10
CLAUDE_BINARY=/home/tsoillc/.npm-global/bin/claude
CLAUDE_EFFORT=
```

`BOT_TOKEN` берём у Telegram-бота `@BotFather`.

`ADMIN_IDS` — твой Telegram ID. Его можно узнать через `@userinfobot` или потом через команду `/id` у бота.

Сохранить в nano:

```text
Ctrl + O
Enter
Ctrl + X
```

## 7. Настраиваем `users.json`

```bash
nano users.json
```

Минимально для тебя одной:

```json
{
  "111111111": {
    "name": "You",
    "role": "admin",
    "projects": ["*"],
    "can_edit": true
  }
}
```

`111111111` замени на свой Telegram ID.

Для команды:

```json
{
  "111111111": {
    "name": "You",
    "role": "admin",
    "projects": ["*"],
    "can_edit": true
  },
  "222222222": {
    "name": "Partner",
    "role": "team",
    "projects": ["rubrik", "avia-bot"],
    "can_edit": true
  },
  "333333333": {
    "name": "Viewer",
    "role": "viewer",
    "projects": ["rubrik"],
    "can_edit": false
  }
}
```

## 8. Настраиваем `projects.json`

```bash
nano projects.json
```

Должно быть так:

```json
{
  "rubrik": {
    "title": "RUBRIK",
    "path": "/home/tsoillc/projects/rubrik"
  },
  "avia-bot": {
    "title": "Avia Bot",
    "path": "/home/tsoillc/projects/avia-bot"
  },
  "chelsea": {
    "title": "Chelsea Brand",
    "path": "/home/tsoillc/projects/chelsea"
  }
}
```

## 9. Кладём инструкции Claude в проекты

```bash
cd ~/claude-telegram-vps-bot
cp project_templates/CLAUDE.md ~/projects/rubrik/CLAUDE.md
cp project_templates/CLAUDE.md ~/projects/avia-bot/CLAUDE.md
cp project_templates/CLAUDE.md ~/projects/chelsea/CLAUDE.md

mkdir -p ~/projects/rubrik/.claude ~/projects/avia-bot/.claude ~/projects/chelsea/.claude
cp project_templates/.claude/settings.json ~/projects/rubrik/.claude/settings.json
cp project_templates/.claude/settings.json ~/projects/avia-bot/.claude/settings.json
cp project_templates/.claude/settings.json ~/projects/chelsea/.claude/settings.json
```

## 10. Тестируем бота вручную

```bash
cd ~/claude-telegram-vps-bot
./scripts/run_once.sh
```

В Telegram напиши своему боту:

```text
/start
/projects
/use rubrik
/ask Что ты видишь в проекте?
```

Остановить ручной запуск:

```text
Ctrl + C
```

## 11. Запускаем бота постоянно через systemd

Скопировать сервис:

```bash
sudo cp ~/claude-telegram-vps-bot/systemd/claude-telegram-bot.service /etc/systemd/system/claude-telegram-bot.service
sudo systemctl daemon-reload
sudo systemctl enable claude-telegram-bot
sudo systemctl start claude-telegram-bot
sudo systemctl status claude-telegram-bot
```

Логи:

```bash
journalctl -u claude-telegram-bot -f
```

Если меняешь `.env`, `users.json` или `projects.json`, перезапуск:

```bash
sudo systemctl restart claude-telegram-bot
```

## 12. GitHub Actions, если хочешь обновлять код через push

Бот всё равно живёт на VPS через systemd. GitHub Actions нужен только для обновления кода:

```text
push в GitHub
↓
GitHub Actions подключается к VPS
↓
git pull
↓
перезапуск systemd-сервиса
```

В GitHub Secrets добавь:

```text
VPS_HOST = IP сервера
VPS_USER = tsoillc
VPS_SSH_KEY = приватный SSH-ключ для входа на VPS
BOT_DIR = /home/tsoillc/claude-telegram-vps-bot
```

Для перезапуска сервиса из Actions пользователю `tsoillc` нужно разрешить только одну sudo-команду.

Открыть sudoers:

```bash
sudo visudo -f /etc/sudoers.d/tsoillc-systemctl
```

Вставить:

```sudoers
tsoillc ALL=(root) NOPASSWD: /usr/bin/systemctl restart claude-telegram-bot, /usr/bin/systemctl status claude-telegram-bot
```

Сохранить. Проверить:

```bash
sudo systemctl status claude-telegram-bot --no-pager
```

## 13. Что не пушить в GitHub

Эти файлы должны оставаться только на VPS:

```text
.env
users.json
projects.json
state.json
venv/
logs/
```

Они уже добавлены в `.gitignore`.

## Быстрая проверка

```bash
cd ~/claude-telegram-vps-bot
./scripts/check.sh
```

Если бот не отвечает:

```bash
journalctl -u claude-telegram-bot -f
```

Если Claude не найден:

```bash
which claude
nano .env
```

В `.env` должно быть:

```env
CLAUDE_BINARY=/home/tsoillc/.npm-global/bin/claude
```
