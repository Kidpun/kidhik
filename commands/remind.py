"""
.напомни <время> <текст> — установить напоминание
Примеры:
  .напомни 10м позвонить маме
  .напомни 2ч выпить воды
  .напомни 1д день рождения друга
"""
import asyncio
import re
import logging

logger = logging.getLogger(__name__)

# Хранилище активных напоминаний: task объекты
# Автоматически чистится через task.add_done_callback
_reminders: dict[int, list[asyncio.Task]] = {}

# Регэксп времени вынесен на модуль-уровень (быстрее)
_TIME_RE = re.compile(r'^(\d+)\s*([смчдsmhd])', re.IGNORECASE)

_MULTIPLIERS = {
    'с': 1, 's': 1,
    'м': 60, 'm': 60,
    'ч': 3600, 'h': 3600,
    'д': 86400, 'd': 86400,
}

_MAX_SECONDS = 7 * 86400  # максимум 7 дней


def _parse_time(text: str) -> tuple[int, str]:
    """
    Парсит строку вида '10м', '2ч', '1д', '30с' и т.д.
    Возвращает (секунды, остаток_строки).
    """
    m = _TIME_RE.match(text.strip())
    if not m:
        return 0, text

    amount = int(m.group(1))
    unit = m.group(2).lower()
    seconds = amount * _MULTIPLIERS.get(unit, 1)
    rest = text[m.end():].strip()
    return seconds, rest


def _format_duration(seconds: int) -> str:
    """Человеко-читаемая длительность."""
    if seconds < 60:
        return f"{seconds} сек"
    if seconds < 3600:
        return f"{seconds // 60} мин"
    if seconds < 86400:
        return f"{seconds // 3600} ч"
    return f"{seconds // 86400} д"


async def remind_command(event):
    """Обработчик команды .напомни"""
    try:
        args = event.raw_text.split(None, 1)
        if len(args) < 2:
            await event.edit(
                "⏰ **Напоминание**\n\n"
                "Использование: `.напомни <время> <текст>`\n"
                "Примеры:\n"
                "  `.напомни 10м позвонить маме`\n"
                "  `.напомни 2ч выпить воды`\n"
                "  `.напомни 1д день рождения`\n\n"
                "Единицы: `с`/`s` — секунды, `м`/`m` — минуты, `ч`/`h` — часы, `д`/`d` — дни"
            )
            return

        seconds, remind_text = _parse_time(args[1])

        if seconds <= 0:
            await event.edit("❌ Не могу распознать время. Пример: `10м`, `2ч`, `1д`")
            return

        if not remind_text:
            await event.edit("❌ Укажи текст напоминания. Пример: `.напомни 10м позвонить`")
            return

        if seconds > _MAX_SECONDS:
            await event.edit("❌ Максимум — 7 дней")
            return

        time_str = _format_duration(seconds)
        chat_id = event.chat_id
        sender_id = event.sender_id
        msg_id = event.id
        client = event.client

        await event.edit(f"✅ Напоминание через **{time_str}**: _{remind_text}_")

        async def _fire():
            try:
                await asyncio.sleep(seconds)
                await client.send_message(
                    chat_id,
                    f"⏰ **Напоминание!**\n\n{remind_text}",
                    reply_to=msg_id
                )
            except asyncio.CancelledError:
                # Корректное завершение при остановке userbot
                raise
            except Exception as e:
                logger.error(f"Ошибка отправки напоминания: {e}", exc_info=True)

        task = asyncio.create_task(_fire(), name=f"remind-{sender_id}-{msg_id}")
        _reminders.setdefault(sender_id, []).append(task)

        # Чистим завершённые задачи, чтобы не текла память
        def _cleanup(t: asyncio.Task, sid: int = sender_id):
            try:
                _reminders.get(sid, []).remove(t)
                if not _reminders.get(sid):
                    _reminders.pop(sid, None)
            except (ValueError, KeyError):
                pass
        task.add_done_callback(_cleanup)

    except Exception as e:
        logger.error(f"remind_command error: {e}", exc_info=True)
        try:
            await event.edit("❌ Ошибка установки напоминания")
        except Exception:
            pass
