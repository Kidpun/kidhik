"""
Команда .стоп
Останавливает все активные процессы пользователя
Работает через userbot во всех чатах
"""
import logging
from telethon import events
from telethon.errors import FloodWaitError

from utils.user_manager import user_manager

logger = logging.getLogger(__name__)

# Импортируем active_sglypa_chats после определения logger, чтобы избежать циклических импортов
try:
    from commands.sglypa import active_sglypa_chats
except ImportError:
    active_sglypa_chats = {}

# Импортируем user_reactions для остановки реакций
try:
    from commands.reactions import user_reactions
    logger.info(f"Successfully imported user_reactions from reactions module: {type(user_reactions)}")
except ImportError as e:
    user_reactions = {}
    logger.error(f"Failed to import user_reactions: {e}")


async def stop_command(event: events.NewMessage.Event):
    """
    Обработчик команды .стоп
    Немедленно останавливает все активные процессы пользователя
    """
    user_id = event.sender_id
    
    # Останавливаем активный процесс
    was_active = user_manager.stop(user_id)
    
    # Деактивируем все активные сглыпы для этого пользователя
    try:
        me = await event.client.get_me()
        if me.id == user_id:
            # Деактивируем все сглыпы
            for chat_id in list(active_sglypa_chats.keys()):
                active_sglypa_chats[chat_id] = False
    except Exception:
        pass
    
    # Останавливаем реакции для этого пользователя
    try:
        logger.info(f"Stopping reactions for user {user_id}. Current user_reactions keys: {list(user_reactions.keys())}")
        # Удаляем все реакции для этого пользователя
        keys_to_remove = [key for key in user_reactions.keys() if key[0] == user_id]
        logger.info(f"Keys to remove for user {user_id}: {keys_to_remove}")
        for key in keys_to_remove:
            del user_reactions[key]
        if keys_to_remove:
            logger.info(f"Stopped reactions for user {user_id} in {len(keys_to_remove)} chats. Remaining keys: {list(user_reactions.keys())}")
        else:
            logger.info(f"No reactions found to stop for user {user_id}")
    except Exception as e:
        logger.error(f"Error stopping reactions: {e}", exc_info=True)
    
    try:
        if was_active:
            await event.respond("✅ Все активные процессы остановлены")
            logger.info(f"User {user_id} stopped all processes")
        else:
            await event.respond("Нет активных процессов для остановки")
    except FloodWaitError as e:
        logger.warning(f"FloodWaitError при отправке ответа на .стоп: нужно подождать {e.seconds} секунд")
        # Просто логируем, не отправляем ответ - процесс уже остановлен
    except Exception as e:
        logger.error(f"Error responding to stop command: {e}")
