"""
Менеджер Spotify API
Управляет токенами пользователей и получением текущего трека
"""
import os
import json
import logging
from typing import Optional, Dict
from pathlib import Path

# Загружаем .env ДО импорта spotipy
from dotenv import load_dotenv
load_dotenv()

import spotipy
from spotipy.oauth2 import SpotifyOAuth

logger = logging.getLogger(__name__)


class SpotifyManager:
    """
    Управляет Spotify API для пользователей
    """
    
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.tokens_file = self.base_dir / "data" / "spotify_tokens.json"
        self.tokens_file.parent.mkdir(exist_ok=True)
        
        # Загружаем токены пользователей
        self.user_tokens: Dict[int, Dict] = self._load_tokens()
        
        # Настройки Spotify API (только из ENV)
        self.client_id = os.getenv("SPOTIFY_CLIENT_ID", "")
        self.client_secret = os.getenv("SPOTIFY_CLIENT_SECRET", "")
        self.redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI", "http://localhost:8888/callback")
        
        if not self.client_id or not self.client_secret:
            logger.info("Spotify API не настроен. Команда .музыка отключена.")
    
    def _load_tokens(self) -> Dict[int, Dict]:
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
        uid_str = str(user_id)
        has_creds = uid_str in self.user_tokens or user_id in self.user_tokens
        logger.info(f"Checking Spotify credentials for user {user_id}: {has_creds}")
        logger.info(f"Available user tokens: {list(self.user_tokens.keys())}")
        return has_creds
    
    def logout(self, user_id: int):
        """Удаляет токены пользователя (отключает Spotify)"""
        uid = str(user_id)
        if uid in self.user_tokens:
            del self.user_tokens[uid]
            self._save_tokens()
            return True
        return False
    
    def set_tokens(self, user_id: int, access_token: str, refresh_token: str, expires_at: int):
        self.user_tokens[str(user_id)] = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_at": expires_at
        }
        self._save_tokens()
    
    def get_client(self, user_id: int) -> Optional[spotipy.Spotify]:
        uid = str(user_id)
        if not self.has_credentials(user_id):
            return None
        
        try:
            tokens = self.user_tokens[uid]
            oauth = SpotifyOAuth(
                client_id=self.client_id,
                client_secret=self.client_secret,
                redirect_uri=self.redirect_uri,
                scope="user-read-currently-playing user-read-playback-state",
                cache_path=None
            )
            
            token_info = {
                "access_token": tokens["access_token"],
                "refresh_token": tokens["refresh_token"],
                "expires_at": tokens["expires_at"]
            }
            
            if oauth.is_token_expired(token_info):
                token_info = oauth.refresh_access_token(token_info["refresh_token"])
                self.set_tokens(user_id, token_info["access_token"], token_info["refresh_token"], token_info["expires_at"])
            
            return spotipy.Spotify(auth=token_info["access_token"])
        except:
            return None
    
    def get_auth_url(self) -> Optional[str]:
        try:
            oauth = SpotifyOAuth(
                client_id=self.client_id,
                client_secret=self.client_secret,
                redirect_uri=self.redirect_uri,
                scope="user-read-currently-playing user-read-playback-state",
                cache_path=None
            )
            return oauth.get_authorize_url()
        except:
            return None
    
    def exchange_code_for_tokens(self, code: str) -> Optional[Dict]:
        try:
            oauth = SpotifyOAuth(
                client_id=self.client_id,
                client_secret=self.client_secret,
                redirect_uri=self.redirect_uri,
                scope="user-read-currently-playing user-read-playback-state",
                cache_path=None
            )
            return oauth.get_access_token(code, as_dict=True)
        except Exception as e:
            logger.error(f"Error exchanging code for tokens: {e}")
            return None
    
    def authorize_user(self, user_id: int, code: str) -> bool:
        """
        Авторизует пользователя по коду из OAuth callback
        Возвращает True если успешно
        """
        try:
            token_info = self.exchange_code_for_tokens(code)
            if not token_info:
                return False
            
            self.set_tokens(
                user_id,
                token_info["access_token"],
                token_info["refresh_token"],
                token_info["expires_at"]
            )
            logger.info(f"User {user_id} successfully authorized with Spotify")
            return True
        except Exception as e:
            logger.error(f"Error authorizing user {user_id}: {e}")
            return False
    
    async def get_current_track(self, user_id: int) -> Optional[Dict]:
        try:
            logger.info(f"🎵 Getting current track for user {user_id}")
            client = self.get_client(user_id)
            if not client:
                logger.info(f"No Spotify client for user {user_id}")
                return None
            
            # Проверяем, чей это аккаунт на самом деле
            try:
                me = client.me()
                logger.info(f"Spotify account for user {user_id}: {me.get('id')} ({me.get('display_name')})")
            except Exception as e:
                logger.error(f"Error getting Spotify account info: {e}")
            
            # Пробуем получить текущий трек
            current = client.current_user_playing_track()
            logger.info(f"Spotify response for user {user_id}: is_playing={current.get('is_playing') if current else None}")
            
            if not current:
                return None
            
            # Проверяем, играет ли что-то
            if not current.get("is_playing"):
                return None
            
            item = current.get("item")
            if not item:
                return None
            
            # Парсим артистов (исправлен баг)
            artists_list = item.get("artists", [])
            if artists_list:
                artists = ", ".join([a["name"] for a in artists_list])
            else:
                artists = "Unknown"
            
            track_name = item.get("name", "Unknown")
            
            album_cover = None
            images = item.get("album", {}).get("images", [])
            if images:
                album_cover = images[0].get("url")
            
            return {
                "text": f"{artists} - {track_name}",
                "album_cover": album_cover
            }
        except Exception as e:
            logger.error(f"Error getting current track for user {user_id}: {e}")
            return None

spotify_manager = SpotifyManager()
