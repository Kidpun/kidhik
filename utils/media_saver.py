"""
Утилита для сохранения медиа, удаленных и отредактированных сообщений
"""
import os
import logging
from pathlib import Path
from datetime import datetime
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument, DocumentAttributeVideo

from utils.bot_sender import send_self_destruct_media, send_deleted_message, send_to_user

logger = logging.getLogger(__name__)

# Папки для сохранения
BASE_DIR = Path(__file__).parent.parent
SAVED_MEDIA_DIR = BASE_DIR / "saved_media"
DELETED_MESSAGES_DIR = BASE_DIR / "deleted_messages"

# Создаём папки если их нет
SAVED_MEDIA_DIR.mkdir(exist_ok=True)
DELETED_MESSAGES_DIR.mkdir(exist_ok=True)


async def save_self_destruct_photo(event, client, user_id: int):
    """
    Сохраняет фото/видео/кружок/гс с 1 просмотром
    """
    try:
        if not event.message.media:
            return
        
        # Получаем информацию о чате
        try:
            chat = await event.get_chat()
            chat_title = getattr(chat, 'title', None) or getattr(chat, 'first_name', None) or 'Чат'
        except:
            chat_title = "Чат"
        
        # Получаем информацию об отправителе
        try:
            sender = await event.get_sender()
            sender_name = getattr(sender, 'first_name', 'Unknown')
            from utils.username_helper import get_user_username
            sender_username = await get_user_username(client, sender)
        except:
            sender_name = "User"
            sender_username = None
        
        # Определяем тип медиа и расширение
        media_type = "медиа"
        ext = '.jpg'
        
        if isinstance(event.message.media, MessageMediaPhoto):
            media_type = "Фото"
            ext = '.jpg'
        elif isinstance(event.message.media, MessageMediaDocument):
            doc = event.message.media.document
            mime_type = getattr(doc, 'mime_type', '')
            
            is_round = False
            is_voice = False
            
            if hasattr(doc, 'attributes'):
                for attr in doc.attributes:
                    attr_name = type(attr).__name__
                    
                    # Проверяем через isinstance для более точного определения кружков
                    if isinstance(attr, DocumentAttributeVideo):
                        if hasattr(attr, 'round_message') and attr.round_message:
                            is_round = True
                    
                    # Альтернативная проверка по имени класса (на случай если isinstance не работает)
                    if 'Round' in attr_name or 'VideoRound' in attr_name:
                        is_round = True
                    
                    if 'Voice' in attr_name or 'Audio' in attr_name:
                        is_voice = True
            
            if is_round:
                media_type = "Кружок"
                ext = '.mp4'
            elif is_voice or 'audio' in mime_type or 'voice' in mime_type:
                media_type = "Голосовое сообщение"
                ext = '.ogg'
            elif 'video' in mime_type:
                media_type = "Видео"
                ext = '.mp4'
            else:
                media_type = "Документ"
                ext = '.file'
        
        # Создаём имя файла
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"user_{user_id}_{timestamp}{ext}"
        filepath = SAVED_MEDIA_DIR / filename
        
        # Скачиваем медиа
        await client.download_media(event.message, file=filepath)
        
        # Получаем chat_id из события
        chat_id = event.chat_id
        
        # Определяем тип чата и его ID
        chat_type = "чат"
        chat_id_display = chat_id
        
        try:
            chat_entity = await event.get_chat()
            from telethon.tl.types import User, Channel, Chat
            
            if isinstance(chat_entity, User):
                # Проверяем, является ли это ботом
                if getattr(chat_entity, 'bot', False):
                    chat_type = "бот"
                else:
                    chat_type = "пользователь"
                chat_id_display = chat_entity.id
            elif isinstance(chat_entity, Channel):
                if getattr(chat_entity, 'megagroup', False):
                    chat_type = "группа"
                else:
                    chat_type = "канал"
                chat_id_display = chat_entity.id
            elif isinstance(chat_entity, Chat):
                chat_type = "группа"
                chat_id_display = chat_entity.id
        except Exception as e:
            logger.debug(f"Error getting chat entity for self-destruct media: {e}")
            chat_id_display = chat_id
        
        # Отправляем в ЛС через бота с улучшенным текстом
        await send_self_destruct_media(
            user_id, filepath, chat_title, sender_name, sender_username, media_type,
            chat_type=chat_type, chat_id=chat_id_display
        )
            
    except Exception as e:
        logger.error(f"Ошибка при сохранении медиа для {user_id}: {e}")


async def save_deleted_message_media(chat_id, message_id, message, client):
    """
    Скачивает медиа из удаленного сообщения
    """
    try:
        if not message or not message.media:
            return None, None
        
        temp_dir = Path("temp_media")
        temp_dir.mkdir(exist_ok=True)
        
        media_type = "медиа"
        ext = '.file'
        
        if isinstance(message.media, MessageMediaPhoto):
            ext = '.jpg'
            media_type = 'Фото'
        elif isinstance(message.media, MessageMediaDocument):
            doc = message.media.document
            mime_type = getattr(doc, 'mime_type', '')
            
            # Проверяем, является ли это кружком
            is_round = False
            if hasattr(doc, 'attributes'):
                for attr in doc.attributes:
                    if isinstance(attr, DocumentAttributeVideo):
                        if hasattr(attr, 'round_message') and attr.round_message:
                            is_round = True
                    attr_name = type(attr).__name__
                    if 'Round' in attr_name or 'VideoRound' in attr_name:
                        is_round = True
            
            if is_round:
                media_type = 'Кружок'
                ext = '.mp4'
            elif 'video' in mime_type:
                media_type = 'Видео'
                ext = '.mp4'
            elif 'audio' in mime_type or 'voice' in mime_type:
                media_type = 'Аудио'
                ext = '.ogg'
            else:
                media_type = 'Документ'
                ext = '.file'
        
        filepath = temp_dir / f"del_{message_id}{ext}"
        await client.download_media(message, file=filepath)
        
        return str(filepath), media_type
    except Exception as e:
        logger.debug(f"Error saving deleted media: {e}")
        return None, None


async def save_deleted_message(chat_id, message_id, text, media_info=None, media_path=None, 
                              chat_title=None, sender_name=None, sender_username=None, user_id: int = None, client=None):
    """
    Отправляет отчет об удаленном сообщении
    """
    try:
        if not user_id:
            return

        chat_title = chat_title or "Чат"
        sender_name = sender_name or "Unknown"
        
        # Определяем тип чата и его ID
        chat_type = "чат"
        chat_id_display = chat_id
        
        if client:
            try:
                chat_entity = await client.get_entity(chat_id)
                from telethon.tl.types import User, Channel, Chat
                
                if isinstance(chat_entity, User):
                    # Проверяем, является ли это ботом
                    if getattr(chat_entity, 'bot', False):
                        chat_type = "бот"
                    else:
                        chat_type = "пользователь"
                    chat_id_display = chat_entity.id
                elif isinstance(chat_entity, Channel):
                    if getattr(chat_entity, 'megagroup', False):
                        chat_type = "группа"
                    else:
                        chat_type = "канал"
                    chat_id_display = chat_entity.id
                elif isinstance(chat_entity, Chat):
                    chat_type = "группа"
                    chat_id_display = chat_entity.id
            except Exception as e:
                logger.debug(f"Error getting chat entity for deleted message: {e}")
                chat_id_display = chat_id
        
        # Формируем текст с ID
        text_with_id = f"🗑️ <b>Удаленное сообщение</b>\n\n"
        text_with_id += f"💬 <b>Чат:</b> {chat_title}\n"
        text_with_id += f"🆔 <b>ID {chat_type}:</b> <code>{chat_id_display}</code>\n"
        text_with_id += f"👤 <b>Пользователь:</b> {sender_name}"
        if sender_username:
            text_with_id += f" (@{sender_username})"
        text_with_id += f"\n\n"
        
        if text:
            text_with_id += f"💬 <b>Сообщение:</b>\n{text}\n\n"
        
        if media_info:
            text_with_id += f"📎 <b>Медиа:</b> {media_info}\n\n"
        
        # Добавляем подпись с командой .игнор
        text_with_id += f"💡 <i>Если хотите отключить уведомления от этого {chat_type}, пропишите:</i>\n"
        text_with_id += f"<code>.игнор {chat_id_display}</code>"
        
        # Отправляем в ЛС через бота
        media_filepath = Path(media_path) if media_path else None
        # Используем готовый текст вместо отдельных параметров
        if media_filepath and media_filepath.exists():
            # Определяем тип медиа по расширению
            ext = media_filepath.suffix.lower()
            
            if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                await send_to_user(user_id, text_with_id, photo_path=media_filepath)
            elif ext in ['.mp4', '.mov', '.avi', '.mkv']:
                await send_to_user(user_id, text_with_id, video_path=media_filepath)
            elif ext in ['.ogg', '.oga', '.m4a', '.mp3']:
                await send_to_user(user_id, text_with_id, voice_path=media_filepath)
            else:
                await send_to_user(user_id, text_with_id, document_path=media_filepath)
        else:
            await send_to_user(user_id, text_with_id)
            
        if media_path and os.path.exists(media_path):
            try: os.remove(media_path)
            except: pass
        
    except Exception as e:
        error_msg = str(e)
        # Проверяем, является ли это ошибкой обработки исключений Python 3.10+
        if "catching classes that do not inherit from BaseException" in error_msg:
            logger.error(f"Ошибка при сохранении удаленного сообщения: ошибка обработки исключений (возможно, проблема в aiohttp). Полная ошибка: {e}", exc_info=True)
        else:
            logger.error(f"Ошибка при сохранении удаленного сообщения: {e}", exc_info=True)


async def save_edited_message(chat_id, message_id, old_text, new_text,
                              chat_title, sender_name, sender_username, user_id, client=None):
    """
    Отправляет отчет об изменении сообщения
    """
    try:
        if not user_id:
            return

        chat_title = chat_title or "Чат"
        sender_name = sender_name or "Unknown"
        
        # Определяем тип чата и его ID
        chat_type = "чат"
        chat_id_display = chat_id
        
        if client:
            try:
                chat_entity = await client.get_entity(chat_id)
                from telethon.tl.types import User, Channel, Chat
                
                if isinstance(chat_entity, User):
                    # Проверяем, является ли это ботом
                    if getattr(chat_entity, 'bot', False):
                        chat_type = "бот"
                    else:
                        chat_type = "пользователь"
                    chat_id_display = chat_entity.id
                elif isinstance(chat_entity, Channel):
                    if getattr(chat_entity, 'megagroup', False):
                        chat_type = "группа"
                    else:
                        chat_type = "канал"
                    chat_id_display = chat_entity.id
                elif isinstance(chat_entity, Chat):
                    chat_type = "группа"
                    chat_id_display = chat_entity.id
            except Exception as e:
                logger.debug(f"Error getting chat entity for edited message: {e}")
                chat_id_display = chat_id
        
        text = f"📝 <b>Измененное сообщение</b>\n\n"
        text += f"💬 <b>Чат:</b> {chat_title}\n"
        text += f"🆔 <b>ID {chat_type}:</b> <code>{chat_id_display}</code>\n"
        text += f"👤 <b>Автор:</b> {sender_name}"
        if sender_username:
            text += f" (@{sender_username})"
        text += f"\n\n"
        text += f"❌ <b>Было:</b>\n{old_text}\n\n"
        text += f"✅ <b>Стало:</b>\n{new_text}\n\n"
        
        # Добавляем подпись с командой .игнор
        text += f"💡 <i>Если хотите отключить уведомления от этого {chat_type}, пропишите:</i>\n"
        text += f"<code>.игнор {chat_id_display}</code>"

        await send_to_user(user_id, text)
        
    except Exception as e:
        logger.error(f"Ошибка при отправке измененного сообщения: {e}")
