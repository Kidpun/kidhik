"""
Команды для авторизации Яндекс Музыки
.yandex_auth - получить ссылку для авторизации
.yandex_token <токен> - ввести токен из callback
.yandex_logout - отключить Яндекс Музыку
"""
import logging
import re
from telethon import events

from utils.yandex_music import yandex_manager, YANDEX_MUSIC_AVAILABLE

logger = logging.getLogger(__name__)


async def yandex_auth_command(event: events.NewMessage.Event):
    """
    Обработчик команды .yandex_auth
    Показывает ссылку для авторизации
    """
    if not YANDEX_MUSIC_AVAILABLE:
        await event.respond(
            "❌ Библиотека yandex-music не установлена.\n"
            "Установите: <code>pip install yandex-music</code>",
            parse_mode='html'
        )
        return
    
    user_id = event.sender_id
    
    # Проверяем, не авторизован ли уже пользователь
    if yandex_manager.has_credentials(user_id):
        await event.respond(
            "✅ Вы уже авторизованы в Яндекс Музыке.\n"
            "Используйте команду <code>.музыка</code> для просмотра текущего трека.\n\n"
            "Для выхода: <code>.yandex_logout</code>",
            parse_mode='html'
        )
        return
    
    # Получаем URL для авторизации
    auth_url = yandex_manager.get_auth_url()
    
    await event.respond(
        "🟡 <b>Авторизация Яндекс Музыки</b>\n\n"
        "📋 <b>Инструкция:</b>\n"
        "1. Перейдите по ссылке ниже\n"
        "2. Войдите в свой аккаунт Яндекс\n"
        "3. Разрешите доступ приложению\n"
        "4. После перенаправления нажмите кнопку <b>\"Копировать\"</b> на странице\n"
        "5. Отправьте боту скопированную команду\n\n"
        "⚠️ <b>Если видите ошибку \"redirect_uri не совпадает\":</b>\n"
        "Убедитесь, что в настройках Яндекс OAuth приложения указан Callback URL:\n"
        "<code>https://kidwork.live/spotify/yandex_callback.html</code>\n\n"
        f"<a href=\"{auth_url}\">🔗 Перейти к авторизации</a>\n\n"
        f"Или скопируйте ссылку:\n<code>{auth_url}</code>",
        parse_mode='html'
    )


async def yandex_token_command(event: events.NewMessage.Event):
    """
    Обработчик команды .yandex_token <токен или URL>
    Сохраняет токен пользователя
    """
    if not YANDEX_MUSIC_AVAILABLE:
        await event.respond("❌ Библиотека yandex-music не установлена.")
        return
    
    user_id = event.sender_id
    text = event.message.text.strip()
    
    # Извлекаем токен
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        await event.respond(
            "❌ Использование: <code>.yandex_token &lt;токен или URL&gt;</code>",
            parse_mode='html'
        )
        return
    
    token_or_url = parts[1].strip()
    
    # Пробуем извлечь токен из URL
    token = None
    
    # Если это URL с access_token в hash (#access_token=...)
    if '#access_token=' in token_or_url:
        match = re.search(r'#access_token=([^&\s]+)', token_or_url)
        if match:
            token = match.group(1)
    # Если это URL с access_token в query (?access_token=...)
    elif 'access_token=' in token_or_url:
        match = re.search(r'access_token=([^&\s#]+)', token_or_url)
        if match:
            token = match.group(1)
    else:
        # Предполагаем, что это сам токен
        token = token_or_url
    
    if not token:
        await event.respond(
            "❌ Не удалось извлечь токен.\n"
            "Убедитесь, что вы скопировали полный URL из браузера."
        )
        return
    
    # Пробуем авторизоваться
    try:
        if yandex_manager.authorize_user(user_id, token):
            await event.respond(
                "✅ <b>Яндекс Музыка успешно подключена!</b>\n\n"
                "Теперь команда <code>.музыка</code> будет показывать треки из Яндекс Музыки.\n\n"
                "Для отключения: <code>.yandex_logout</code>",
                parse_mode='html'
            )
            logger.info(f"Yandex Music authorization successful for user {user_id}")
        else:
            await event.respond(
                "❌ Неверный токен.\n"
                "Попробуйте получить новую ссылку: <code>.yandex_auth</code>",
                parse_mode='html'
            )
    except Exception as e:
        logger.error(f"Yandex auth error for user {user_id}: {e}")
        error_msg = str(e).lower()
        if "invalid" in error_msg or "неверный" in error_msg:
            help_text = (
                "❌ <b>Неверный токен</b>\n\n"
                "Возможные причины:\n"
                "• Токен устарел или недействителен\n"
                "• Неправильно скопирован URL\n\n"
                "Попробуйте:\n"
                "1. Получить новую ссылку: <code>.yandex_auth</code>\n"
                "2. Убедитесь, что скопировали <b>весь URL</b> из браузера\n"
                "3. URL должен начинаться с <code>https://kidwork.live/spotify/yandex_callback.html#access_token=</code>"
            )
        else:
            help_text = (
                f"❌ <b>Ошибка авторизации:</b> {e}\n\n"
                "Попробуйте получить новую ссылку: <code>.yandex_auth</code>"
            )
        await event.respond(help_text, parse_mode='html')


async def yandex_logout_command(event: events.NewMessage.Event):
    """
    Обработчик команды .yandex_logout
    Отключает Яндекс Музыку
    """
    user_id = event.sender_id
    
    if yandex_manager.logout(user_id):
        await event.respond(
            "✅ Яндекс Музыка отключена.\n"
            "Для повторного подключения: <code>.yandex_auth</code>",
            parse_mode='html'
        )
        logger.info(f"Yandex Music logout for user {user_id}")
    else:
        await event.respond("ℹ️ Вы и так не авторизованы в Яндекс Музыке.")
