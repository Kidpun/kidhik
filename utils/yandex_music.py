"""
Менеджер Яндекс Музыки
Управляет токенами пользователей и получением текущего трека
"""
import os
import json
import logging
from typing import Optional, Dict
from pathlib import Path

logger = logging.getLogger(__name__)

# Пробуем импортировать yandex_music
try:
    from yandex_music import Client
    YANDEX_MUSIC_AVAILABLE = True
except ImportError:
    YANDEX_MUSIC_AVAILABLE = False
    logger.warning("yandex-music не установлен. Команда Яндекс Музыки недоступна.")


class YandexMusicManager:
    """
    Управляет Яндекс Музыкой для пользователей
    """
    
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.tokens_file = self.base_dir / "data" / "yandex_tokens.json"
        self.tokens_file.parent.mkdir(exist_ok=True)
        
        # Загружаем токены пользователей
        self.user_tokens: Dict[str, str] = self._load_tokens()
        
        # OAuth настройки
        # Используем публичный client_id от Яндекс Музыки
        self.client_id = "23cabbbdc6cd418abb4b39c32c41195d"
        self.redirect_uri = os.getenv("YANDEX_REDIRECT_URI", "https://kidwork.live/spotify/yandex_callback.html")
    
    def _load_tokens(self) -> Dict[str, str]:
        if not self.tokens_file.exists():
            return {}
        try:
            with open(self.tokens_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    
    def _save_tokens(self):
        try:
            with open(self.tokens_file, 'w', encoding='utf-8') as f:
                json.dump(self.user_tokens, f, indent=2, ensure_ascii=False)
        except:
            pass
    
    def has_credentials(self, user_id: int) -> bool:
        return str(user_id) in self.user_tokens
    
    def set_token(self, user_id: int, token: str) -> bool:
        """
        Сохраняет токен пользователя и проверяет его валидность
        """
        if not YANDEX_MUSIC_AVAILABLE:
            return False
        
        try:
            # Проверяем токен
            client = Client(token).init()
            if client.me and client.me.account:
                self.user_tokens[str(user_id)] = token
                self._save_tokens()
                logger.info(f"Yandex Music token saved for user {user_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Invalid Yandex Music token for user {user_id}: {e}")
            return False
    
    def get_auth_url(self) -> str:
        """
        Генерирует URL для OAuth авторизации Яндекс Музыки
        Использует implicit flow (токен сразу в URL)
        """
        import urllib.parse
        params = {
            "response_type": "token",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri
        }
        auth_url = f"https://oauth.yandex.ru/authorize?{urllib.parse.urlencode(params)}"
        logger.info(f"Generated Yandex OAuth URL with redirect_uri: {self.redirect_uri}")
        return auth_url
    
    def authorize_user(self, user_id: int, token: str) -> bool:
        """
        Авторизует пользователя по токену из OAuth callback
        Возвращает True если успешно
        """
        return self.set_token(user_id, token)
    
    def logout(self, user_id: int) -> bool:
        """Удаляет токен пользователя"""
        uid = str(user_id)
        if uid in self.user_tokens:
            del self.user_tokens[uid]
            self._save_tokens()
            return True
        return False
    
    def get_client(self, user_id: int) -> Optional['Client']:
        if not YANDEX_MUSIC_AVAILABLE:
            return None
        
        uid = str(user_id)
        if uid not in self.user_tokens:
            return None
        
        try:
            return Client(self.user_tokens[uid]).init()
        except:
            return None
    
    async def get_current_track(self, user_id: int) -> Optional[Dict]:
        """
        Получает текущий играющий трек из Яндекс Музыки
        """
        if not YANDEX_MUSIC_AVAILABLE:
            return None
        
        try:
            client = self.get_client(user_id)
            if not client:
                return None
            
            # Получаем очереди воспроизведения
            queues = client.queues_list()
            if not queues:
                return None
            
            # Берём последнюю активную очередь
            last_queue = client.queue(queues[0].id)
            if not last_queue:
                return None
            
            # Получаем текущий трек
            current_track_id = last_queue.get_current_track()
            if not current_track_id:
                return None
            
            # Получаем информацию о треке
            track = current_track_id.fetch_track()
            if not track:
                return None
            
            # Парсим артистов
            artists = ", ".join([a.name for a in track.artists]) if track.artists else "Unknown"
            track_name = track.title or "Unknown"
            
            # Получаем обложку
            album_cover = None
            if track.cover_uri:
                album_cover = f"https://{track.cover_uri.replace('%%', '400x400')}"
            
            return {
                "text": f"{artists} - {track_name}",
                "album_cover": album_cover,
                "service": "yandex"
            }
            
        except Exception as e:
            logger.debug(f"Error getting Yandex Music track for user {user_id}: {e}")
            return None


yandex_manager = YandexMusicManager()

