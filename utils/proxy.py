"""
Система прокси для KidHik Userbot
Поддерживает: SOCKS5, SOCKS4, HTTP
Формат PROXY_URL в .env:
    socks5://user:pass@host:port
    socks5://host:port
    http://host:port
"""
import logging
from urllib.parse import urlparse
from config import PROXY_URL

logger = logging.getLogger(__name__)


def get_proxy() -> dict | None:
    """
    Парсит PROXY_URL из .env и возвращает dict для Telethon/aiohttp.
    Возвращает None если прокси не задан.
    """
    if not PROXY_URL:
        return None

    try:
        parsed = urlparse(PROXY_URL)
        scheme = parsed.scheme.lower()

        # Маппинг схем → socks типы (для python-socks / telethon)
        scheme_map = {
            "socks5": 2,   # socks.SOCKS5
            "socks4": 1,   # socks.SOCKS4
            "http":   3,   # socks.HTTP
            "https":  3,
        }

        if scheme not in scheme_map:
            logger.warning(f"⚠️ Неизвестный тип прокси: {scheme}. Поддерживаются: socks5, socks4, http")
            return None

        proxy_type = scheme_map[scheme]
        host = parsed.hostname
        port = parsed.port or (1080 if "socks" in scheme else 8080)
        username = parsed.username or None
        password = parsed.password or None

        if not host or not port:
            logger.warning("⚠️ Некорректный PROXY_URL — не удалось получить host:port")
            return None

        # Формат для Telethon
        proxy = (proxy_type, host, port, True, username, password)
        logger.info(f"🌐 Прокси: {scheme}://{host}:{port}" + (f" (auth: {username})" if username else ""))
        return proxy

    except Exception as e:
        logger.error(f"❌ Ошибка парсинга PROXY_URL '{PROXY_URL}': {e}")
        return None


def get_aiohttp_proxy() -> str | None:
    """
    Возвращает прокси строку для aiohttp (используется в bot_manager/бот-запросах).
    """
    if not PROXY_URL:
        return None
    # aiohttp принимает строку вида 'http://host:port' или 'socks5://host:port'
    return PROXY_URL


def proxy_info() -> str:
    """Возвращает читаемую информацию о прокси для .помощь (без логина/пароля)"""
    if not PROXY_URL:
        return "❌ Прокси не настроен"
    try:
        parsed = urlparse(PROXY_URL)
        if not parsed.hostname:
            return "⚠️ Прокси задан, но URL некорректный"
        return f"✅ {parsed.scheme}://{parsed.hostname}:{parsed.port or '?'}"
    except Exception:
        return "⚠️ Прокси задан, но URL некорректный"
