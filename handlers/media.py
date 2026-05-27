"""
Обработчики для сохранения медиа, удаленных и отредактированных сообщений
"""
import logging
import asyncio
from telethon import events
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument, DocumentAttributeVideo

from utils.media_saver import (
    save_self_destruct_photo, 
    save_deleted_message, 
    save_deleted_message_media,
    save_edited_message
)
from utils.message_cache import message_cache
from utils.ignore_list import ignore_manager
from utils.username_helper import get_user_username

logger = logging.getLogger(__name__)

async def media_handler(event: events.NewMessage.Event, client, user_id: int):
    """
    Обрабатывает медиа-сообщения (фото/видео/кружки/гс с 1 просмотром)
    """
    try:
        # 1. Проверяем игнор-лист (строго)
        chat_id = event.chat_id
        if chat_id and ignore_manager.is_ignored(user_id, chat_id):
            return
        
        # Если это сообщение от самого себя - обычно не сохраняем (мы и так видим)
        # Но если пользователь хочет тестить на себе? Оставим.
        
        if not event.message.media:
            return
        
        msg = event.message
        media = msg.media
        is_view_once = False
        
        # --- ЛОГИКА ОПРЕДЕЛЕНИЯ 1-VIEW / TTL ---
        
        # 1. Явный TTL на сообщении (API Layer 130+)
        if getattr(msg, 'ttl_seconds', None) and msg.ttl_seconds > 0:
            is_view_once = True
            
        # 2. TTL внутри медиа (старый способ или для фото)
        if not is_view_once and getattr(media, 'ttl_seconds', None) and media.ttl_seconds > 0:
            is_view_once = True
            
        # 3. Специфичные проверки для типов медиа
        if not is_view_once:
            if isinstance(media, MessageMediaPhoto):
                # Иногда has_spoiler + ttl_seconds
                if getattr(media, 'ttl_seconds', None): 
                    is_view_once = True
                    
            elif isinstance(media, MessageMediaDocument):
                doc = media.document
                if hasattr(doc, 'attributes'):
                    for attr in doc.attributes:
                        # Атрибут видео может содержать флаги
                        if isinstance(attr, DocumentAttributeVideo):
                            # Кружки (round_message) с TTL
                            if getattr(attr, 'round_message', False):
                                # Кружок считается 1-view если есть TTL на сообщении (уже проверено выше)
                                pass
                            # Обычные видео с таймером
                            # TTL для них обычно в msg.ttl_seconds
                            pass
                            
                        # Проверяем наличие поля ttl_seconds в любых атрибутах (если вдруг)
                        if getattr(attr, 'ttl_seconds', None) and attr.ttl_seconds is not None:
                            is_view_once = True

        if is_view_once:
            logger.info(f"📸 Detected View-Once Media from {event.sender_id} in {chat_id}")
            await save_self_destruct_photo(event, client, user_id)
            
    except Exception as e:
        logger.error(f"Media handler error: {e}")


async def deleted_message_handler(event: events.MessageDeleted.Event, client, user_id: int):
    """
    Обрабатывает удаленные сообщения.
    Включает батчинг (группировку) для массовых удалений.
    """
    try:
        deleted_ids = event.deleted_ids
        if not deleted_ids: return

        # Определяем chat_id (в ЛС event.chat_id может быть None для удалений)
        chat_id = getattr(event, 'chat_id', None)
        
        # Пытаемся восстановить chat_id из кеша, если его нет
        if not chat_id:
            for msg_id in deleted_ids:
                # Ищем во всем кеше пользователя
                # message_cache.by_id keys are (user_id, chat_id)
                for key in list(message_cache.by_id.keys()):
                    if key[0] == user_id and msg_id in message_cache.by_id[key]:
                        chat_id = key[1]
                        break
                if chat_id: break
        
        # Если так и не нашли chat_id, мы не можем проверить игнор и не знаем откуда сообщение.
        # Но попробуем обработать.
        
        if chat_id and ignore_manager.is_ignored(user_id, chat_id):
            return
        
        # --- БАТЧИНГ (Оптимизация массового удаления) ---
        is_batch = len(deleted_ids) > 3 # Если удалено более 3 сообщений сразу
        
        batch_lines = []
        
        for msg_id in deleted_ids:
            # Достаем из кеша
            cached_msg = message_cache.get_message(user_id, chat_id, msg_id) if chat_id else None
            
            # Если chat_id не был известен, ищем еще раз (для надежности)
            if not cached_msg and not chat_id:
                 for key, msgs in message_cache.by_id.items():
                    if key[0] == user_id and msg_id in msgs:
                        cached_msg = msgs[msg_id]
                        chat_id = key[1]
                        break
            
            # Если нашли chat_id только что - проверяем игнор
            if chat_id and ignore_manager.is_ignored(user_id, chat_id):
                            continue
            
            if not cached_msg: continue

            # Игнорируем свои удаления
            sender_id = cached_msg.sender_id or (cached_msg.from_id.user_id if cached_msg.from_id else None)
            if sender_id == user_id: continue

            text = getattr(cached_msg, 'text', "") or getattr(cached_msg, 'message', "")
            
            # Игнорируем команды
            if text and text.strip().startswith('.'): continue

            # МЕДИА: Сохраняем отдельно (батчинг для файлов сложен)
            if hasattr(cached_msg, 'media') and cached_msg.media:
                media_path, media_info = await save_deleted_message_media(chat_id or 0, msg_id, cached_msg, client)
                
                # Получаем инфо о чате/юзере для красивого лога
                sender_name = "User"
                chat_title = "Chat"
                try:
                    s = await cached_msg.get_sender()
                    if s: sender_name = getattr(s, 'first_name', "User")
                    c = await cached_msg.get_chat()
                    if c: chat_title = getattr(c, 'title', chat_title)
                except Exception: pass
                
                await save_deleted_message(
                    chat_id or 0, msg_id, text, media_info, media_path,
                    chat_title, sender_name, "", user_id, client=client
                )
                continue

            # ТЕКСТ: Добавляем в батч
            sender_name = "User"
            try:
                s = await cached_msg.get_sender()
                if s: sender_name = getattr(s, 'first_name', "User")
            except Exception: pass
            
            if is_batch:
                batch_lines.append(f"👤 <b>{sender_name}:</b> {text[:100]}") # Обрезаем длинные
            else:
                # Одиночное - полная обработка
                chat_title = "Chat"
                sender_username = ""
                try:
                    s = await cached_msg.get_sender()
                    if s: 
                        sender_name = getattr(s, 'first_name', "Unknown")
                        sender_username = await get_user_username(client, s) or ""
                    c = await cached_msg.get_chat()
                    if c: chat_title = getattr(c, 'title', chat_title)
                except Exception: pass
                
                await save_deleted_message(
                    chat_id or 0, msg_id, text, None, None,
                    chat_title, sender_name, sender_username, user_id, client=client
                )

        # Отправка батча текстов
        if batch_lines:
            header = f"🗑 <b>Массовое удаление ({len(batch_lines)} шт) в чате {chat_id}</b>\n\n"
            full_text = header + "\n".join(batch_lines)
            if len(full_text) > 4000: full_text = full_text[:4000] + "..."
            
            # Используем save_deleted_message для отправки (хак: передаем всё как текст одного сообщения)
            await save_deleted_message(
                chat_id or 0, 0, full_text, None, None,
                "Batch Log", "System", "", user_id, client=client
            )
            
    except Exception as e:
        logger.error(f"Deleted handler error: {e}")


async def edited_message_handler(event: events.MessageEdited.Event, client, user_id: int):
    """
    Обрабатывает отредактированные сообщения
    """
    try:
        # Свои правки игнорим
        if event.sender_id == user_id: return
            
        chat_id = event.chat_id
        if not chat_id and hasattr(event.message, 'chat_id'):
            chat_id = event.message.chat_id
        
        # Строгая проверка игнора
        if chat_id and ignore_manager.is_ignored(user_id, chat_id):
            return
        
        msg_id = event.id
        old_msg = message_cache.get_message(user_id, chat_id, msg_id)
        
        # Всегда обновляем кеш (даже если игнор, чтобы потом знать что было)
        # Но если игнор - мы вернулись выше. Значит тут не игнор.
        
        if not old_msg:
            message_cache.add_message(user_id, chat_id, event.message)
            return

        old_text = getattr(old_msg, 'text', "") or getattr(old_msg, 'message', "")
        new_text = event.text or ""

        if old_text == new_text:
            message_cache.add_message(user_id, chat_id, event.message)
            return

        if old_text.strip().startswith('.') or new_text.strip().startswith('.'):
            message_cache.add_message(user_id, chat_id, event.message)
            return

        sender_name = "Unknown"
        sender_username = ""
        chat_title = "Чат"

        try:
            sender = await event.get_sender()
            if sender:
                sender_name = getattr(sender, 'first_name', "Unknown")
                sender_username = await get_user_username(client, sender) or ""
            
            chat = await event.get_chat()
            if chat:
                chat_title = getattr(chat, 'title', chat_title)
        except Exception: pass

        await save_edited_message(
            chat_id, msg_id, old_text, new_text,
            chat_title, sender_name, sender_username, user_id, client=client
        )
        
        message_cache.add_message(user_id, chat_id, event.message)

    except Exception as e:
        logger.error(f"Edited handler error: {e}")
