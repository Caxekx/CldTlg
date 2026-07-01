# Claude Code Telegram Bot на VPS

Закрытый Telegram-бот для внутренней команды: Telegram → VPS → Claude Code → папка конкретного проекта → ответ обратно в Telegram.

Подходит для сценария: ты + 1–2 человека из команды. Не рассчитано на публичных подписчиков и SaaS.

---

## 0. Что внутри архива

```text
claude-telegram-vps-bot/
├── bot.py                         # основной бот
├── requirements.txt               # Python-зависимости
├── .env.example                   # шаблон секретов
├── users.example.json             # шаблон пользователей
├── projects.example.json          # шаблон проектов
├── project_templates/
│   ├── CLAUDE.md                  # правила для каждого проекта
│   └── .claude/settings.json      # доп. ограничения Claude Code
├── scripts/
│   ├── install.sh                 # установка зависимостей
│   ├── run_once.sh                # ручной запуск для теста
│   ├── check.sh                   # диагностика
│   └── update.sh                  # обновление с GitHub на VPS
├── systemd/
│   └── claude-telegram-bot.service
└── .github/workflows/deploy.yml   # пример деплоя через GitHub Actions
```

---

## 1. Логика работы

```text
Telegram ID пользователя
↓
users.json: можно ли ему пользоваться ботом?
↓
projects.json: какие проекты ему доступны?
↓
/use rubrik выбирает папку /home/claudebot/projects/rubrik
↓
/ask, /plan или /code запускает claude -p внутри этой папки
```

Команды в Telegram:

```text
/start      — инструкция
/id         — узнать Telegram ID
/projects   — список доступных проектов
/use rubrik — выбрать проект
/where      — текущий проект
/ask текст  — спросить без изменения файлов
/plan текст — получить план без изменения файлов
/code текст — разрешить менять файлы, только если can_edit=true
/health     — диагностика Claude Code
```

---

## 2. Что выбрать: systemd, GitHub Actions, Docker, tmux?

### Лучший вариант для тебя: systemd на VPS

Бот живёт на VPS постоянно. Если VPS перезагрузится, systemd сам поднимет бота.

```text
Подходит: да
Сложность: средняя
Надёжность: высокая
```

### GitHub Actions

GitHub Actions не должен постоянно держать Telegram-бота. Используй его только для обновления кода на VPS после push в GitHub.

```text
Подходит для деплоя: да
Подходит для постоянного запуска бота: нет
```

### Docker

Хороший вариант позже, но для первого запуска не нужен. Сначала проще systemd.

### tmux

Можно использовать для теста, но не как финальный запуск. После перезагрузки или падения процесса бот остановится.

---

## 3. Подготовка VPS

Подключись к серверу:

```bash
ssh root@SERVER_IP
```

Обнови сервер:

```bash
apt update && apt upgrade -y
```

Поставь базовые пакеты:

```bash
apt install -y python3 python3-venv python3-pip git curl nano
```

Создай отдельного пользователя под бота:

```bash
adduser claudebot
```

Переключись в него:

```bash
su - claudebot
```

---

## 4. Установка Claude Code на VPS

Внутри пользователя `claudebot`:

```bash
curl -fsSL https://claude.ai/install.sh | bash
```

Перезапусти shell:

```bash
exit
su - claudebot
```

Проверь:

```bash
claude --version
```

Запусти первый логин:

```bash
claude
```

Claude Code покажет ссылку. Открой её у себя в браузере, войди в Claude с Max/Pro-подпиской и вставь код обратно в терминал VPS.

Проверка авторизации:

```bash
claude auth status --text
```

Если команда `claude` не находится, попробуй:

```bash
which claude
```

И потом укажи этот путь в `.env` в переменной:

```env
CLAUDE_BINARY=/home/claudebot/.local/bin/claude
```

---

## 5. Создай Telegram-бота

В Telegram открой `@BotFather`.

Напиши:

```text
/newbot
```

Дальше:

```text
Name: Claude VPS Bot
Username: your_claude_vps_bot
```

BotFather даст токен вида:

```text
1234567890:AAHxxxxxxxxxxxxxxxxxxxxxxxx
```

Это вставишь в `.env`.

---

## 6. Загрузка проекта бота на VPS

### Вариант А. Без GitHub, просто архивом

На своём компьютере распакуй архив и залей папку на VPS, например через SFTP/Transmit/Cyberduck.

Итоговый путь должен быть:

```text
/home/claudebot/claude-telegram-vps-bot
```

### Вариант Б. Через GitHub

1. Создай приватный репозиторий на GitHub.
2. Загрузи туда содержимое архива.
3. На VPS под пользователем `claudebot` сделай:

```bash
cd /home/claudebot
git clone GITHUB_REPO_SSH_OR_HTTPS_URL claude-telegram-vps-bot
cd claude-telegram-vps-bot
```

Пример placeholder:

```bash
git clone git@github.com:YOUR_USERNAME/claude-telegram-vps-bot.git claude-telegram-vps-bot
```

---

## 7. Установка бота

Под пользователем `claudebot`:

```bash
cd /home/claudebot/claude-telegram-vps-bot
./scripts/install.sh
```

Скрипт создаст:

```text
.env
users.json
projects.json
venv/
logs/
```

---

## 8. Настрой `.env`

Открой:

```bash
nano .env
```

Заполни:

```env
BOT_TOKEN=PASTE_TELEGRAM_BOT_TOKEN_HERE
ADMIN_IDS=PASTE_YOUR_TELEGRAM_ID_HERE
MAX_PROMPT_CHARS=6000
CLAUDE_TIMEOUT_SECONDS=900
CLAUDE_MAX_TURNS_ASK=6
CLAUDE_MAX_TURNS_CODE=10
CLAUDE_BINARY=claude
CLAUDE_EFFORT=
```

Если systemd потом не увидит `claude`, замени:

```env
CLAUDE_BINARY=/home/claudebot/.local/bin/claude
```

Сохрани nano:

```text
Ctrl + O
Enter
Ctrl + X
```

---

## 9. Узнай свой Telegram ID

Пока можно временно запустить бота и написать `/id`.

```bash
./scripts/run_once.sh
```

В Telegram напиши своему боту:

```text
/id
```

Он должен вернуть число, например:

```text
123456789
```

Останови ручной запуск:

```text
Ctrl + C
```

---

## 10. Настрой пользователей

Открой:

```bash
nano users.json
```

Пример:

```json
{
  "123456789": {
    "name": "Katerina",
    "role": "admin",
    "projects": ["*"],
    "can_edit": true
  },
  "987654321": {
    "name": "Partner",
    "role": "team",
    "projects": ["rubrik", "avia-bot"],
    "can_edit": true
  },
  "555555555": {
    "name": "Designer",
    "role": "viewer",
    "projects": ["rubrik"],
    "can_edit": false
  }
}
```

Пояснение:

```text
projects: ["*"]       — доступны все проекты
projects: ["rubrik"]  — доступен только rubrik
can_edit: true         — можно /code
can_edit: false        — только /ask и /plan
```

---

## 11. Настрой проекты

Открой:

```bash
nano projects.json
```

Пример:

```json
{
  "rubrik": {
    "title": "RUBRIK",
    "path": "/home/claudebot/projects/rubrik"
  },
  "avia-bot": {
    "title": "Avia Bot",
    "path": "/home/claudebot/projects/avia-bot"
  },
  "chelsea": {
    "title": "Chelsea Brand",
    "path": "/home/claudebot/projects/chelsea"
  }
}
```

Создай папки:

```bash
mkdir -p /home/claudebot/projects/rubrik
mkdir -p /home/claudebot/projects/avia-bot
mkdir -p /home/claudebot/projects/chelsea
```

Если проект лежит в GitHub:

```bash
cd /home/claudebot/projects/rubrik
git clone GITHUB_PROJECT_URL .
```

Если проекта пока нет, просто положи туда файлы вручную.

---

## 12. Добавь правила Claude в каждый проект

Для каждого проекта положи `CLAUDE.md`:

```bash
cp /home/claudebot/claude-telegram-vps-bot/project_templates/CLAUDE.md /home/claudebot/projects/rubrik/CLAUDE.md
```

И опционально настройки ограничений:

```bash
mkdir -p /home/claudebot/projects/rubrik/.claude
cp /home/claudebot/claude-telegram-vps-bot/project_templates/.claude/settings.json /home/claudebot/projects/rubrik/.claude/settings.json
```

Повтори для других проектов:

```bash
cp /home/claudebot/claude-telegram-vps-bot/project_templates/CLAUDE.md /home/claudebot/projects/avia-bot/CLAUDE.md
mkdir -p /home/claudebot/projects/avia-bot/.claude
cp /home/claudebot/claude-telegram-vps-bot/project_templates/.claude/settings.json /home/claudebot/projects/avia-bot/.claude/settings.json
```

---

## 13. Первый тест вручную

```bash
cd /home/claudebot/claude-telegram-vps-bot
./scripts/run_once.sh
```

В Telegram:

```text
/start
/projects
/use rubrik
/health
/ask Объясни, что лежит в этом проекте
```

Если работает — останови:

```text
Ctrl + C
```

---

## 14. Запуск через systemd

Выйди в root:

```bash
exit
```

Скопируй service:

```bash
cp /home/claudebot/claude-telegram-vps-bot/systemd/claude-telegram-bot.service /etc/systemd/system/claude-telegram-bot.service
```

Включи автозапуск:

```bash
systemctl daemon-reload
systemctl enable claude-telegram-bot
systemctl start claude-telegram-bot
```

Проверка:

```bash
systemctl status claude-telegram-bot
```

Логи:

```bash
journalctl -u claude-telegram-bot -f
```

Перезапуск:

```bash
systemctl restart claude-telegram-bot
```

---

## 15. Обновление руками без GitHub Actions

Под root или через sudo:

```bash
su - claudebot
cd /home/claudebot/claude-telegram-vps-bot
git pull
./scripts/install.sh
exit
systemctl restart claude-telegram-bot
```

Это самый простой и понятный вариант.

---

## 16. Обновление через GitHub Actions

GitHub Actions здесь нужен не для запуска бота, а для команды:

```text
push в GitHub → GitHub подключается к VPS → git pull → restart systemd
```

### 16.1. Сгенерируй SSH-ключ для GitHub Actions на своём компьютере или VPS

```bash
ssh-keygen -t ed25519 -C "github-actions-claude-bot" -f github_actions_claude_bot
```

Появятся два файла:

```text
github_actions_claude_bot      — приватный ключ
github_actions_claude_bot.pub  — публичный ключ
```

### 16.2. Добавь публичный ключ на VPS

На VPS под пользователем `claudebot`:

```bash
mkdir -p ~/.ssh
nano ~/.ssh/authorized_keys
```

Вставь содержимое файла:

```text
github_actions_claude_bot.pub
```

Права:

```bash
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
```

### 16.3. Разреши claudebot перезапускать только этот сервис

Под root:

```bash
visudo -f /etc/sudoers.d/claudebot-systemctl
```

Вставь:

```text
claudebot ALL=NOPASSWD: /bin/systemctl restart claude-telegram-bot, /bin/systemctl status claude-telegram-bot
```

### 16.4. Добавь Secrets в GitHub

В репозитории GitHub:

```text
Settings → Secrets and variables → Actions → New repository secret
```

Создай:

```text
VPS_HOST = SERVER_IP
VPS_USER = claudebot
VPS_SSH_KEY = содержимое приватного ключа github_actions_claude_bot
BOT_DIR = /home/claudebot/claude-telegram-vps-bot
```

### 16.5. Проверь workflow

Файл уже лежит тут:

```text
.github/workflows/deploy.yml
```

После push в `main` GitHub должен зайти на VPS и выполнить:

```bash
cd /home/claudebot/claude-telegram-vps-bot
git pull --ff-only
./scripts/install.sh
sudo systemctl restart claude-telegram-bot
```

---

## 17. Как добавить нового человека из команды

1. Он пишет боту:

```text
/id
```

2. Присылает тебе число.

3. Ты добавляешь его в `users.json`:

```json
"222222222": {
  "name": "Partner",
  "role": "team",
  "projects": ["rubrik", "avia-bot"],
  "can_edit": true
}
```

4. Перезапуск не обязателен: бот читает `users.json` на каждый запрос. Но для спокойствия можно:

```bash
systemctl restart claude-telegram-bot
```

---

## 18. Как добавить новый проект

1. Создай папку:

```bash
mkdir -p /home/claudebot/projects/new-project
```

2. Положи туда файлы или склонируй GitHub:

```bash
cd /home/claudebot/projects/new-project
git clone GITHUB_PROJECT_URL .
```

3. Добавь в `projects.json`:

```json
"new-project": {
  "title": "New Project",
  "path": "/home/claudebot/projects/new-project"
}
```

4. Добавь доступ пользователю в `users.json`:

```json
"projects": ["rubrik", "new-project"]
```

5. Скопируй правила Claude:

```bash
cp /home/claudebot/claude-telegram-vps-bot/project_templates/CLAUDE.md /home/claudebot/projects/new-project/CLAUDE.md
mkdir -p /home/claudebot/projects/new-project/.claude
cp /home/claudebot/claude-telegram-vps-bot/project_templates/.claude/settings.json /home/claudebot/projects/new-project/.claude/settings.json
```

---

## 19. Что делать, если не работает

### Бот не отвечает

```bash
systemctl status claude-telegram-bot
journalctl -u claude-telegram-bot -f
```

### Claude не авторизован

```bash
su - claudebot
claude auth status --text
claude
```

### systemd не видит claude

```bash
su - claudebot
which claude
```

Скопируй путь в `.env`:

```env
CLAUDE_BINARY=/home/claudebot/.local/bin/claude
```

Потом:

```bash
systemctl restart claude-telegram-bot
```

### Ошибка в JSON

Проверь, что в `users.json` и `projects.json` нет лишней запятой в конце.

Плохой пример:

```json
{
  "rubrik": {
    "title": "RUBRIK"
  },
}
```

Хороший пример:

```json
{
  "rubrik": {
    "title": "RUBRIK"
  }
}
```

---

## 20. Минимальный чеклист запуска

```text
[ ] VPS обновлён
[ ] создан пользователь claudebot
[ ] Claude Code установлен под claudebot
[ ] claude auth status --text показывает авторизацию
[ ] создан Telegram-бот через BotFather
[ ] .env заполнен
[ ] users.json заполнен реальными Telegram ID
[ ] projects.json указывает на реальные папки
[ ] в проекте есть CLAUDE.md
[ ] ./scripts/run_once.sh работает
[ ] systemd service запущен
[ ] /health в Telegram проходит
```
