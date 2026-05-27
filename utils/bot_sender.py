"""
Утилита для отправки сообщений через Telegram Bot API
Отправляет медиа с 1 просмотром и удаленные сообщения в ЛС пользователя
"""
import logging
import asyncio
import aiohttp
import ssl
from pathlib import Path
from typing import Optional
from io import BytesIO

from config import BOT_TOKEN, OWNER_ID

logger = logging.getLogger(__name__)


def get_bot_api_url() -> str:
    """Получает URL для Telegram Bot API"""
    if not BOT_TOKEN:
        return None
    return f"https://api.telegram.org/bot{BOT_TOKEN}"


async def send_to_user(user_id: int, text: str, photo_path: Path = None, document_path: Path = None, video_path: Path = None, voice_path: Path = None):
    """
    Отправляет сообщение пользователю через Bot API
    
    :param user_id: ID пользователя, которому отправляем
    :param text: Текст сообщения
    :param photo_path: Путь к фото
    :param document_path: Путь к документу
    :param video_path: Путь к видео
    :param voice_path: Путь к голосовому сообщению
    """
    if not BOT_TOKEN:
        logger.warning("BOT_TOKEN не установлен, отправка через бота невозможна")
        return
    
    bot_api_url = get_bot_api_url()
    if not bot_api_url:
        return
    
    # Создаем SSL контекст с отключенной проверкой сертификата
    # (для случаев с прокси или корпоративным файрволом)
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    
    # Увеличиваем таймауты для запросов
    timeout = aiohttp.ClientTimeout(total=30, connect=10)
    
    try:
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            if photo_path and photo_path.exists():
                url = f"{bot_api_url}/sendPhoto"
                data = aiohttp.FormData()
                data.add_field('chat_id', str(user_id))
                data.add_field('caption', text)
                data.add_field('parse_mode', 'HTML')
                # Читаем файл в память перед отправкой
                with open(photo_path, 'rb') as photo_file:
                    photo_data = photo_file.read()
                data.add_field('photo', BytesIO(photo_data), filename=photo_path.name, content_type='image/jpeg')
                async with session.post(url, data=data) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        logger.error(f"Ошибка отправки фото: {resp.status} - {error_text}")
                        
            elif video_path and video_path.exists():
                url = f"{bot_api_url}/sendVideo"
                data = aiohttp.FormData()
                data.add_field('chat_id', str(user_id))
                data.add_field('caption', text)
                data.add_field('parse_mode', 'HTML')
                # Читаем файл в память перед отправкой
                with open(video_path, 'rb') as video_file:
                    video_data = video_file.read()
                data.add_field('video', BytesIO(video_data), filename=video_path.name, content_type='video/mp4')
                async with session.post(url, data=data) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        logger.error(f"Ошибка отправки видео: {resp.status} - {error_text}")
                        
            elif voice_path and voice_path.exists():
                url = f"{bot_api_url}/sendVoice"
                data = aiohttp.FormData()
                data.add_field('chat_id', str(user_id))
                data.add_field('caption', text)
                data.add_field('parse_mode', 'HTML')
                # Читаем файл в память перед отправкой
                with open(voice_path, 'rb') as voice_file:
                    voice_data = voice_file.read()
                data.add_field('voice', BytesIO(voice_data), filename=voice_path.name, content_type='audio/ogg')
                async with session.post(url, data=data) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        logger.error(f"Ошибка отправки голосового: {resp.status} - {error_text}")
                        
            elif document_path and document_path.exists():
                url = f"{bot_api_url}/sendDocument"
                data = aiohttp.FormData()
                data.add_field('chat_id', str(user_id))
                data.add_field('caption', text)
                data.add_field('parse_mode', 'HTML')
                # Читаем файл в память перед отправкой
                with open(document_path, 'rb') as doc_file:
                    doc_data = doc_file.read()
                data.add_field('document', BytesIO(doc_data), filename=document_path.name)
                async with session.post(url, data=data) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        logger.error(f"Ошибка отправки документа: {resp.status} - {error_text}")
            else:
                url = f"{bot_api_url}/sendMessage"
                payload = {
                    'chat_id': str(user_id), # Передаем как строку для безопасности (int64 issue)
                    'text': text,
                    'parse_mode': 'HTML'
                }
                async with session.post(url, json=payload) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        try:
                            result = await resp.json()
                            if result.get('error_code') == 403:
                                logger.warning(f"Бот заблокирован пользователем {user_id}")
                            elif result.get('error_code') == 400:
                                logger.warning(f"Чат с пользователем {user_id} не найден")
                            else:
                                logger.error(f"Ошибка отправки сообщения: {resp.status} - {error_text}")
                        except:
                            logger.error(f"Ошибка отправки сообщения: {resp.status} - {error_text}")
        
    except asyncio.TimeoutError:
        # Таймауты - это нормально, не логируем
        pass
    except aiohttp.ClientError as e:
        # Ошибки подключения - логируем только критичные
        error_str = str(e).lower()
        if "connection" not in error_str or "timeout" not in error_str:
            logger.error(f"Ошибка подключения при отправке сообщения пользователю {user_id}: {e}")
    except Exception as e:
        # Проверяем, является ли это исключением таймаута
        error_str = str(e)
        if "timeout" in error_str.lower() or "Connection timeout" in error_str:
            # Таймауты - это нормально, не логируем
            pass
        else:
            logger.error(f"Ошибка при отправке сообщения через бота: {e}", exc_info=True)


async def send_self_destruct_media(user_id: int, media_path: Path, chat_title: str, sender_name: str, sender_username: str, media_type: str = "photo", chat_type: str = "чат", chat_id: int = None):
    """
    Отправляет медиа с 1 просмотром в ЛС пользователя
    """
    text = f"📸 <b>Медиа с 1 просмотром</b>\n\n"
    text += f"💬 <b>Чат:</b> {chat_title}\n"
    if chat_id is not None:
        text += f"🆔 <b>ID {chat_type}:</b> <code>{chat_id}</code>\n"
    text += f"👤 <b>Отправитель:</b> {sender_name}"
    if sender_username:
        text += f" (@{sender_username})"
    text += f"\n📎 <b>Тип:</b> {media_type}"
    
    # Добавляем подпись с командой .игнор
    if chat_id is not None:
        text += f"\n\n💡 <i>Если хотите отключить уведомления от этого {chat_type}, пропишите:</i>\n"
        text += f"<code>.игнор {chat_id}</code>"
    
    # Определяем тип медиа по расширению
    ext = media_path.suffix.lower()
    
    if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
        await send_to_user(user_id, text, photo_path=media_path)
    elif ext in ['.mp4', '.mov', '.avi', '.mkv']:
        await send_to_user(user_id, text, video_path=media_path)
    elif ext in ['.ogg', '.oga', '.m4a', '.mp3']:
        await send_to_user(user_id, text, voice_path=media_path)
    else:
        await send_to_user(user_id, text, document_path=media_path)


async def send_deleted_message(user_id: int, chat_title: str, sender_name: str, sender_username: str, 
                               message_text: str, media_path: Path = None, media_type: str = None):
    """
    Отправляет информацию об удаленном сообщении в ЛС пользователя
    """
    text = f"🗑️ <b>Удаленное сообщение</b>\n\n"
    text += f"💬 <b>Чат:</b> {chat_title}\n"
    text += f"👤 <b>Пользователь:</b> {sender_name}"
    if sender_username:
        text += f" (@{sender_username})"
    text += f"\n\n"
    
    if message_text:
        text += f"💬 <b>Сообщение:</b>\n{message_text}\n\n"
    
    if media_type:
        text += f"📎 <b>Медиа:</b> {media_type}"
    
    if media_path and media_path.exists():
        # Определяем тип медиа по расширению
        ext = media_path.suffix.lower()
        
        if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
            await send_to_user(user_id, text, photo_path=media_path)
        elif ext in ['.mp4', '.mov', '.avi', '.mkv']:
            await send_to_user(user_id, text, video_path=media_path)
        elif ext in ['.ogg', '.oga', '.m4a', '.mp3']:
            await send_to_user(user_id, text, voice_path=media_path)
        else:
            await send_to_user(user_id, text, document_path=media_path)
    else:
        await send_to_user(user_id, text)

