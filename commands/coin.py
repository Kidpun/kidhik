"""
Команда .монетка
Бросает монетку с шансом 50/50 (орел/решка)
Одноразовая команда
"""
import logging
import random
from telethon import events

logger = logging.getLogger(__name__)


async def coin_command(event: events.NewMessage.Event):
    """
    Обработчик команды .монетка
    Бросает монетку с равным шансом выпадения орла или решки
    """
    try:
        # Генерируем случайный результат (0 - орел, 1 - решка)
        result = random.choice(['орел', 'решка'])

        # Определяем эмодзи для результата
        emoji = '🪙' if result == 'орел' else '🪙'

        # Отправляем результат
        await event.respond(
            f"🪙 <b>Монетка:</b> {result.upper()}!\n\n"
            f"🎲 Случайный бросок завершен.",
            parse_mode='html'
        )

        logger.info(f"User {event.sender_id} flipped coin: {result}")

    except Exception as e:
        logger.error(f"Error in coin command: {e}", exc_info=True)
        await event.respond("❌ Ошибка при броске монетки")














