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
from telethon import events

logger = logging.getLogger(__name__)

# Хранилище активных напоминаний: task объекты
_reminders: dict[int, list[asyncio.Task]] = {}


def _parse_time(text: str) -> tuple[int, str]:
    """
    Парсит строку вида '10м', '2ч', '1д', '30с' и т.д.
    Возвращает (секунды, остаток_строки).
    """
    pattern = r'^(\d+)\s*([смчдsmhd])'
    m = re.match(pattern, text.strip(), re.IGNORECASE)
    if not m:
        return 0, text

    amount = int(m.group(1))
    unit = m.group(2).lower()

    multipliers = {
        'с': 1, 's': 1,
        'м': 60, 'm': 60,
        'ч': 3600, 'h': 3600,
        'д': 86400, 'd': 86400,
    }
    seconds = amount * multipliers.get(unit, 1)
    rest = text[m.end():].strip()
    return seconds, rest


async def remind_command(event):
    """Обработчик команды .напомни"""
    try:
        args = event.raw_text.split(None, 1)
        if len(args) < 2:
            await event.respond(
                "⏰ **Напоминание**\n\n"
                "Использование: `.напомни <время> <текст>`\n"
                "Примеры:\n"
                "  `.напомни 10м позвонить маме`\n"
                "  `.напомни 2ч выпить воды`\n"
                "  `.напомни 1д день рождения`\n\n"
                "Единицы: `с`/`s` — секунды, `м`/`m` — минуты, `ч`/`h` — часы, `д`/`d` — дни"
            )
            return

        payload = args[1]
        seconds, remind_text = _parse_time(payload)

        if seconds <= 0:
            await event.respond("❌ Не могу распознать время. Пример: `10м`, `2ч`, `1д`")
            return

        if not remind_text:
            await event.respond("❌ Укажи текст напоминания. Пример: `.напомни 10м позвонить`")
            return

        if seconds > 7 * 86400:
            await event.respond("❌ Максимум — 7 дней")
            return

        # Форматируем время для отображения
        if seconds < 60:
            time_str = f"{seconds} сек"
        elif seconds < 3600:
            time_str = f"{seconds // 60} мин"
        elif seconds < 86400:
            time_str = f"{seconds // 3600} ч"
        else:
            time_str = f"{seconds // 86400} д"

        chat_id = event.chat_id
        sender_id = event.sender_id
        msg_id = event.id

        confirm = await event.respond(f"✅ Напоминание через **{time_str}**: _{remind_text}_")

        async def _fire():
            await asyncio.sleep(seconds)
            try:
                await event.client.send_message(
                    chat_id,
                    f"⏰ **Напоминание!**\n\n{remind_text}",
                    reply_to=msg_id
                )
            except Exception as e:
                logger.error(f"Ошибка отправки напоминания: {e}")

        task = asyncio.create_task(_fire())
        _reminders.setdefault(sender_id, []).append(task)

    except Exception as e:
        logger.error(f"remind_command error: {e}", exc_info=True)
