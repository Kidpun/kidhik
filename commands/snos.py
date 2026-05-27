"""
Команда .снос
Показывает прогресс "сноса" от 0% до 99%, затем ошибку
Работает через userbot во всех чатах
"""
import asyncio
import logging
import random
from telethon import events
from telethon.errors import FloodWaitError

from utils.user_manager import user_manager

logger = logging.getLogger(__name__)


async def snos_command(event: events.NewMessage.Event):
    """
    Обработчик команды .снос
    """
    user_id = event.sender_id
    chat_id = event.chat_id
    chat = await event.get_chat()
    chat_title = getattr(chat, 'title', 'Private Chat')
    
    # Останавливаем предыдущий процесс, если есть
    user_manager.stop(user_id)
    
    logger.info(f"🚀 .снос command received from user {user_id} in chat {chat_id} (title: {chat_title})")
    
    # Создаём задачу для показа прогресса
    task = asyncio.create_task(_snos_progress(user_id, chat_id, event.client))
    user_manager.set_active(user_id, "снос", task)


async def _snos_progress(user_id: int, chat_id: int, client):
    """
    Показывает прогресс сноса
    """
    try:
        # Отправляем начальное сообщение
        try:
            progress_msg = await client.send_message(chat_id, "НАЧИНАЮ СНОС - 0%")
        except FloodWaitError as e:
            logger.warning(f"FloodWaitError при отправке начального сообщения: нужно подождать {e.seconds} секунд")
            # Ждём и пробуем снова
            await asyncio.sleep(e.seconds + 5)
            progress_msg = await client.send_message(chat_id, "НАЧИНАЮ СНОС - 0%")
        
        percentage = 0
        
        while percentage < 99:
            # Проверяем, не остановлен ли процесс
            if not user_manager.is_active(user_id) or user_manager.get_active_command(user_id) != "снос":
                try:
                    await progress_msg.delete()
                except Exception:
                    pass
                break
            
            # Увеличиваем процент
            if percentage < 30:
                percentage += 5
            else:
                percentage += 10
            
            # Ограничиваем до 99%
            if percentage > 99:
                percentage = 99
            
            # Редактируем сообщение
            try:
                await progress_msg.edit(f"НАЧИНАЮ СНОС - {percentage}%")
            except FloodWaitError as e:
                logger.warning(f"FloodWaitError при редактировании: нужно подождать {e.seconds} секунд")
                # Ждём указанное время
                await asyncio.sleep(e.seconds + 2)
                # Пробуем снова
                try:
                    await progress_msg.edit(f"НАЧИНАЮ СНОС - {percentage}%")
                except Exception:
                    pass
            except Exception as e:
                logger.error(f"Error editing snos message: {e}")
                # Если не можем редактировать, прекращаем
                if "message can't be edited" in str(e).lower() or "message not found" in str(e).lower():
                    break
            
            # Ждём перед следующим обновлением (от 1 до 3 секунд - безопасная задержка)
            await asyncio.sleep(random.uniform(1, 3))
        
        # Если дошли до 99%, показываем ошибку
        if percentage >= 99:
            try:
                await progress_msg.edit(
                    "ОШИБКА СНОСА\n"
                    "причина: его защищает аллах"
                )
            except FloodWaitError as e:
                logger.warning(f"FloodWaitError при финальном редактировании: нужно подождать {e.seconds} секунд")
                await asyncio.sleep(e.seconds + 2)
                try:
                    await progress_msg.edit(
                        "ОШИБКА СНОСА\n"
                        "причина: его защищает аллах"
                    )
                except Exception:
                    pass
            except Exception as e:
                logger.error(f"Error editing final snos message: {e}")
            
            # Останавливаем процесс после завершения
            await asyncio.sleep(2)
            user_manager.stop(user_id)
            
    except asyncio.CancelledError:
        logger.info(f"Snos progress cancelled for user {user_id}")
        try:
            await progress_msg.delete()
        except Exception:
            pass
    except Exception as e:
        logger.error(f"Error in snos progress for user {user_id}: {e}")
