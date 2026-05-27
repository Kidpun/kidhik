"""
Модуль конфигурации бота
Экспортирует все необходимые настройки из settings.py
"""

from .settings import (
    # Базовые пути
    BASE_DIR,
    TEXT_DIR,
    TROLL_FILE,
    
    # Telegram API
    API_ID,
    API_HASH,
    BOT_TOKEN,
    SESSION_FILE,
    
    # Настройки устройства
    DEFAULT_DEVICE_MODEL,
    DEFAULT_SYSTEM_VERSION,
    DEFAULT_APP_VERSION,
    LANG_CODE,
    SYSTEM_LANG_CODE,
    
    # Фразы для команды .откат
    OTKAT_PHRASES,
    OTKAT_REPLY_CHANCE,
    
    # Spotify
    SPOTIFY_CLIENT_ID,
    SPOTIFY_CLIENT_SECRET,
    SPOTIFY_REDIRECT_URI,
    
    # Владелец бота
    OWNER_ID,
    
    # Google Gemini AI
    GEMINI_API_KEY,
    GEMINI_MODEL,
    GOOGLE_SEARCH_CX,
    
    # FunStat API
    FUNSTAT_TOKEN,
)

__all__ = [
    'BASE_DIR',
    'TEXT_DIR',
    'TROLL_FILE',
    'API_ID',
    'API_HASH',
    'BOT_TOKEN',
    'SESSION_FILE',
    'DEFAULT_DEVICE_MODEL',
    'DEFAULT_SYSTEM_VERSION',
    'DEFAULT_APP_VERSION',
    'LANG_CODE',
    'SYSTEM_LANG_CODE',
    'OTKAT_PHRASES',
    'OTKAT_REPLY_CHANCE',
    'SPOTIFY_CLIENT_ID',
    'SPOTIFY_CLIENT_SECRET',
    'SPOTIFY_REDIRECT_URI',
    'OWNER_ID',
    'GEMINI_API_KEY',
    'GEMINI_MODEL',
    'GOOGLE_SEARCH_CX',
    'FUNSTAT_TOKEN',
]
