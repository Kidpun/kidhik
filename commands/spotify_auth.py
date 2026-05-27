"""
Команды для авторизации Spotify
.spotify_auth - получить ссылку для авторизации
.spotify_code <код> - ввести код авторизации
.spotify_logout - отключить Spotify
"""
import logging
import re
from telethon import events

from utils.spotify import spotify_manager

logger = logging.getLogger(__name__)


async def spotify_auth_command(event: events.NewMessage.Event):
    """
    Обработчик команды .spotify_auth
    Показывает ссылку для авторизации Spotify
    """
    user_id = event.sender_id
    
    # Проверяем, настроены ли credentials
    if not spotify_manager.client_id or not spotify_manager.client_secret:
        await event.respond(
            "❌ Spotify API не настроен.\n"
            "Обратитесь к администратору."
        )
        return
    
    # Проверяем, не авторизован ли уже пользователь
    if spotify_manager.has_credentials(user_id):
        await event.respond(
            "✅ Вы уже авторизованы в Spotify.\n"
            "Используйте команду .музыка для просмотра текущего трека.\n\n"
            "Для выхода: .spotify_logout"
        )
        return
    
    # Получаем URL для авторизации
    auth_url = spotify_manager.get_auth_url()
    
    if not auth_url:
        await event.respond(
            "❌ Ошибка при генерации ссылки авторизации."
        )
        return
    
    await event.respond(
        "🔗 <b>Авторизация Spotify</b>\n\n"
        "📋 <b>Инструкция:</b>\n"
        "1. Перейдите по ссылке ниже\n"
        "2. Войдите в свой аккаунт Spotify\n"
        "3. Разрешите доступ приложению\n"
        "4. После перенаправления вы увидите страницу с ошибкой (это нормально!)\n"
        "5. <b>ВАЖНО:</b> Скопируйте <b>весь URL</b> из адресной строки браузера\n"
        "   URL будет вида: <code>https://example.com/callback?code=AQB123...</code>\n"
        "6. Отправьте команду: <code>.spotify_code &lt;скопированный_URL&gt;</code>\n\n"
        "💡 <b>Совет:</b> Даже если страница не загружается, URL в адресной строке содержит нужный код!\n\n"
        f"<a href=\"{auth_url}\">🔗 Перейти к авторизации</a>\n\n"
        f"Или скопируйте ссылку:\n<code>{auth_url}</code>",
        parse_mode='html'
    )


async def spotify_code_command(event: events.NewMessage.Event):
    """
    Обработчик команды .spotify_code <код или URL>
    Завершает авторизацию Spotify
    """
    user_id = event.sender_id
    text = event.message.text.strip()
    
    # Извлекаем код из команды
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        await event.respond(
            "❌ Использование: <code>.spotify_code &lt;код или URL&gt;</code>\n\n"
            "Скопируйте полный URL из браузера после авторизации.",
            parse_mode='html'
        )
        return
    
    code_or_url = parts[1].strip()
    
    # Пробуем извлечь код из URL
    code = None
    if 'code=' in code_or_url:
        # Извлекаем код из URL
        match = re.search(r'code=([^&\s]+)', code_or_url)
        if match:
            code = match.group(1)
    else:
        # Предполагаем, что это сам код
        code = code_or_url
    
    if not code:
        await event.respond(
            "❌ Не удалось извлечь код авторизации.\n"
            "Убедитесь, что вы скопировали полный URL из браузера."
        )
        return
    
    try:
        # Пробуем авторизоваться
        success = spotify_manager.authorize_user(user_id, code)
        
        if success:
            await event.respond(
                "✅ <b>Spotify успешно подключен!</b>\n\n"
                "Теперь вы можете использовать команду <code>.музыка</code> "
                "для отображения текущего трека.\n\n"
                "Для отключения: <code>.spotify_logout</code>",
                parse_mode='html'
            )
            logger.info(f"Spotify authorization successful for user {user_id}")
        else:
            await event.respond(
                "❌ Не удалось авторизоваться в Spotify.\n"
                "Попробуйте получить новую ссылку: <code>.spotify_auth</code>",
                parse_mode='html'
            )
            
    except Exception as e:
        logger.error(f"Spotify auth error for user {user_id}: {e}")
        await event.respond(
            f"❌ Ошибка авторизации: {e}\n\n"
            "Попробуйте получить новую ссылку: <code>.spotify_auth</code>",
            parse_mode='html'
        )


async def spotify_logout_command(event: events.NewMessage.Event):
    """
    Обработчик команды .spotify_logout
    Отключает Spotify API
    """
    user_id = event.sender_id
    
    if spotify_manager.logout(user_id):
        await event.respond(
            "✅ Spotify успешно отключен.\n"
            "Токены удалены. Для повторного подключения: <code>.spotify_auth</code>",
            parse_mode='html'
        )
        logger.info(f"Spotify logout for user {user_id}")
    else:
        await event.respond("ℹ️ Вы и так не авторизованы в Spotify.")
