"""
Команда .троль
Отправляет случайные фразы из файла text/troll.txt
Работает через userbot во всех чатах
"""
import asyncio
import random
import logging
from pathlib import Path
from telethon import events
from telethon.errors import FloodWaitError

from config import TROLL_FILE
from utils.user_manager import user_manager

logger = logging.getLogger(__name__)


def _load_troll_phrases() -> list:
    """Загружает фразы из файла troll.txt"""
    try:
        if not TROLL_FILE.exists():
            logger.warning(f"Troll file not found: {TROLL_FILE}")
            return ["Троль файл не найден"]
        
        with open(TROLL_FILE, 'r', encoding='utf-8') as f:
            phrases = [line.strip() for line in f if line.strip()]
        
        if not phrases:
            return ["Файл тролля пуст"]
        
        return phrases
    except Exception as e:
        logger.error(f"Error loading troll phrases: {e}")
        return ["Ошибка загрузки фраз"]


async def troll_command(event: events.NewMessage.Event):
    """
    Обработчик команды .троль
    Использование:
    .троль - обычный режим
    .троль @username - тегает пользователя
    .троль (реплай) - тегает автора сообщения
    """
    user_id = event.sender_id
    chat_id = event.chat_id
    chat = await event.get_chat()
    chat_title = getattr(chat, 'title', 'Private Chat')
    
    # Останавливаем предыдущий процесс, если есть
    user_manager.stop(user_id)
    
    # Загружаем фразы
    phrases = _load_troll_phrases()
    
    if not phrases:
        await event.respond("Файл тролля пуст или не найден")
        return
    
    # Определяем цель (target) для тега
    target_user = None
    target_mention = None
    
    # 1. Проверяем реплай
    if event.message.is_reply:
        try:
            replied_msg = await event.get_reply_message()
            if replied_msg and replied_msg.sender_id != user_id:
                target_user = await replied_msg.get_sender()
                # Формируем упоминание
                target_mention = f"[{target_user.first_name}](tg://user?id={target_user.id})"
                logger.info(f"Target set via reply: {target_user.id}")
        except Exception as e:
            logger.debug(f"Error getting reply target: {e}")
    
    # 2. Если нет реплая - проверяем @username в тексте
    if not target_user:
        text = event.message.text.strip()
        if '@' in text:
            parts = text.split()
            for part in parts:
                if part.startswith('@') and len(part) > 1:
                    username = part[1:]
                    try:
                        target_user = await event.client.get_entity(username)
                        if target_user.id != user_id:
                            target_mention = f"[{target_user.first_name}](tg://user?id={target_user.id})"
                            logger.info(f"Target set via @username: {target_user.id}")
                        break
                    except Exception as e:
                        logger.debug(f"Error getting @username target: {e}")
    
    logger.info(f"🚀 .троль command received from user {user_id} in chat {chat_id} (title: {chat_title}, target: {target_mention is not None})")
    
    # Создаём задачу для отправки фраз
    task = asyncio.create_task(_troll_loop(user_id, chat_id, phrases, event.client, target_mention))
    user_manager.set_active(user_id, "троль", task)


async def _troll_loop(user_id: int, chat_id: int, phrases: list, client, target_mention: str = None):
    """
    Цикл отправки случайных фраз из файла
    Работает до команды .стоп
    
    Args:
        user_id: ID пользователя
        chat_id: ID чата
        phrases: Список фраз для отправки
        client: Telegram клиент
        target_mention: Упоминание цели (формат: [Имя](tg://user?id=123))
    """
    try:
        while True:
            # Проверяем, не остановлен ли процесс
            if not user_manager.is_active(user_id) or user_manager.get_active_command(user_id) != "троль":
                break
            
            # Выбираем случайную фразу
            phrase = random.choice(phrases)
            
            # Если есть цель - добавляем упоминание в начало
            if target_mention:
                message = f"{target_mention}, {phrase}"
            else:
                message = phrase
            
            try:
                # Отправляем с parse_mode='md' если есть упоминание
                if target_mention:
                    await client.send_message(chat_id, message, parse_mode='md')
                else:
                    await client.send_message(chat_id, message)
            except FloodWaitError as e:
                logger.warning(f"FloodWaitError: нужно подождать {e.seconds} секунд")
                # Ждём указанное время + небольшой запас
                await asyncio.sleep(e.seconds + 5)
                # Пропускаем эту итерацию, продолжаем дальше
                continue
            except Exception as e:
                logger.error(f"Error sending message in troll (chat {chat_id}): {e}")
                # Если ошибка критическая, прекращаем работу
                if "chat not found" in str(e).lower() or "you were blocked" in str(e).lower():
                    break
                # При других ошибках ждём подольше
                await asyncio.sleep(5)
            
            # Ждём перед следующей отправкой (от 0.5 до 2 секунд - быстрая отправка)
            await asyncio.sleep(random.uniform(0.5, 2.0))
            
    except asyncio.CancelledError:
        logger.info(f"Troll loop cancelled for user {user_id}")
    except Exception as e:
        logger.error(f"Error in troll loop for user {user_id}: {e}")
