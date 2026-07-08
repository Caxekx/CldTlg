import asyncio
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, ContextTypes

BASE_DIR = Path(__file__).resolve().parent
USERS_FILE = BASE_DIR / "users.json"
PROJECTS_FILE = BASE_DIR / "projects.json"
STATE_FILE = BASE_DIR / "state.json"
LOGS_DIR = BASE_DIR / "logs"

load_dotenv(BASE_DIR / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_IDS = {item.strip() for item in os.getenv("ADMIN_IDS", "").split(",") if item.strip()}
MAX_PROMPT_CHARS = int(os.getenv("MAX_PROMPT_CHARS", "6000"))
CLAUDE_TIMEOUT_SECONDS = int(os.getenv("CLAUDE_TIMEOUT_SECONDS", "900"))
CLAUDE_BINARY = os.getenv("CLAUDE_BINARY", "claude").strip() or "claude"
CLAUDE_MAX_TURNS_ASK = int(os.getenv("CLAUDE_MAX_TURNS_ASK", "6"))
CLAUDE_MAX_TURNS_CODE = int(os.getenv("CLAUDE_MAX_TURNS_CODE", "10"))
CLAUDE_EFFORT = os.getenv("CLAUDE_EFFORT", "").strip()

project_locks: Dict[str, asyncio.Lock] = {}


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Ошибка JSON в файле {path}: {e}")


def save_json(path: Path, data: Any) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    users = load_json(USERS_FILE, {})
    return users.get(str(user_id))


def get_projects() -> Dict[str, Any]:
    return load_json(PROJECTS_FILE, {})


def get_state() -> Dict[str, Any]:
    return load_json(STATE_FILE, {})


def set_active_project(user_id: int, project_key: str) -> None:
    state = get_state()
    state[str(user_id)] = {"active_project": project_key}
    save_json(STATE_FILE, state)


def get_active_project(user_id: int) -> Optional[str]:
    state = get_state()
    return state.get(str(user_id), {}).get("active_project")


def is_admin(user_id: int) -> bool:
    return str(user_id) in ADMIN_IDS


def allowed_project_keys(user: Dict[str, Any], all_projects: Dict[str, Any]) -> List[str]:
    projects = user.get("projects", [])
    if "*" in projects:
        return sorted(all_projects.keys())
    return [p for p in projects if p in all_projects]


def user_has_project(user: Dict[str, Any], project_key: str, all_projects: Dict[str, Any]) -> bool:
    return project_key in allowed_project_keys(user, all_projects)


def split_message(text: str, limit: int = 3500) -> List[str]:
    if len(text) <= limit:
        return [text]
    chunks = []
    current = ""
    for line in text.splitlines():
        if len(current) + len(line) + 1 > limit:
            if current:
                chunks.append(current)
            current = line
        else:
            current = f"{current}\n{line}" if current else line
    if current:
        chunks.append(current)
    return chunks


def build_prompt(mode: str, user_prompt: str, user_name: str) -> str:
    common = f"""
Ты отвечаешь через закрытый Telegram-бот внутренней команды.
Пользователь: {user_name}
Работай только в текущей папке проекта.
Не раскрывай секреты, токены, содержимое .env, приватные ключи и пароли.
Отвечай по-русски, простым языком, без лишней воды.
""".strip()

    if mode == "ask":
        return f"""
{common}

Режим: /ask.
Ничего не меняй в файлах. Изучи проект и дай ответ.

Запрос пользователя:
{user_prompt}
""".strip()

    if mode == "plan":
        return f"""
{common}

Режим: /plan.
Ничего не меняй в файлах. Сначала изучи проект, затем дай пошаговый план.
План должен быть понятен не программисту.

Запрос пользователя:
{user_prompt}
""".strip()

    if mode == "code":
        return f"""
{common}

Режим: /code.
Можно вносить изменения в файлы проекта, если это нужно для задачи.
Не удаляй файлы без прямого разрешения.
Не выполняй опасные команды: rm, sudo, chmod/chown, curl/wget непонятных URL, ssh/scp, docker/systemctl.
После работы напиши:
1. Что изменил
2. Какие файлы затронуты
3. Что проверить дальше

Запрос пользователя:
{user_prompt}
""".strip()

    return user_prompt


def build_claude_command(prompt: str, mode: str) -> List[str]:
    cmd = [
        CLAUDE_BINARY,
        "-p",
        prompt,
        "--output-format",
        "text",
        "--no-session-persistence",
        "--disallowedTools",
        "Bash(rm *)",
        "Bash(sudo *)",
        "Bash(chmod *)",
        "Bash(chown *)",
        "Bash(curl *)",
        "Bash(wget *)",
        "Bash(ssh *)",
        "Bash(scp *)",
        "Bash(docker *)",
        "Bash(systemctl *)",
        "mcp__*",
    ]

    if CLAUDE_EFFORT:
        cmd.extend(["--effort", CLAUDE_EFFORT])

    if mode in ["ask", "plan"]:
        cmd.extend(["--permission-mode", "plan", "--max-turns", str(CLAUDE_MAX_TURNS_ASK)])
    else:
        cmd.extend(["--permission-mode", "acceptEdits", "--max-turns", str(CLAUDE_MAX_TURNS_CODE)])

    return cmd


def append_log(user_id: int, project_key: str, mode: str, prompt: str, result: str) -> None:
    LOGS_DIR.mkdir(exist_ok=True)
    log_file = LOGS_DIR / f"{datetime.utcnow().strftime('%Y-%m-%d')}.log"
    now = datetime.utcnow().isoformat() + "Z"
    with log_file.open("a", encoding="utf-8") as f:
        f.write("\n" + "=" * 80 + "\n")
        f.write(f"time: {now}\nuser_id: {user_id}\nproject: {project_key}\nmode: {mode}\n")
        f.write("--- prompt ---\n")
        f.write(prompt[:3000] + ("\n...[truncated]" if len(prompt) > 3000 else ""))
        f.write("\n--- result ---\n")
        f.write(result[:6000] + ("\n...[truncated]" if len(result) > 6000 else ""))
        f.write("\n")


async def run_claude(project_path: str, prompt: str, mode: str) -> str:
    project_path_obj = Path(project_path).expanduser().resolve()
    if not project_path_obj.exists():
        return f"Папка проекта не найдена: {project_path_obj}"

    cmd = build_claude_command(prompt, mode)

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(project_path_obj),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=CLAUDE_TIMEOUT_SECONDS)
        out = stdout.decode("utf-8", errors="replace").strip()
        err = stderr.decode("utf-8", errors="replace").strip()

        if process.returncode != 0:
            return (
                "Claude Code завершился с ошибкой.\n\n"
                f"Код ошибки: {process.returncode}\n\n"
                f"stderr:\n{err or 'Нет текста ошибки'}\n\n"
                "Что проверить: `claude auth status --text`, путь к проекту, права пользователя tsoillc."
            )
        return out or "Claude Code не вернул текстовый ответ."

    except asyncio.TimeoutError:
        return "Задача слишком долго выполнялась и была остановлена по таймауту. Уменьши запрос или увеличь CLAUDE_TIMEOUT_SECONDS в .env."
    except FileNotFoundError:
        return f"Команда `{CLAUDE_BINARY}` не найдена. Укажи полный путь в .env: CLAUDE_BINARY=/home/tsoillc/.npm-global/bin/claude"
    except Exception as e:
        return f"Неожиданная ошибка: {type(e).__name__}: {e}"


async def require_access(update: Update) -> Optional[Dict[str, Any]]:
    user_id = update.effective_user.id
    user = get_user(user_id)
    if not user:
        await update.message.reply_text(
            f"Нет доступа. Отправь этот ID администратору:\n\n{user_id}"
        )
        return None
    return user


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = await require_access(update)
    if not user:
        return
    await update.message.reply_text(
        "Привет. Это закрытый бот команды для Claude Code на VPS.\n\n"
        "Команды:\n"
        "/id — показать твой Telegram ID\n"
        "/projects — список доступных проектов\n"
        "/use project_name — выбрать проект\n"
        "/where — показать активный проект\n"
        "/ask текст — спросить по проекту без изменения файлов\n"
        "/plan текст — получить план без изменения файлов\n"
        "/code текст — внести изменения, если у тебя есть права\n"
        "/health — проверить, видит ли бот Claude Code"
    )


async def my_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(str(update.effective_user.id))


async def health(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = await require_access(update)
    if not user:
        return

    checks = []
    checks.append(f"BOT_TOKEN: {'ok' if BOT_TOKEN else 'missing'}")
    checks.append(f"USERS_FILE: {'ok' if USERS_FILE.exists() else 'missing'}")
    checks.append(f"PROJECTS_FILE: {'ok' if PROJECTS_FILE.exists() else 'missing'}")

    try:
        result = subprocess.run([CLAUDE_BINARY, "auth", "status", "--text"], capture_output=True, text=True, timeout=20)
        checks.append(f"claude auth status exit: {result.returncode}")
        checks.append((result.stdout or result.stderr or "no output").strip()[:1200])
    except Exception as e:
        checks.append(f"claude auth status error: {type(e).__name__}: {e}")

    await update.message.reply_text("\n".join(checks))


async def projects(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = await require_access(update)
    if not user:
        return

    all_projects = get_projects()
    allowed = allowed_project_keys(user, all_projects)
    if not allowed:
        await update.message.reply_text("У тебя пока нет доступных проектов.")
        return

    lines = []
    for key in allowed:
        title = all_projects.get(key, {}).get("title", key)
        lines.append(f"- {key} — {title}")

    await update.message.reply_text(
        "Доступные проекты:\n\n" + "\n".join(lines) + "\n\nВыбрать проект: /use project_name"
    )


async def use_project(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = await require_access(update)
    if not user:
        return
    if not context.args:
        await update.message.reply_text("Напиши так: /use fil")
        return

    project_key = context.args[0].strip()
    all_projects = get_projects()
    if project_key not in all_projects:
        await update.message.reply_text("Такой проект не описан в projects.json.")
        return
    if not user_has_project(user, project_key, all_projects):
        await update.message.reply_text("У тебя нет доступа к этому проекту.")
        return

    set_active_project(update.effective_user.id, project_key)
    title = all_projects[project_key].get("title", project_key)
    await update.message.reply_text(f"Активный проект: {title}")


async def where(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = await require_access(update)
    if not user:
        return
    project_key = get_active_project(update.effective_user.id)
    if not project_key:
        await update.message.reply_text("Активный проект не выбран. Используй /projects и /use project_name")
        return

    all_projects = get_projects()
    project = all_projects.get(project_key, {})
    title = project.get("title", project_key)
    path = project.get("path", "path not found")
    await update.message.reply_text(f"Активный проект: {title}\nПапка: {path}")


async def handle_claude_command(update: Update, context: ContextTypes.DEFAULT_TYPE, mode: str) -> None:
    user_id = update.effective_user.id
    user = await require_access(update)
    if not user:
        return

    if mode == "code" and not user.get("can_edit", False):
        await update.message.reply_text("У тебя нет прав на изменение файлов. Используй /ask или /plan.")
        return

    user_text = " ".join(context.args).strip()
    if not user_text:
        await update.message.reply_text(f"Напиши запрос после команды. Например:\n/{mode} проверь структуру проекта")
        return
    if len(user_text) > MAX_PROMPT_CHARS:
        await update.message.reply_text(f"Запрос слишком длинный. Максимум: {MAX_PROMPT_CHARS} символов.")
        return

    project_key = get_active_project(user_id)
    if not project_key:
        await update.message.reply_text("Сначала выбери проект: /projects, затем /use project_name")
        return

    all_projects = get_projects()
    project = all_projects.get(project_key)
    if not project:
        await update.message.reply_text("Активный проект не найден в projects.json.")
        return
    if not user_has_project(user, project_key, all_projects):
        await update.message.reply_text("У тебя больше нет доступа к этому проекту.")
        return

    project_path = project["path"]
    title = project.get("title", project_key)
    lock = project_locks.setdefault(project_key, asyncio.Lock())
    if lock.locked():
        await update.message.reply_text("Этот проект уже обрабатывает другую задачу. Попробуй позже.")
        return

    await update.message.reply_text(f"Принял задачу для проекта: {title}")
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    user_name = user.get("name", str(user_id))
    prompt = build_prompt(mode, user_text, user_name)

    async with lock:
        result = await run_claude(project_path, prompt, mode)

    append_log(user_id, project_key, mode, user_text, result)

    for chunk in split_message(result):
        await update.message.reply_text(chunk)


async def ask(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await handle_claude_command(update, context, "ask")


async def plan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await handle_claude_command(update, context, "plan")


async def code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await handle_claude_command(update, context, "code")


def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN не задан. Скопируй .env.example в .env и заполни BOT_TOKEN.")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("id", my_id))
    app.add_handler(CommandHandler("health", health))
    app.add_handler(CommandHandler("projects", projects))
    app.add_handler(CommandHandler("use", use_project))
    app.add_handler(CommandHandler("where", where))
    app.add_handler(CommandHandler("ask", ask))
    app.add_handler(CommandHandler("plan", plan))
    app.add_handler(CommandHandler("code", code))
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
