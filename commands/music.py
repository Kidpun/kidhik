"""
Команда .музыка
Показывает текущий трек владельца бота из Spotify с обложкой альбома
Работает через userbot во всех чатах
"""
import logging
import aiohttp
import ssl
from io import BytesIO
from telethon import events

from utils.spotify import spotify_manager

logger = logging.getLogger(__name__)


async def music_command(event: events.NewMessage.Event):
    """
    Обработчик команды .музыка
    Показывает что слушает владелец бота (только Spotify)
    """
    from config import OWNER_ID
    
    user_id = event.sender_id
    
    # Логируем для отладки
    logger.info(f"🎵 .музыка command from user_id={user_id}")
    
    # Проверяем Spotify только у владельца
    has_spotify = spotify_manager.has_credentials(OWNER_ID)
    
    if not has_spotify:
        await event.respond(
            "❌ Владелец бота не подключил Spotify"
        )
        return
    
    # Получаем трек владельца
    try:
        spotify_track = await spotify_manager.get_current_track(OWNER_ID)
        if not spotify_track:
            await event.respond("🔇 Сейчас ничего не играет")
            return
        
        # Формируем текст в зависимости от того, кто запросил
        if user_id == OWNER_ID:
            text = f"🟢 <b>Spotify</b>\n🎵 {spotify_track['text']}"
        else:
            text = f"🎵 <b>Этот трек слушает владелец:</b>\n{spotify_track['text']}"
        
        # Если есть обложка, отправляем с фото
        if spotify_track.get("album_cover"):
            try:
                # Создаем SSL контекст
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                
                connector = aiohttp.TCPConnector(ssl=ssl_context)
                
                # Скачиваем обложку
                async with aiohttp.ClientSession(connector=connector) as session:
                    async with session.get(spotify_track["album_cover"]) as resp:
                        if resp.status == 200:
                            image_data = await resp.read()
                            image_file = BytesIO(image_data)
                            image_file.name = "album_cover.jpg"
                            await event.client.send_file(
                                event.chat_id,
                                image_file,
                                caption=text,
                                parse_mode='html'
                            )
                        else:
                            await event.respond(text, parse_mode='html')
            except Exception as e:
                logger.debug(f"Error downloading album cover: {e}")
                await event.respond(text, parse_mode='html')
        else:
            await event.respond(text, parse_mode='html')
    except Exception as e:
        logger.error(f"Error in music command: {e}")
        await event.respond("❌ Ошибка при получении трека")
