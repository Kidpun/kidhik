"""
Модуль для работы с FunStat API
https://funstat.info/swagger/index.html
"""
import asyncio
import logging
import aiohttp
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class FunStatAPI:
    """Клиент для работы с FunStat API"""
    
    BASE_URL = "https://funstat.info/api"
    
    def __init__(self, token: str):
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        # Rate limit: 15 req/s
        self.rate_limit_delay = 1.0 / 15  # ~0.067 секунд между запросами
        self._last_request_time = 0
        self._lock = asyncio.Lock()
    
    async def _wait_rate_limit(self):
        """Ждет перед следующим запросом чтобы не превысить rate limit"""
        async with self._lock:
            current_time = asyncio.get_event_loop().time()
            time_since_last = current_time - self._last_request_time
            
            if time_since_last < self.rate_limit_delay:
                await asyncio.sleep(self.rate_limit_delay - time_since_last)
            
            self._last_request_time = asyncio.get_event_loop().time()
    
    async def _request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Базовый метод для HTTP запросов"""
        await self._wait_rate_limit()
        
        url = f"{self.BASE_URL}/{endpoint}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method, 
                    url, 
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=10),
                    **kwargs
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 401:
                        logger.error("FunStat API: Unauthorized (invalid token)")
                        return None
                    elif response.status == 429:
                        logger.warning("FunStat API: Rate limit exceeded")
                        return None
                    else:
                        logger.error(f"FunStat API error: {response.status}")
                        return None
        except asyncio.TimeoutError:
            logger.error("FunStat API: Request timeout")
            return None
        except Exception as e:
            logger.error(f"FunStat API request error: {e}")
            return None
    
    async def get_user_info(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает информацию о пользователе
        
        GET /user/{user_id}
        
        Возвращает:
        - id: Telegram ID
        - username: текущий username
        - first_name: имя
        - last_name: фамилия
        - phone: номер телефона (если доступен)
        - bio: описание профиля
        - is_premium: премиум статус
        - is_verified: верифицирован
        - registration_date: примерная дата регистрации
        """
        return await self._request("GET", f"user/{user_id}")
    
    async def get_username_history(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает историю изменений username
        
        GET /user/{user_id}/username-history
        
        Возвращает список изменений с датами
        """
        return await self._request("GET", f"user/{user_id}/username-history")
    
    async def get_name_history(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает историю изменений имени/фамилии
        
        GET /user/{user_id}/name-history
        """
        return await self._request("GET", f"user/{user_id}/name-history")
    
    async def get_photo_history(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает историю фото профиля
        
        GET /user/{user_id}/photo-history
        """
        return await self._request("GET", f"user/{user_id}/photo-history")
    
    async def get_bio_history(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает историю изменений описания (bio)
        
        GET /user/{user_id}/bio-history
        """
        return await self._request("GET", f"user/{user_id}/bio-history")
    
    async def get_phone_history(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает историю номеров телефона
        
        GET /user/{user_id}/phone-history
        """
        return await self._request("GET", f"user/{user_id}/phone-history")
    
    async def get_full_history(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает полную историю изменений профиля
        
        GET /user/{user_id}/full-history
        """
        return await self._request("GET", f"user/{user_id}/full-history")
    
    async def search_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Поиск пользователя по username (без @)
        
        GET /search/username/{username}
        """
        username = username.lstrip('@')
        return await self._request("GET", f"search/username/{username}")
    
    async def search_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        """
        Поиск пользователя по номеру телефона
        
        GET /search/phone/{phone}
        """
        return await self._request("GET", f"search/phone/{phone}")
    
    async def get_related_users(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает связанных пользователей
        
        GET /user/{user_id}/related
        """
        return await self._request("GET", f"user/{user_id}/related")
    
    async def get_groups(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает список групп пользователя
        
        GET /user/{user_id}/groups
        """
        return await self._request("GET", f"user/{user_id}/groups")

# Глобальный экземпляр (инициализируется с токеном из .env)
funstat_api: Optional[FunStatAPI] = None

def init_funstat(token: str):
    """Инициализирует FunStat API с токеном"""
    global funstat_api
    if token and token != "":
        funstat_api = FunStatAPI(token)
        logger.info("✅ FunStat API initialized")
    else:
        logger.warning("⚠️ FunStat token not provided, API disabled")
