"""
Команда .откат
Удаляет сообщение пользователя и начинает отправлять случайные фразы
Работает через userbot во всех чатах
"""
import asyncio
import random
import logging
from telethon import events
from telethon.errors import FloodWaitError

from config import OTKAT_PHRASES, OTKAT_REPLY_CHANCE
from utils.user_manager import user_manager
from utils.message_cache import message_cache

logger = logging.getLogger(__name__)


async def otkat_command(event: events.NewMessage.Event):
    """
    Обработчик команды .откат
    Работает везде через userbot
    """
    user_id = event.sender_id
    chat_id = event.chat_id
    chat = await event.get_chat()
    chat_title = getattr(chat, 'title', 'Private Chat')
    
    # Останавливаем предыдущий процесс, если есть
    user_manager.stop(user_id)
    
    logger.info(f"🚀 .откат command received from user {user_id} in chat {chat_id} (title: {chat_title})")
    
    # Создаём задачу для отправки фраз
    task = asyncio.create_task(_otkat_loop(user_id, chat_id, event.client))
    user_manager.set_active(user_id, "откат", task)


async def _otkat_loop(user_id: int, chat_id: int, client):
    """
    Цикл отправки случайных фраз для команды .откат
    Работает до команды .стоп
    Отправляет сообщения только после сообщений других пользователей
    """
    try:
        # Получаем свой ID для проверки
        me = await client.get_me()
        me_id = me.id
        
        # Отслеживаем последнее сообщение от других пользователей
        last_other_message_id = None
        
        while True:
            # Проверяем, не остановлен ли процесс
            if not user_manager.is_active(user_id) or user_manager.get_active_command(user_id) != "откат":
                break
            
            # Проверяем, есть ли новые сообщения от других пользователей
            # Передаем user_id для получения изолированного кеша
            last_message = message_cache.get_last_message(user_id, chat_id)
            if last_message:
                # Проверяем, что сообщение не от нас
                msg_user_id = None
                
                # Пробуем разные способы получить sender_id
                if hasattr(last_message, 'sender_id'):
                    msg_user_id = last_message.sender_id
                elif hasattr(last_message, 'from_id'):
                    sender_id = last_message.from_id
                    if sender_id:
                        # Получаем user_id из from_id (может быть PeerUser)
                        if hasattr(sender_id, 'user_id'):
                            msg_user_id = sender_id.user_id
                        elif hasattr(sender_id, 'channel_id'):
                            # Это сообщение из канала, пропускаем
                            msg_user_id = None
                        else:
                            msg_user_id = sender_id
                
                # Если сообщение от другого пользователя
                if msg_user_id and msg_user_id != me_id:
                        msg_id = getattr(last_message, 'id', None)
                        # Если это новое сообщение (не то же самое)
                        if msg_id != last_other_message_id:
                            last_other_message_id = msg_id
                            
                            # Выбираем случайную фразу
                            phrase = random.choice(OTKAT_PHRASES)
                            
                            # С шансом 20% пытаемся сделать reply на последнее сообщение
                            try:
                                if random.random() < OTKAT_REPLY_CHANCE:
                                    try:
                                        await client.send_message(
                                            chat_id,
                                            phrase,
                                            reply_to=last_message
                                        )
                                    except FloodWaitError as e:
                                        logger.warning(f"FloodWaitError при reply: нужно подождать {e.seconds} секунд")
                                        await asyncio.sleep(e.seconds + 5)
                                        continue
                                    except Exception as reply_err:
                                        # Если не удалось отправить reply, отправляем обычное сообщение
                                        logger.debug(f"Could not send reply, sending normal message: {reply_err}")
                                        try:
                                            await client.send_message(chat_id, phrase)
                                        except FloodWaitError as e:
                                            logger.warning(f"FloodWaitError: нужно подождать {e.seconds} секунд")
                                            await asyncio.sleep(e.seconds + 5)
                                            continue
                                else:
                                    try:
                                        await client.send_message(chat_id, phrase)
                                    except FloodWaitError as e:
                                        logger.warning(f"FloodWaitError: нужно подождать {e.seconds} секунд")
                                        await asyncio.sleep(e.seconds + 5)
                                        continue
                            except FloodWaitError as e:
                                logger.warning(f"FloodWaitError: нужно подождать {e.seconds} секунд")
                                await asyncio.sleep(e.seconds + 5)
                                continue
                            except Exception as e:
                                logger.error(f"Error sending message in otkat (chat {chat_id}): {e}")
                                # Если ошибка критическая, прекращаем работу
                                if "chat not found" in str(e).lower() or "you were blocked" in str(e).lower():
                                    break
                                # При других ошибках ждём подольше
                                await asyncio.sleep(5)
            
            # Ждём перед следующей проверкой (от 1 до 3 секунд)
            await asyncio.sleep(random.uniform(1, 3))
            
    except asyncio.CancelledError:
        logger.info(f"Otkat loop cancelled for user {user_id}")
    except Exception as e:
        logger.error(f"Error in otkat loop for user {user_id}: {e}")
