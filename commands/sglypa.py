"""
Команда .сглыпа
Режим сглыпы - пересылает случайные сообщения пользователей из чата (скрывая ник)
Работает индивидуально для каждого пользователя
"""
import asyncio
import random
import logging
import time
import re
from collections import deque
from telethon import events
from telethon.errors import FloodWaitError
from telethon.tl.types import MessageMediaDocument, MessageMediaPhoto, DocumentAttributeSticker

from utils.user_manager import user_manager
from utils.message_cache import message_cache

logger = logging.getLogger(__name__)

# Хранилище активных чатов для сглыпы
# (user_id, chat_id) -> Task
active_sglypa_tasks = {}

# Хранилище последних отправленных ID сообщений для предотвращения повторов
# (user_id, chat_id) -> deque(maxlen=100)
sent_history = {}

# Глобальные задачи для периодических операций
_cache_cleanup_task = None


async def sglypa_command(event: events.NewMessage.Event):
    """
    Обработчик команды .сглыпа
    Активирует/деактивирует режим сглыпы в текущем чате
    """
    global _cache_cleanup_task
    
    me = await event.client.get_me()
    user_id = me.id
    chat_id = event.chat_id
    key = (user_id, chat_id)
    
    if key in active_sglypa_tasks and not active_sglypa_tasks[key].done():
        # Деактивируем - просто отменяем задачу
        active_sglypa_tasks[key].cancel()
        del active_sglypa_tasks[key]
        if key in sent_history:
            del sent_history[key]
        await event.respond("❌ Режим сглыпы деактивирован")
        logger.info(f"[User {user_id}] Сглыпа остановлена в чате {chat_id}")
    else:
        await event.respond("✅ Сглыпа активирована!")
        
        # Инициализируем историю отправленных для этого чата
        sent_history[key] = deque(maxlen=100)
        
        # Парсим историю
        asyncio.create_task(_parse_chat_history(user_id, chat_id, event.client))
        
        if _cache_cleanup_task is None or _cache_cleanup_task.done():
            _cache_cleanup_task = asyncio.create_task(_periodic_cache_cleanup())
        
        # Запускаем цикл сглыпы
        task = asyncio.create_task(_sglypa_loop(user_id, chat_id, event.client))
        active_sglypa_tasks[key] = task
        user_manager.set_active(user_id, f"сглыпа_{chat_id}", task)


def _is_advertisement(text: str) -> bool:
    """Проверяет текст на наличие рекламы и стоп-слов"""
    if not text: return False
    text = text.lower()
    
    # Ссылки
    if 'http://' in text or 'https://' in text or 't.me/' in text or 'tg://' in text:
        return True
    if '@' in text and len(text.split()) < 3: # username как отдельное сообщение
        return True
        
    # Ключевые слова рекламы
    stop_words = [
        r'розыгрыш', r'\d+\s*место', r'подписка', r'спонсор', 
        r'за рекламу', r'набираю отзывы', r'отпиши лс', 
        r'неограничено', r'лучший чат', r'ссылки на сайт',
        r'1000\s*₽', r'500\s*₽', r'200\s*₽'
    ]
    
    for pattern in stop_words:
        if re.search(pattern, text):
            return True
            
    return False

def _should_skip_message(message) -> bool:
    """Проверяет, нужно ли пропустить сообщение"""
    if not message: 
        return True
    
    # 1. Стикеры
    if message.sticker:
        return True
    if hasattr(message, 'media') and isinstance(message.media, MessageMediaDocument):
        for attr in message.media.document.attributes:
            if isinstance(attr, DocumentAttributeSticker):
                return True
        # Проверка на .webm (анимированные стикеры)
        if message.file and message.file.name and message.file.name.endswith('.webm'):
            return True

    # 2. Текст
    if hasattr(message, 'text') and message.text:
        text = message.text.strip()
        # Пропускаем команды
        if text.startswith('.'):
            return True
        # Реклама и ссылки
        if _is_advertisement(text):
            return True
            
    return False


async def _parse_chat_history(user_id: int, chat_id: int, client):
    try:
        count = 0
        skipped = 0
        logger.info(f"[User {user_id}] Начинаю парсинг истории чата {chat_id}...")
        async for message in client.iter_messages(chat_id, limit=3000): # Уменьшил лимит для скорости
            if message.sender_id != user_id and not _should_skip_message(message):
                message_cache.add_message(user_id, chat_id, message)
                count += 1
            else:
                skipped += 1
            if count % 100 == 0:
                await asyncio.sleep(0.01)
        logger.info(f"[User {user_id}] Парсинг истории завершен: {count} msg")
    except Exception as e:
        logger.error(f"[User {user_id}] Ошибка парсинга: {e}")


async def _periodic_cache_cleanup():
    while True:
        try:
            await asyncio.sleep(600)
            from pathlib import Path
            import os
            temp_dir = Path("temp_media")
            if temp_dir.exists():
                for f in temp_dir.iterdir():
                    try: 
                        if f.is_file(): os.remove(f)
                    except Exception: pass
        except Exception:
            pass

def _generate_glitch_text(messages):
    """Генерирует склеенный текст из кеша"""
    if not messages: return None
    
    # Собираем все слова из сообщений
    all_words = []
    for m in messages:
        if m.text and not _is_advertisement(m.text):
            words = m.text.split()
            all_words.extend(words)
    
    if not all_words: return None
    
    # Определяем длину (шансы 33/33/33)
    r = random.random()
    if r < 0.33:
        length = random.randint(1, 2)
    elif r < 0.66:
        length = random.randint(3, 4)
    else:
        length = random.randint(5, 6)
        
    # Генерируем
    result_words = []
    for _ in range(length):
        if all_words:
            word = random.choice(all_words)
            result_words.append(word)
            
    return " ".join(result_words)


async def _sglypa_loop(user_id: int, chat_id: int, client):
    """
    Индивидуальный цикл сглыпы
    """
    key = (user_id, chat_id)
    last_msg_id = None
    last_send_time = time.time()
    
    try:
        logger.info(f"[User {user_id}] Сглыпа запущена для чата {chat_id}")
        while True:
            if user_manager.get_active_command(user_id) != f"сглыпа_{chat_id}":
                break
                
            last_message = message_cache.get_last_message(user_id, chat_id)
            current_time = time.time()
            should_send = False
            
            # Триггеры отправки
            if last_message and last_message.id != last_msg_id:
                last_msg_id = last_message.id
                if last_message.sender_id != user_id:
                    await asyncio.sleep(random.randint(2, 5)) # Случайная задержка
                    should_send = True
            elif current_time - last_send_time >= 15: # Реже шлем сами (15 сек)
                should_send = True
            
            if should_send:
                cache_deque = message_cache.cache.get(key)
                if not cache_deque:
                    await asyncio.sleep(1)
                    continue
                
                messages = list(cache_deque)
                # Выбираем режим: 35% склейка, 65% оригинал
                use_glitch = random.random() < 0.35
                
                if use_glitch:
                    # СКЛЕЙКА
                    text = _generate_glitch_text(messages)
                    if text:
                        try:
                            await client.send_message(chat_id, text)
                            last_send_time = time.time()
                            logger.debug(f"Sglypa glitch sent: {text}")
                        except Exception as e:
                            logger.error(f"Sglypa glitch error: {e}")
                else:
                    # ОРИГИНАЛ
                    valid = [
                        m for m in messages 
                        if m.sender_id != user_id 
                        and not _should_skip_message(m)
                    ]
                    if valid:
                        selected = random.choice(valid)
                        
                        # Обрезка текста до 11 слов
                        if hasattr(selected, 'text') and selected.text:
                            words = selected.text.split()
                            if len(words) > 11:
                                selected.text = " ".join(words[:11])
                        
                        try:
                            await _send_msg(client, chat_id, selected)
                            last_send_time = time.time()
                        except FloodWaitError as e:
                            await asyncio.sleep(e.seconds + 1)
                        except Exception as e:
                            logger.error(f"Sglypa send error: {e}")
            
            await asyncio.sleep(1)
            
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"Sglypa loop error: {e}")
    finally:
        if key in active_sglypa_tasks: del active_sglypa_tasks[key]
        if key in sent_history: del sent_history[key]


async def _send_msg(client, chat_id, message):
    try:
        # Медиа (кроме стикеров, они уже отфильтрованы)
        if hasattr(message, 'media') and message.media:
            from pathlib import Path
            import os
            temp_dir = Path("temp_media")
            temp_dir.mkdir(exist_ok=True)
            path = await client.download_media(message, file=temp_dir)
            if path:
                try:
                    # Если текст был обрезан, используем его как caption
                    caption = getattr(message, 'text', None)
                    await client.send_file(chat_id, path, caption=caption)
                finally:
                    # Всегда удаляем файл, даже если отправка упала
                    try:
                        os.remove(path)
                        logger.debug(f"Removed sglypa temp file: {path}")
                    except Exception as e:
                        logger.warning(f"Failed to remove sglypa temp file {path}: {e}")
                return
        
        if hasattr(message, 'text') and message.text:
            await client.send_message(chat_id, message.text)
    except Exception as e:
        logger.debug(f"Error in sglypa _send_msg: {e}")
