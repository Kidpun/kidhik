"""
Обработчик всех сообщений
Сохраняет сообщения в кеш для использования в командах
"""
import logging
import asyncio
from telethon import events
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument
from utils.message_cache import message_cache

logger = logging.getLogger(__name__)

async def save_message_handler(event: events.NewMessage.Event, user_id: int):
    """
    Сохраняет все сообщения в кеш.
    Если в сообщении есть медиа, мы подготавливаем его к возможному удалению.
    """
    try:
        # Пропускаем свои сообщения
        if event.sender_id == user_id:
            return
        
        # Сохраняем в кеш (для .откат и логов удалений)
        chat_id = event.chat_id
        message_cache.add_message(user_id, chat_id, event.message)
        
        # Если это фото или небольшое видео - мы НЕ скачиваем его сразу (чтобы не забить диск),
        # но кеш Telethon теперь знает об этом сообщении.
        # Основная магия скачивания будет в deleted_message_handler.
        
    except Exception as e:
        logger.error(f"Ошибка при сохранении сообщения в кеш для {user_id}: {e}")
