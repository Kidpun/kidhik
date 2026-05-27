"""
Команда .dl <ссылка>
Скачивание видео через yt-dlp (TikTok, Shorts, Reels)
"""
import logging
import os
import asyncio
from telethon import events
try:
    import yt_dlp
    DL_AVAILABLE = True
except ImportError:
    DL_AVAILABLE = False

logger = logging.getLogger(__name__)

# Прокси для обхода блокировок (можно настроить через переменную окружения)
PROXY = os.getenv('PROXY', None)  # Например: socks5://127.0.0.1:1080

def get_ytdlp_version():
    """Получает версию yt-dlp"""
    try:
        import yt_dlp
        return yt_dlp.version.__version__
    except:
        return None

async def download_command(event: events.NewMessage.Event):
    """
    .dl <url> - Скачать видео
    """
    if not DL_AVAILABLE:
        await event.edit("❌ yt-dlp не установлен.\n`pip install yt-dlp`")
        return

    url = None
    args = event.message.text.split()
    if len(args) > 1:
        url = args[1]
    
    # Проверяем реплай
    if not url:
        reply = await event.get_reply_message()
        if reply and reply.text:
            url = reply.text.strip()
            
    if not url or "http" not in url:
        await event.edit("❌ Укажите ссылку!")
        return
        
    await event.edit(f"⬇️ Скачиваю...\n`{url}`")
    
    filename = f"temp_media/dl_{event.id}.mp4"
    
    # Определяем, нужен ли прокси (для TikTok и других заблокированных сервисов)
    is_tiktok = 'tiktok.com' in url or 'vm.tiktok.com' in url or 'douyin.com' in url
    
    # Для TikTok используем мобильный User-Agent и другие методы обхода
    if is_tiktok:
        # Мобильный User-Agent часто работает лучше для TikTok
        mobile_ua = 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1'
        ydl_opts = {
            'format': 'best[ext=mp4]/best',
            'outtmpl': filename,
            'quiet': True,
            'no_warnings': True,
            'max_filesize': 50 * 1024 * 1024,
            # Мобильный User-Agent для обхода блокировок
            'user_agent': mobile_ua,
            'referer': 'https://www.tiktok.com/',
            'http_headers': {
                'User-Agent': mobile_ua,
                'Referer': 'https://www.tiktok.com/',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Origin': 'https://www.tiktok.com',
            },
            'extractor_args': {
                'tiktok': {
                    'webpage_download_timeout': 60,
                }
            },
        }
        
        # Добавляем прокси, если указан
        if PROXY:
            ydl_opts['proxy'] = PROXY
            logger.info(f"Using proxy for TikTok: {PROXY}")
        else:
            logger.info("TikTok detected, trying without proxy (mobile UA)")
    else:
        # Для других сервисов используем стандартные настройки
        ydl_opts = {
            'format': 'best[ext=mp4]/best',
            'outtmpl': filename,
            'quiet': True,
            'no_warnings': True,
            'max_filesize': 50 * 1024 * 1024,
        }
    
    try:
        # Запускаем в executor (блокирует поток)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: _download(url, ydl_opts))
        
        if os.path.exists(filename):
            try:
                await event.edit("⬆️ Загружаю...")
                await event.client.send_file(event.chat_id, filename, caption=f"📹 Скачано via KidHik", reply_to=event.reply_to_msg_id)
                await event.delete()
            finally:
                # Всегда удаляем файл, даже если отправка упала
                try:
                    os.remove(filename)
                    logger.debug(f"Removed temp file: {filename}")
                except Exception as e:
                    logger.warning(f"Failed to remove temp file {filename}: {e}")
        else:
            # Если TikTok и первая попытка не удалась, пробуем альтернативные методы
            if is_tiktok:
                await event.edit("🔄 Пробую альтернативный метод...")
                # Пробуем с десктопным User-Agent
                ydl_opts_alt = {
                    'format': 'best[ext=mp4]/best',
                    'outtmpl': filename,
                    'quiet': True,
                    'no_warnings': True,
                    'max_filesize': 50 * 1024 * 1024,
                    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'referer': 'https://www.tiktok.com/',
                    'http_headers': {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                        'Referer': 'https://www.tiktok.com/',
                    },
                    'extractor_args': {
                        'tiktok': {
                            'webpage_download_timeout': 90,
                        }
                    },
                }
                if PROXY:
                    ydl_opts_alt['proxy'] = PROXY
                try:
                    await loop.run_in_executor(None, lambda: _download(url, ydl_opts_alt))
                    if os.path.exists(filename):
                        try:
                            await event.edit("⬆️ Загружаю...")
                            await event.client.send_file(event.chat_id, filename, caption=f"📹 Скачано via KidHik", reply_to=event.reply_to_msg_id)
                            await event.delete()
                        finally:
                            try:
                                os.remove(filename)
                                logger.debug(f"Removed temp file: {filename}")
                            except Exception as e:
                                logger.warning(f"Failed to remove temp file {filename}: {e}")
                        return
                except Exception as e2:
                    logger.error(f"Alternative download method failed: {e2}")
                    # Удаляем файл если он был скачан
                    if os.path.exists(filename):
                        try:
                            os.remove(filename)
                        except:
                            pass
            
            error_msg = "❌ Ошибка скачивания (файл не найден)."
            if is_tiktok:
                error_msg = "❌ <b>Не удалось скачать TikTok видео</b>\n\n"
                error_msg += "💡 <b>Возможные причины:</b>\n"
                error_msg += "• IP адрес заблокирован TikTok\n"
                error_msg += "• Видео недоступно или удалено\n"
                error_msg += "• Проблемы с сетью\n\n"
                error_msg += "💡 <b>Решения:</b>\n"
                error_msg += "• Используйте VPN/прокси на сервере\n"
                error_msg += "• Настройте прокси: <code>export PROXY=socks5://127.0.0.1:1080</code>\n"
                error_msg += "• Попробуйте другую ссылку"
            await event.edit(error_msg, parse_mode='html')
            
    except Exception as e:
        logger.error(f"Download error: {e}", exc_info=True)
        error_str = str(e).lower()
        error_msg = ""
        
        # Более понятные сообщения об ошибках
        if 'unable to extract' in error_str or 'extract webpage video data' in error_str:
            ytdlp_version = get_ytdlp_version()
            if is_tiktok:
                error_msg = "❌ <b>Ошибка извлечения данных TikTok</b>\n\n"
                error_msg += "TikTok изменил формат страницы или заблокировал доступ.\n\n"
                if ytdlp_version:
                    error_msg += f"📦 Текущая версия yt-dlp: <code>{ytdlp_version}</code>\n\n"
                error_msg += "💡 <b>Возможные решения:</b>\n"
                error_msg += "• Обновите yt-dlp: <code>pip install -U yt-dlp</code>\n"
                error_msg += "• Используйте VPN/прокси (настройте PROXY)\n"
                error_msg += "• Попробуйте другую ссылку\n"
                error_msg += "• Подождите и попробуйте позже"
            else:
                error_msg = "❌ <b>Не удалось извлечь данные видео</b>\n\n"
                error_msg += "Сервис может быть недоступен или изменил формат.\n"
                if ytdlp_version:
                    error_msg += f"\n📦 Текущая версия yt-dlp: <code>{ytdlp_version}</code>\n"
                error_msg += "\nПопробуйте обновить: <code>pip install -U yt-dlp</code>"
        elif 'ip address is blocked' in error_str or 'blocked' in error_str:
            error_msg = "❌ <b>IP адрес заблокирован</b>\n\n"
            error_msg += "TikTok заблокировал доступ с вашего IP.\n"
            error_msg += "💡 <b>Решение:</b> Настройте прокси через переменную окружения:\n"
            error_msg += "<code>export PROXY=socks5://127.0.0.1:1080</code>\n\n"
            error_msg += "Или используйте VPN/прокси на сервере."
        elif 'unavailable' in error_str or 'not available' in error_str:
            error_msg = "❌ Видео недоступно или удалено."
        elif 'private' in error_str:
            error_msg = "❌ Видео приватное или недоступно."
        elif 'sign in' in error_str or 'login' in error_str:
            error_msg = "❌ <b>Требуется авторизация</b>\n\nВидео доступно только для зарегистрированных пользователей."
        elif 'age-restricted' in error_str or 'age restriction' in error_str:
            error_msg = "❌ Видео с возрастными ограничениями."
        else:
            # Общая ошибка, но более понятная
            error_msg = f"❌ <b>Ошибка скачивания</b>\n\n<code>{str(e)[:200]}</code>"
            if is_tiktok:
                error_msg += "\n\n💡 <b>Совет:</b> TikTok может быть заблокирован. Попробуйте использовать прокси."
        
        await event.edit(error_msg, parse_mode='html')
        
        # Cleanup: Удаляем файл если он остался после ошибки
        if os.path.exists(filename): 
            try:
                os.remove(filename)
                logger.debug(f"Cleaned up temp file after error: {filename}")
            except Exception as cleanup_err:
                logger.warning(f"Failed to cleanup temp file {filename}: {cleanup_err}")

def _download(url, opts):
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])


