# Вставь ВЕСЬ код бота, сохрани: Ctrl+X, Y, Enter# Вставь ВЕСЬ код бота, сохрани: Ctrl+X, Y, Enterimport 
# asyncio
import logging import os import html import time as 
time_module from datetime import datetime, date, time, 
timedelta from typing import Optional, Dict, Any, List, 
Tuple from contextlib import suppress from enum import 
Enum
# Теперь загрузи на GitHub (замени ТВОЙ_ЛОГИН на свой):
git initfrom aiogram import Bot, Dispatcher, Router, F 
from aiogram.types import ( git add bot.py 
requirements.txt .env.example Message, CallbackQuery, 
ReplyKeyboardMarkup, KeyboardButton, git commit -m "First 
commit" InlineKeyboardMarkup, InlineKeyboardButton ) from 
aiogram.filters import Command from aiogram.fsm.context 
import FSMContext from aiogram.fsm.state import State, 
StatesGroup from aiogram.fsm.storage.memory import 
MemoryStorage from aiogram.exceptions import ( git branch 
-M main TelegramRetryAfter, TelegramNetworkError, 
TelegramServerError, git remote add origin 
https://github.com/ТВОЙ_ЛОГИН/habit-bot.git 
TelegramBadRequest, TelegramForbiddenError ) from 
apscheduler.schedulers.asyncio import AsyncIOScheduler 
from apscheduler.triggers.cron import CronTrigger from 
apscheduler.jobstores.memory import MemoryJobStore import 
aiosqlite from dotenv import load_dotenv
git push -u origin main
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

API_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not API_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не найден в переменных окружения. Проверьте .env файл.")

DB_PATH = os.getenv("DB_PATH", "habits.db")
MAX_HABITS = 10
RATE_LIMIT_SECONDS = 2
RATE_LIMIT_CLEANUP_INTERVAL = 300
RETRY_MAX_ATTEMPTS = 3
RETRY_BASE_DELAY = 1.0
CALLBACK_EXPIRY_SECONDS = 86400

class HabitFrequency(Enum):
    DAILY = "daily"
    WEEKLY = "weekly"

class CheckStatus(Enum):
    DONE = "done"
    FAIL = "fail"
    SKIP = "skip"

class Messages:
    WELCOME = (
        "👋 <b>Привет, {first_name}!</b>\n\n"
        "Я — трекер привычек с системой streak-ов.\n"
        "Помогу тебе выработать полезные привычки!\n\n"
        "🔥 <b>Как это работает:</b>\n"
        "• Каждый день получаешь напоминания\n"
        "• Отмечаешь выполнение привычки\n"
        "• Растёт серия (streak) — главный показатель\n"
        "• Пропуск дня = сброс серии\n\n"
        "📊 <b>Твоя статистика:</b>\n"
        "• Активных привычек: {habits_count}/{max_habits}\n\n"
        "<i>Мотивация через страх потери прогресса! 💪</i>"
    )
    CANCEL_NO_ACTION = "Нет активных действий для отмены"
    CANCEL_DONE = "❌ Действие отменено. Можешь начать заново."
    LIMIT_REACHED = (
        "❌ <b>Достигнут лимит!</b>\n\n"
        "У тебя уже {max_habits} активных привычек.\n"
        "Удали какую-нибудь через меню 🗑 Удалить"
    )
    ADD_NAME_PROMPT = (
        "📝 <b>Шаг 1 из 3</b>\n\n"
        "Введи название привычки:\n"
        "<i>• От 1 до 50 символов\n"
        "• Например: 'Утренняя зарядка', 'Чтение 30 мин'</i>"
    )
    ADD_NAME_ERROR_LENGTH = (
        "❌ <b>Ошибка!</b>\n"
        "Название должно быть от 1 до 50 символов.\n"
        "Сейчас: {length} символов.\n\n"
        "Попробуй ещё раз:"
    )
    ADD_NAME_ERROR_CHARS = (
        "❌ Название содержит недопустимые символы.\n"
        "Используй только буквы, цифры, пробелы и базовую пунктуацию."
    )
    ADD_FREQ_PROMPT = (
        "🔄 <b>Шаг 2 из 3</b>\n\n"
        "Привычка: <b>{name}</b>\n"
        "Выбери частоту выполнения:"
    )
    ADD_TIME_PROMPT = (
        "⏰ <b>Шаг 3 из 3</b>\n\n"
        "Введи время напоминания в формате HH:MM (UTC):\n"
        "<i>Например: 09:00, 14:30, 20:00</i>"
    )
    ADD_TIME_ERROR = (
        "❌ <b>Неверный формат!</b>\n\n"
        "Введи время в формате HH:MM\n"
        "<i>Например: 09:00, 14:30, 20:00</i>"
    )
    ADD_SUCCESS = (
        "✅ <b>Привычка создана!</b>\n\n"
        "🎯 Название: <b>{name}</b>\n"
        "🔄 Частота: {freq_text}\n"
        "⏰ Напоминание: {time} UTC\n"
        "🔥 Серия: 0 дней\n\n"
        "<i>Я буду присылать напоминания в указанное время.</i>"
    )
    ADD_FAIL = (
        "❌ <b>Не удалось создать привычку!</b>\n\n"
        "Возможные причины:\n"
        "• Привычка с таким названием уже существует\n"
        "• Достигнут лимит привычек"
    )
    NO_HABITS = "📋 <b>У тебя пока нет привычек</b>\n\nНачни с создания первой привычки! 💪"
    HABITS_LIST_TITLE = "📋 <b>Твои привычки:</b>"
    NO_STATS = (
        "📊 <b>Статистика недоступна</b>\n\n"
        "У тебя пока нет привычек.\n"
        "Создай первую через ➕ Добавить"
    )
    STATS_OVERALL = (
        "📊 <b>Общая статистика</b>\n\n"
        "├─ 📋 Всего привычек: <b>{total_habits}</b>\n"
        "├─ 📝 Всего отметок: <b>{total_checks}</b>\n"
        "├─ ✅ Успешных: <b>{total_success}</b>\n"
        "├─ 📈 Общая успешность: <b>{overall_rate:.1f}%</b>\n"
        "├─ 🔥 Макс. текущая серия: <b>{max_streak} дн.</b>\n"
        "└─ 🏆 Лучшая серия за всё время: <b>{best_streak} дн.</b>\n"
    )
    STATS_DETAIL_TITLE = "<b>📈 Детальная статистика:</b>"
    STATS_DETAIL_ITEM = (
        "{index}. {icon} <b>{name}</b>\n"
        "   ├─ 🔥 Серия: {streak} дн.\n"
        "   ├─ 🏆 Рекорд: {best_streak} дн.\n"
        "   ├─ 📈 Успешность: {completion_rate}%\n"
        "   └─ 📊 {total_success}/{total_checks} усп. отм.\n"
    )
    DELETE_NO_HABITS = "🗑 <b>Нечего удалять</b>\n\nУ тебя пока нет привычек."
    DELETE_SELECT = (
        "🗑 <b>Выбери привычку для удаления:</b>\n\n"
        "<i>⚠️ Внимание! Это действие нельзя отменить.\n"
        "Серия и статистика будут потеряны.</i>"
    )
    DELETE_CONFIRM = (
        "⚠️ <b>Удаление привычки</b>\n\n"
        "🎯 <b>{name}</b>\n"
        "🔥 Текущая серия: {streak} дней\n"
        "🏆 Лучшая серия: {best_streak} дней\n\n"
        "Ты уверен? Все данные будут потеряны."
    )
    DELETE_SUCCESS = (
        "✅ <b>Привычка удалена</b>\n\n"
        "🎯 {name}\n"
        "📊 Финальная статистика:\n"
        "• Серия: {streak} дн.\n"
        "• Рекорд: {best_streak} дн.\n"
        "• Успешность: {completion_rate}%\n\n"
        "Создай новую привычку через ➕ Добавить"
    )
    DELETE_CANCELLED = "✅ Удаление отменено"
    REMINDER = (
        "⏰ <b>Напоминание</b>\n\n"
        "🎯 <b>{name}</b>\n"
        "Ты выполнил эту привычку?"
    )
    MISSED_DAY = (
        "⚠️ <b>Пропущен день!</b>\n\n"
        "🎯 {name}\n"
        "💔 Серия сброшена: <b>{old_streak} → 0</b>\n"
        "📅 Последняя отметка: {last_check}\n\n"
        "Начни новую серию сегодня! 💪"
    )
    CHECKIN_DONE = "✅ <b>{name}</b>\nВыполнено!\nСерия: {streak} 🔥\nЛучшая: {best_streak} 🏆"
    CHECKIN_FAIL = "❌ <b>{name}</b>\nПровал\nСерия: {streak} 💔\nЛучшая: {best_streak} 🏆"
    CHECKIN_SKIP = "⏭ <b>{name}</b>\nПропущено\nСерия: {streak} 🔥\nЛучшая: {best_streak} 🏆"
    ALREADY_CHECKED = "❌ Уже отмечено сегодня или привычка не найдена"
    RATE_LIMIT = "⏳ Слишком быстро! Подожди немного."
    FALLBACK = (
        "Я тебя не понял. Используй кнопки меню или команды:\n"
        "/start - начало\n"
        "/habits - список привычек\n"
        "/stats - статистика\n"
        "/delete - удалить привычку\n"
        "/cancel - отмена действия"
    )
    ERROR_USER = "❌ Ошибка. Используй /start"

class HabitStates(StatesGroup):
    name = State()
    frequency = State()
    time = State()

class HabitRecord:
    __slots__ = (
        'id', 'user_id', 'name', 'frequency_type', 'frequency_value',
        'reminder_time', 'streak', 'best_streak', 'total_checks',
        'total_success', 'last_check_date', 'is_active', 'telegram_id', 'timezone'
    )

    def __init__(self, **kwargs):
        self.id: int = kwargs.get('id', 0)
        self.user_id: int = kwargs.get('user_id', 0)
        self.name: str = kwargs.get('name', '')
        self.frequency_type: str = kwargs.get('frequency_type', 'daily')
        self.frequency_value: int = kwargs.get('frequency_value', 1)
        self.reminder_time: str = kwargs.get('reminder_time', '09:00')
        self.streak: int = kwargs.get('streak', 0)
        self.best_streak: int = kwargs.get('best_streak', 0)
        self.total_checks: int = kwargs.get('total_checks', 0)
        self.total_success: int = kwargs.get('total_success', 0)
        self.last_check_date: Optional[str] = kwargs.get('last_check_date')
        self.is_active: int = kwargs.get('is_active', 1)
        self.telegram_id: Optional[int] = kwargs.get('telegram_id')
        self.timezone: str = kwargs.get('timezone', 'UTC')

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> 'HabitRecord':
        return cls(**{k: row.get(k) for k in cls.__slots__ if k in row})

class DatabaseManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._connection: Optional[aiosqlite.Connection] = None
        self._lock = asyncio.Lock()

    async def get_connection(self) -> aiosqlite.Connection:
        if self._connection is None:
            async with self._lock:
                if self._connection is None:
                    self._connection = await aiosqlite.connect(self.db_path)
                    self._connection.row_factory = aiosqlite.Row
                    await self._connection.execute("PRAGMA journal_mode=WAL")
                    await self._connection.execute("PRAGMA foreign_keys=ON")
                    await self._connection.execute("PRAGMA busy_timeout=5000")
        return self._connection

    async def close(self):
        if self._connection:
            await self._connection.close()
            self._connection = None

    async def init_db(self):
        conn = await self.get_connection()
        await conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                timezone TEXT DEFAULT 'UTC',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS habits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                frequency_type TEXT NOT NULL CHECK(frequency_type IN ('daily', 'weekly')),
                frequency_value INTEGER DEFAULT 1,
                reminder_time TEXT NOT NULL,
                streak INTEGER DEFAULT 0,
                best_streak INTEGER DEFAULT 0,
                total_checks INTEGER DEFAULT 0,
                total_success INTEGER DEFAULT 0,
                last_check_date TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE(user_id, name)
            );

            CREATE INDEX IF NOT EXISTS idx_habits_user_active ON habits(user_id, is_active);
            CREATE INDEX IF NOT EXISTS idx_habits_last_check ON habits(last_check_date, is_active);
        """)
        await conn.commit()
        logger.info("Database initialized successfully")

    async def create_user(self, telegram_id: int, timezone: str = "UTC") -> int:
        conn = await self.get_connection()
        cursor = await conn.execute(
            "INSERT OR IGNORE INTO users (telegram_id, timezone) VALUES (?, ?)",
            (telegram_id, timezone)
        )
        await conn.commit()
        if cursor.lastrowid:
            return cursor.lastrowid
        cursor = await conn.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
        row = await cursor.fetchone()
        return row[0] if row else 0

    async def get_user_id(self, telegram_id: int) -> Optional[int]:
        conn = await self.get_connection()
        cursor = await conn.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
        row = await cursor.fetchone()
        return row[0] if row else None

    async def create_habit(self, user_id: int, name: str, frequency_type: str,
                           frequency_value: int, reminder_time: str) -> Optional[int]:
        conn = await self.get_connection()
        cursor = await conn.execute("SELECT COUNT(*) FROM habits WHERE user_id = ? AND is_active = 1", (user_id,))
        count = (await cursor.fetchone())[0]
        if count >= MAX_HABITS:
            logger.warning(f"User {user_id} reached max habits limit")
            return None
        try:
            cursor = await conn.execute(
                """INSERT INTO habits (user_id, name, frequency_type, frequency_value, reminder_time)
                   VALUES (?, ?, ?, ?, ?)""",
                (user_id, name, frequency_type, frequency_value, reminder_time)
            )
            await conn.commit()
            habit_id = cursor.lastrowid
            logger.info(f"Created habit {habit_id} for user {user_id}")
            return habit_id
        except aiosqlite.IntegrityError:
            logger.warning(f"Habit '{name}' already exists for user {user_id}")
            return None

    async def get_habits(self, user_id: int, active_only: bool = True) -> List[HabitRecord]:
        conn = await self.get_connection()
        query = "SELECT * FROM habits WHERE user_id = ?"
        if active_only:
            query += " AND is_active = 1"
        query += " ORDER BY created_at DESC"
        cursor = await conn.execute(query, (user_id,))
        rows = await cursor.fetchall()
        return [HabitRecord.from_row(dict(row)) for row in rows]

    async def get_habit_by_id(self, habit_id: int, user_id: int) -> Optional[HabitRecord]:
        conn = await self.get_connection()
        cursor = await conn.execute(
            "SELECT * FROM habits WHERE id = ? AND user_id = ?",
            (habit_id, user_id)
        )
        row = await cursor.fetchone()
        return HabitRecord.from_row(dict(row)) if row else None

    async def atomic_check_in(self, habit_id: int, user_id: int,
                               status: CheckStatus, today: str) -> Optional[Dict[str, Any]]:
        conn = await self.get_connection()

        cursor = await conn.execute("BEGIN IMMEDIATE")
        try:
            cursor = await conn.execute(
                "SELECT id, name, streak, best_streak, total_checks, total_success, last_check_date "
                "FROM habits WHERE id = ? AND user_id = ? AND is_active = 1",
                (habit_id, user_id)
            )
            row = await cursor.fetchone()
            if not row:
                await conn.execute("ROLLBACK")
                return None

            habit = dict(row)

            if habit['last_check_date'] == today:
                await conn.execute("ROLLBACK")
                logger.info(f"Habit {habit_id} already checked today by user {user_id}")
                return None

            new_streak = habit['streak']
            new_best = habit['best_streak']
            new_total = habit['total_checks'] + 1
            new_success = habit['total_success']

            if status == CheckStatus.DONE:
                new_streak += 1
                new_success += 1
                if new_streak > new_best:
                    new_best = new_streak
            elif status == CheckStatus.FAIL:
                new_streak = 0

            await conn.execute(
                """UPDATE habits SET streak = ?, best_streak = ?, total_checks = ?,
                   total_success = ?, last_check_date = ? WHERE id = ?""",
                (new_streak, new_best, new_total, new_success, today, habit_id)
            )
            await conn.execute("COMMIT")

            return {
                'id': habit_id,
                'name': habit['name'],
                'streak': new_streak,
                'best_streak': new_best,
                'total_checks': new_total,
                'total_success': new_success,
                'status': status
            }
        except Exception as e:
            await conn.execute("ROLLBACK")
            logger.error(f"Atomic check-in failed for habit {habit_id}: {e}")
            raise

    async def delete_habit(self, habit_id: int, user_id: int) -> bool:
        conn = await self.get_connection()
        cursor = await conn.execute(
            "UPDATE habits SET is_active = 0 WHERE id = ? AND user_id = ? AND is_active = 1",
            (habit_id, user_id)
        )
        await conn.commit()
        success = cursor.rowcount > 0
        if success:
            logger.info(f"Deleted habit {habit_id} for user {user_id}")
        return success

    async def get_all_active_habits(self) -> List[HabitRecord]:
        conn = await self.get_connection()
        cursor = await conn.execute("""
            SELECT h.*, u.telegram_id, u.timezone
            FROM habits h
            JOIN users u ON h.user_id = u.id
            WHERE h.is_active = 1
        """)
        rows = await cursor.fetchall()
        return [HabitRecord.from_row(dict(row)) for row in rows]

    async def get_habits_with_expired_streaks(self) -> List[HabitRecord]:
        conn = await self.get_connection()
        today = date.today().isoformat()
        cursor = await conn.execute("""
            SELECT h.*, u.telegram_id, u.timezone
            FROM habits h
            JOIN users u ON h.user_id = u.id
            WHERE h.is_active = 1
            AND h.last_check_date IS NOT NULL
            AND h.last_check_date < ?
            AND h.streak > 0
        """, (today,))
        rows = await cursor.fetchall()
        return [HabitRecord.from_row(dict(row)) for row in rows]

    async def atomic_streak_reset(self, habit_id: int, old_streak: int) -> bool:
        conn = await self.get_connection()
        cursor = await conn.execute("BEGIN IMMEDIATE")
        try:
            cursor = await conn.execute(
                "UPDATE habits SET streak = 0 WHERE id = ? AND streak = ?",
                (habit_id, old_streak)
            )
            updated = cursor.rowcount > 0
            await conn.execute("COMMIT")
            return updated
        except Exception as e:
            await conn.execute("ROLLBACK")
            logger.error(f"Atomic streak reset failed for habit {habit_id}: {e}")
            raise

class RateLimiter:
    def __init__(self, max_interval: float = RATE_LIMIT_SECONDS):
        self.storage: Dict[int, float] = {}
        self.max_interval = max_interval
        self._lock = asyncio.Lock()
        self._last_cleanup = time_module.monotonic()

    async def check_and_update(self, user_id: int) -> bool:
        async with self._lock:
            now = time_module.monotonic()
            if user_id in self.storage:
                if now - self.storage[user_id] < self.max_interval:
                    return False
            self.storage[user_id] = now
            if now - self._last_cleanup > RATE_LIMIT_CLEANUP_INTERVAL:
                self._cleanup_expired(now)
                self._last_cleanup = now
            return True

    def _cleanup_expired(self, now: float):
        expired = [uid for uid, ts in self.storage.items() if now - ts > self.max_interval * 10]
        for uid in expired:
            del self.storage[uid]

class CallbackValidator:
    def __init__(self, ttl: int = CALLBACK_EXPIRY_SECONDS):
        self._cache: Dict[str, float] = {}
        self._lock = asyncio.Lock()
        self.ttl = ttl

    def _make_key(self, user_id: int, habit_id: int, action: str, date_str: str) -> str:
        return f"{user_id}:{habit_id}:{action}:{date_str}"

    async def is_valid(self, user_id: int, habit_id: int, action: str, date_str: str) -> bool:
        key = self._make_key(user_id, habit_id, action, date_str)
        async with self._lock:
            now = time_module.monotonic()
            if key in self._cache:
                if now - self._cache[key] < self.ttl:
                    return False
            self._cache[key] = now
            self._cleanup(now)
            return True

    def _cleanup(self, now: float):
        expired = [k for k, v in self._cache.items() if now - v > self.ttl]
        for k in expired:
            del self._cache[k]

class HabitService:
    def __init__(self, db: DatabaseManager):
        self.db = db
        self._locks: Dict[int, asyncio.Lock] = {}

    def _get_lock(self, habit_id: int) -> asyncio.Lock:
        if habit_id not in self._locks:
            self._locks[habit_id] = asyncio.Lock()
        return self._locks[habit_id]

    @staticmethod
    def calculate_stats(habit: HabitRecord) -> Dict[str, Any]:
        completion_rate = 0.0
        if habit.total_checks > 0:
            completion_rate = (habit.total_success / habit.total_checks) * 100
        streak = habit.streak
        return {
            'name': habit.name,
            'streak': streak,
            'best_streak': habit.best_streak,
            'completion_rate': round(completion_rate, 1),
            'total_checks': habit.total_checks,
            'total_success': habit.total_success,
            'status_icon': '🔥' if streak > 0 else '❌',
            'status_text': 'Активна' if streak > 0 else 'Сброшена'
        }

    async def process_checkin(self, habit_id: int, user_id: int,
                              status: CheckStatus, today: str) -> Optional[Dict[str, Any]]:
        async with self._get_lock(habit_id):
            return await self.db.atomic_check_in(habit_id, user_id, status, today)

class SchedulerService:
    def __init__(self, scheduler: AsyncIOScheduler, db: DatabaseManager, bot: Bot):
        self.scheduler = scheduler
        self.db = db
        self.bot = bot
        self._known_jobs: set = set()

    def _make_job_id(self, habit_id: int) -> str:
        return f"habit_{habit_id}"

    def schedule_habit(self, habit: HabitRecord):
        job_id = self._make_job_id(habit.id)
        self.remove_job(habit.id)

        try:
            reminder_time = datetime.strptime(habit.reminder_time, "%H:%M").time()
            hour, minute = reminder_time.hour, reminder_time.minute

            if habit.frequency_type == HabitFrequency.DAILY.value:
                self.scheduler.add_job(
                    self._send_reminder_wrapper,
                    CronTrigger(hour=hour, minute=minute, timezone='UTC'),
                    args=[habit.id],
                    id=job_id,
                    replace_existing=True,
                    misfire_grace_time=300
                )
                self._known_jobs.add(job_id)
                logger.info(f"Scheduled daily habit {habit.id} at {hour:02d}:{minute:02d} UTC")

            elif habit.frequency_type == HabitFrequency.WEEKLY.value:
                days_count = max(1, min(habit.frequency_value, 7))
                days_of_week = ','.join(str(i) for i in range(days_count))

                self.scheduler.add_job(
                    self._send_reminder_wrapper,
                    CronTrigger(day_of_week=days_of_week, hour=hour, minute=minute, timezone='UTC'),
                    args=[habit.id],
                    id=job_id,
                    replace_existing=True,
                    misfire_grace_time=300
                )
                self._known_jobs.add(job_id)
                logger.info(
                    f"Scheduled weekly habit {habit.id} {days_count} days/week at {hour:02d}:{minute:02d} UTC"
                )
        except Exception as e:
            logger.error(f"Failed to schedule habit {habit.id}: {e}")

    def remove_job(self, habit_id: int):
        job_id = self._make_job_id(habit_id)
        with suppress(Exception):
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
                self._known_jobs.discard(job_id)
                logger.info(f"Removed job for habit {habit_id}")

    async def load_all_jobs_on_start(self):
        try:
            habits = await self.db.get_all_active_habits()
            loaded_ids = {self._make_job_id(h.id) for h in habits}
            for job in self.scheduler.get_jobs():
                if job.id not in loaded_ids and job.id != 'reset_missed':
                    self.scheduler.remove_job(job.id)
            for habit in habits:
                self.schedule_habit(habit)
            logger.info(f"Loaded {len(habits)} habits into scheduler")
        except Exception as e:
            logger.error(f"Error loading jobs on start: {e}")

    async def _send_reminder_wrapper(self, habit_id: int):
        habits = await self.db.get_all_active_habits()
        habit = next((h for h in habits if h.id == habit_id), None)

        if habit is None:
            self.remove_job(habit_id)
            return

        await self._send_reminder(habit)

    async def _send_reminder(self, habit: HabitRecord):
        today = date.today().isoformat()
        if habit.last_check_date == today:
            return

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Выполнил", callback_data=f"check_{habit.id}_done_{today}"),
                InlineKeyboardButton(text="❌ Провалил", callback_data=f"check_{habit.id}_fail_{today}"),
            ],
            [
                InlineKeyboardButton(text="⏭ Пропустить", callback_data=f"check_{habit.id}_skip_{today}")
            ]
        ])

        await self._retry_send_message(
            chat_id=habit.telegram_id,
            text=Messages.REMINDER.format(name=html.escape(habit.name)),
            reply_markup=keyboard
        )

    async def _retry_send_message(self, chat_id: int, text: str, reply_markup=None):
        for attempt in range(RETRY_MAX_ATTEMPTS):
            try:
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode="HTML"
                )
                return
            except TelegramRetryAfter as e:
                delay = e.retry_after
                logger.warning(f"Rate limited, retrying in {delay}s (attempt {attempt + 1})")
                await asyncio.sleep(delay)
            except (TelegramNetworkError, TelegramServerError) as e:
                delay = RETRY_BASE_DELAY * (2 ** attempt)
                logger.warning(f"Network error: {e}, retrying in {delay}s (attempt {attempt + 1})")
                await asyncio.sleep(delay)
            except TelegramForbiddenError:
                logger.warning(f"User {chat_id} blocked the bot")
                return
            except TelegramBadRequest as e:
                logger.error(f"Bad request for user {chat_id}: {e}")
                return
            except Exception as e:
                logger.error(f"Failed to send message: {e}")
                break
        logger.error(f"Failed to send message after {RETRY_MAX_ATTEMPTS} attempts")

    async def reset_missed_habits(self):
        logger.info("Running missed habits reset job")
        missed = await self.db.get_habits_with_expired_streaks()

        for habit in missed:
            old_streak = habit.streak
            success = await self.db.atomic_streak_reset(habit.id, old_streak)
            if not success:
                logger.info(f"Habit {habit.id} streak was already modified, skipping notification")
                continue

            logger.info(f"Reset streak for habit {habit.id} (was {old_streak})")

            await self._retry_send_message(
                chat_id=habit.telegram_id,
                text=Messages.MISSED_DAY.format(
                    name=html.escape(habit.name),
                    old_streak=old_streak,
                    last_check=habit.last_check_date or "нет данных"
                )
            )

        logger.info(f"Reset {len(missed)} missed habits")

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)

scheduler = AsyncIOScheduler(jobstores={'default': MemoryJobStore()}, timezone='UTC')
db_manager = DatabaseManager(DB_PATH)
habit_service = HabitService(db_manager)
scheduler_service = SchedulerService(scheduler, db_manager, bot)
rate_limiter = RateLimiter()
callback_validator = CallbackValidator()

main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Добавить")],
        [KeyboardButton(text="📋 Привычки"), KeyboardButton(text="📊 Статистика")],
        [KeyboardButton(text="🗑 Удалить")]
    ],
    resize_keyboard=True,
    input_field_placeholder="Выберите действие..."
)

cancel_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="/cancel")]],
    resize_keyboard=True
)

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await db_manager.create_user(message.from_user.id)
    user_id = await db_manager.get_user_id(message.from_user.id)
    habits_count = 0
    if user_id:
        habits = await db_manager.get_habits(user_id)
        habits_count = len(habits)

    first_name = html.escape(message.from_user.first_name or "Пользователь")
    await message.answer(
        Messages.WELCOME.format(first_name=first_name, habits_count=habits_count, max_habits=MAX_HABITS),
        reply_markup=main_keyboard,
        parse_mode="HTML"
    )

@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    if await state.get_state() is None:
        await message.answer(Messages.CANCEL_NO_ACTION, reply_markup=main_keyboard)
        return
    await state.clear()
    await message.answer(Messages.CANCEL_DONE, reply_markup=main_keyboard)

@router.message(F.text.in_(["➕ Добавить", "добавить", "+"]))
async def add_habit_start(message: Message, state: FSMContext):
    user_id = await db_manager.get_user_id(message.from_user.id)
    if not user_id:
        await message.answer(Messages.ERROR_USER)
        return

    habits = await db_manager.get_habits(user_id)
    if len(habits) >= MAX_HABITS:
        await message.answer(Messages.LIMIT_REACHED.format(max_habits=MAX_HABITS), parse_mode="HTML")
        return

    await state.set_state(HabitStates.name)
    await message.answer(Messages.ADD_NAME_PROMPT, reply_markup=cancel_keyboard, parse_mode="HTML")

@router.message(HabitStates.name)
async def habit_name_handler(message: Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 1 or len(name) > 50:
        await message.answer(Messages.ADD_NAME_ERROR_LENGTH.format(length=len(name)), parse_mode="HTML")
        return
    if any(char in name for char in ['<', '>', '&', '"', "'"]):
        await message.answer(Messages.ADD_NAME_ERROR_CHARS, parse_mode="HTML")
        return

    await state.update_data(name=name)
    await state.set_state(HabitStates.frequency)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Ежедневно", callback_data="freq_daily")],
        [InlineKeyboardButton(text="📆 1 раз в неделю", callback_data="weekly_1")],
        [InlineKeyboardButton(text="📆 2 раза в неделю", callback_data="weekly_2")],
        [InlineKeyboardButton(text="📆 3 раза в неделю", callback_data="weekly_3")],
        [InlineKeyboardButton(text="📆 5 раз в неделю", callback_data="weekly_5")],
        [InlineKeyboardButton(text="📆 7 раз в неделю", callback_data="weekly_7")]
    ])

    await message.answer(
        Messages.ADD_FREQ_PROMPT.format(name=html.escape(name)),
        reply_markup=keyboard,
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("freq_"))
async def frequency_callback(callback: CallbackQuery, state: FSMContext):
    freq_type = callback.data.split("_")[1]
    if freq_type == "daily":
        await state.update_data(frequency_type="daily", frequency_value=1)
        await state.set_state(HabitStates.time)
        await callback.message.edit_text("✅ Частота: <b>ежедневно</b>", parse_mode="HTML")
        await callback.message.answer(Messages.ADD_TIME_PROMPT, reply_markup=cancel_keyboard, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("weekly_"))
async def weekly_count_callback(callback: CallbackQuery, state: FSMContext):
    count = int(callback.data.split("_")[1])
    await state.update_data(frequency_type="weekly", frequency_value=count)
    await state.set_state(HabitStates.time)
    await callback.message.edit_text(f"✅ Частота: <b>{count} раз(а) в неделю</b>", parse_mode="HTML")
    await callback.message.answer(Messages.ADD_TIME_PROMPT, reply_markup=cancel_keyboard, parse_mode="HTML")
    await callback.answer()

@router.message(HabitStates.time)
async def habit_time_handler(message: Message, state: FSMContext):
    time_str = message.text.strip()
    try:
        parsed_time = datetime.strptime(time_str, "%H:%M")
        if not (0 <= parsed_time.hour <= 23 and 0 <= parsed_time.minute <= 59):
            raise ValueError
    except ValueError:
        await message.answer(Messages.ADD_TIME_ERROR, parse_mode="HTML")
        return

    data = await state.get_data()
    user_id = await db_manager.get_user_id(message.from_user.id)
    if not user_id:
        await message.answer(Messages.ERROR_USER)
        await state.clear()
        return

    habit_id = await db_manager.create_habit(
        user_id=user_id, name=data['name'],
        frequency_type=data['frequency_type'],
        frequency_value=data.get('frequency_value', 1),
        reminder_time=time_str
    )

    if habit_id is None:
        await message.answer(Messages.ADD_FAIL, parse_mode="HTML")
        await state.clear()
        await message.answer("Выбери действие:", reply_markup=main_keyboard)
        return

    habit = await db_manager.get_habit_by_id(habit_id, user_id)
    if habit:
        scheduler_service.schedule_habit(habit)

    freq_text = "ежедневно" if data['frequency_type'] == 'daily' else f"{data.get('frequency_value', 1)} раз(а) в неделю"

    await message.answer(
        Messages.ADD_SUCCESS.format(name=html.escape(data['name']), freq_text=freq_text, time=time_str),
        parse_mode="HTML"
    )
    await state.clear()
    await message.answer("Готово! Выбери следующее действие:", reply_markup=main_keyboard)

@router.message(F.text.in_(["📋 Привычки", "привычки", "habits"]))
async def list_habits(message: Message):
    user_id = await db_manager.get_user_id(message.from_user.id)
    if not user_id:
        await message.answer(Messages.ERROR_USER)
        return

    habits = await db_manager.get_habits(user_id)

    if not habits:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить первую привычку", callback_data="add_first")]
        ])
        await message.answer(Messages.NO_HABITS, reply_markup=keyboard, parse_mode="HTML")
        return

    await message.answer(Messages.HABITS_LIST_TITLE, parse_mode="HTML")
    today_str = date.today().isoformat()

    for habit in habits:
        stats = habit_service.calculate_stats(habit)

        habit_text = (
            f"{stats['status_icon']} <b>{html.escape(stats['name'])}</b>\n"
            f"├─ 🔥 Серия: <b>{stats['streak']} дней</b>\n"
            f"├─ 🏆 Рекорд: {stats['best_streak']} дней\n"
            f"├─ 📈 Успешность: {stats['completion_rate']}%\n"
            f"└─ 📊 Всего: {stats['total_checks']} отм. / {stats['total_success']} усп.\n"
            f"   <i>Статус: {stats['status_text']}</i>\n"
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Выполнил", callback_data=f"check_{habit.id}_done_{today_str}"),
                InlineKeyboardButton(text="❌ Провалил", callback_data=f"check_{habit.id}_fail_{today_str}"),
            ],
            [
                InlineKeyboardButton(text="⏭ Пропустить", callback_data=f"check_{habit.id}_skip_{today_str}")
            ]
        ])

        await message.answer(habit_text, reply_markup=keyboard, parse_mode="HTML")

@router.message(F.text.in_(["📊 Статистика", "статистика", "stats"]))
async def show_stats(message: Message):
    user_id = await db_manager.get_user_id(message.from_user.id)
    if not user_id:
        await message.answer(Messages.ERROR_USER)
        return

    habits = await db_manager.get_habits(user_id)
    if not habits:
        await message.answer(Messages.NO_STATS, parse_mode="HTML")
        return

    total_habits = len(habits)
    total_checks = sum(h.total_checks for h in habits)
    total_success = sum(h.total_success for h in habits)
    overall_rate = (total_success / total_checks * 100) if total_checks > 0 else 0.0
    max_streak = max((h.streak for h in habits), default=0)
    best_streak = max((h.best_streak for h in habits), default=0)

    stats_text = Messages.STATS_OVERALL.format(
        total_habits=total_habits, total_checks=total_checks, total_success=total_success,
        overall_rate=overall_rate, max_streak=max_streak, best_streak=best_streak
    )
    await message.answer(stats_text, parse_mode="HTML")
    await message.answer(Messages.STATS_DETAIL_TITLE, parse_mode="HTML")

    for i, habit in enumerate(habits, 1):
        stats = habit_service.calculate_stats(habit)
        detail_text = Messages.STATS_DETAIL_ITEM.format(
            index=i, icon=stats['status_icon'], name=html.escape(stats['name']),
            streak=stats['streak'], best_streak=stats['best_streak'],
            completion_rate=stats['completion_rate'],
            total_success=stats['total_success'], total_checks=stats['total_checks']
        )
        await message.answer(detail_text, parse_mode="HTML")

@router.message(F.text.in_(["🗑 Удалить", "удалить", "delete"]))
async def delete_habit_menu(message: Message):
    user_id = await db_manager.get_user_id(message.from_user.id)
    if not user_id:
        await message.answer(Messages.ERROR_USER)
        return

    habits = await db_manager.get_habits(user_id)
    if not habits:
        await message.answer(Messages.DELETE_NO_HABITS, parse_mode="HTML")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"{'🔥' if habit.streak > 0 else '❌'} {html.escape(habit.name)} (🔥{habit.streak})",
            callback_data=f"delconfirm_{habit.id}"
        )]
        for habit in habits
    ] + [[InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_del")]])

    await message.answer(Messages.DELETE_SELECT, reply_markup=keyboard, parse_mode="HTML")

@router.callback_query(F.data.startswith("delconfirm_"))
async def confirm_delete(callback: CallbackQuery):
    habit_id = int(callback.data.split("_")[1])
    user_id = await db_manager.get_user_id(callback.from_user.id)
    habit = await db_manager.get_habit_by_id(habit_id, user_id) if user_id else None

    if not habit:
        await callback.message.edit_text("❌ Привычка не найдена")
        await callback.answer()
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"del_{habit_id}"),
         InlineKeyboardButton(text="❌ Нет, оставить", callback_data="cancel_del")]
    ])

    await callback.message.edit_text(
        Messages.DELETE_CONFIRM.format(
            name=html.escape(habit.name), streak=habit.streak, best_streak=habit.best_streak
        ),
        reply_markup=keyboard, parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "cancel_del")
async def cancel_delete(callback: CallbackQuery):
    await callback.message.edit_text(Messages.DELETE_CANCELLED)
    await callback.answer()

@router.callback_query(F.data.startswith("del_"))
async def delete_habit_callback(callback: CallbackQuery):
    habit_id = int(callback.data.split("_")[1])
    user_id = await db_manager.get_user_id(callback.from_user.id)
    if not user_id:
        await callback.message.edit_text("❌ Ошибка пользователя")
        await callback.answer()
        return

    habit = await db_manager.get_habit_by_id(habit_id, user_id)
    if not habit:
        await callback.message.edit_text("❌ Привычка не найдена")
        await callback.answer()
        return

    success = await db_manager.delete_habit(habit_id, user_id)
    if success:
        scheduler_service.remove_job(habit_id)
        stats = habit_service.calculate_stats(habit)
        await callback.message.edit_text(
            Messages.DELETE_SUCCESS.format(
                name=html.escape(habit.name), streak=habit.streak,
                best_streak=habit.best_streak, completion_rate=stats['completion_rate']
            ),
            parse_mode="HTML"
        )
        logger.info(f"User {callback.from_user.id} deleted habit {habit_id}: {habit.name}")
    else:
        await callback.message.edit_text("❌ Не удалось удалить привычку")
    await callback.answer()

@router.callback_query(F.data == "add_first")
async def add_first_habit(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await add_habit_start(callback.message, state)
    await callback.answer()

@router.callback_query(F.data.startswith("check_"))
async def handle_checkin(callback: CallbackQuery):
    if not await rate_limiter.check_and_update(callback.from_user.id):
        await callback.answer(Messages.RATE_LIMIT, show_alert=True)
        return

    user_id = await db_manager.get_user_id(callback.from_user.id)
    if not user_id:
        await callback.answer("❌ Ошибка. Используй /start", show_alert=True)
        return

    try:
        parts = callback.data.split("_")
        if len(parts) < 4:
            raise ValueError("Missing date in callback")
        habit_id = int(parts[1])
        action = CheckStatus(parts[2])
        callback_date = parts[3]
    except (IndexError, ValueError):
        await callback.answer("❌ Некорректные данные", show_alert=True)
        return

    today = date.today().isoformat()
    if callback_date != today:
        await callback.answer("❌ Это напоминание за другой день", show_alert=True)
        return

    if not await callback_validator.is_valid(user_id, habit_id, action.value, today):
        await callback.answer("❌ Вы уже нажимали эту кнопку", show_alert=True)
        return

    result = await habit_service.process_checkin(habit_id, user_id, action, today)

    if result is None:
        await callback.answer(Messages.ALREADY_CHECKED, show_alert=True)
        return

    if action == CheckStatus.DONE:
        text = Messages.CHECKIN_DONE.format(
            name=html.escape(result['name']), streak=result['streak'], best_streak=result['best_streak']
        )
    elif action == CheckStatus.FAIL:
        text = Messages.CHECKIN_FAIL.format(
            name=html.escape(result['name']), streak=result['streak'], best_streak=result['best_streak']
        )
    else:
        text = Messages.CHECKIN_SKIP.format(
            name=html.escape(result['name']), streak=result['streak'], best_streak=result['best_streak']
        )

    try:
        await callback.message.edit_text(text, parse_mode="HTML")
    except TelegramBadRequest:
        pass
    await callback.answer()

@router.message(Command("habits"))
async def cmd_habits(message: Message):
    await list_habits(message)

@router.message(Command("stats"))
async def cmd_stats(message: Message):
    await show_stats(message)

@router.message(Command("delete"))
async def cmd_delete(message: Message):
    await delete_habit_menu(message)

@router.message()
async def fallback_handler(message: Message, state: FSMContext):
    if await state.get_state() is not None:
        await message.answer(
            "Вы находитесь в процессе создания привычки.\nИспользуйте /cancel для отмены.",
            reply_markup=cancel_keyboard
        )
        return
    await message.answer(Messages.FALLBACK, reply_markup=main_keyboard)

async def main():
    logger.info("Starting bot initialization...")
    await db_manager.init_db()

    scheduler.add_job(
        scheduler_service.reset_missed_habits,
        CronTrigger(hour=0, minute=5, timezone='UTC'),
        id='reset_missed',
        replace_existing=True,
        misfire_grace_time=300
    )

    scheduler.start()
    await scheduler_service.load_all_jobs_on_start()

    try:
        logger.info("Starting polling...")
        await dp.start_polling(bot)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Stopping bot...")
    except Exception as e:
        logger.error(f"Critical error: {e}")
    finally:
        scheduler.shutdown(wait=False)
        await db_manager.close()
        await bot.session.close()
        logger.info("Bot stopped")

if __name__ == "__main__":
    asyncio.run(main())
