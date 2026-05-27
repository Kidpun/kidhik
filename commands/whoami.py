"""
Команда .whoami
Показывает личную статистику пользователя
"""
import logging
from telethon import events
from utils.username_helper import get_user_username

logger = logging.getLogger(__name__)


async def whoami_command(event: events.NewMessage.Event):
    """
    Обработчик команды .whoami
    Показывает личную статистику пользователя
    """
    try:
        # Получаем информацию о себе
        me = await event.client.get_me()
        
        # Получаем данные
        user_id = me.id
        first_name = getattr(me, 'first_name', '')
        last_name = getattr(me, 'last_name', '') or ''
        
        # Получаем username (включая NFT)
        username = await get_user_username(event.client, me)
        
        # Формируем имя
        full_name = f"{first_name} {last_name}".strip() or "Unknown"
        
        # Формируем username пользователя
        username_text = f"@{username}" if username else "нет"
        
        # Формируем сообщение
        # Первая строка всегда показывает @kidhik (username канала бота)
        text = f"👤 <b>Вы - пользователь КИДХИК</b> @kidhik\n\n"
        text += f"📝 <b>Ваше имя:</b> {full_name}\n"
        text += f"📱 <b>Ваш юзернейм:</b> {username_text}\n"
        text += f"🆔 <b>Ваш ID:</b> <code>{user_id}</code>"
        
        await event.respond(text, parse_mode='html')
        
    except Exception as e:
        logger.error(f"Ошибка в команде .whoami: {e}", exc_info=True)
        await event.respond("❌ Ошибка при получении информации")

