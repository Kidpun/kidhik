"""
Кеш последних сообщений в чатах (изолированный для каждого пользователя)
"""
from typing import Dict, Optional, Tuple
from collections import deque
import logging

logger = logging.getLogger(__name__)


class MessageCache:
    """
    Кеш последних сообщений для каждого пользователя и его чатов.
    Теперь автоматически очищает старые ID при переполнении.
    """
    
    def __init__(self, max_size: int = 500, max_chats: int = 50):
        """
        :param max_size: Максимальное количество сообщений на чат
        :param max_chats: Максимальное количество чатов в кеше
        """
        self.max_size = max_size
        self.max_chats = max_chats
        # (user_id, chat_id) -> deque of message objects
        self.cache: Dict[Tuple[int, int], deque] = {}
        # (user_id, chat_id) -> {message_id: message}
        self.by_id: Dict[Tuple[int, int], Dict[int, object]] = {}
        # Для LRU - храним последний доступ к каждому чату
        self.last_access: Dict[Tuple[int, int], float] = {}
    
    def add_message(self, user_id: int, chat_id: int, message):
        """Добавляет сообщение в кеш и следит за размером"""
        if not hasattr(message, 'id'): return
        
        key = (user_id, chat_id)
        
        # Проверяем лимит чатов
        if key not in self.cache:
            if len(self.cache) >= self.max_chats:
                # Удаляем самый старый чат (LRU)
                import time
                oldest_key = min(self.last_access, key=self.last_access.get)
                logger.debug(f"Removing oldest chat from cache: {oldest_key}")
                self.cache.pop(oldest_key, None)
                self.by_id.pop(oldest_key, None)
                self.last_access.pop(oldest_key, None)
            
            self.cache[key] = deque(maxlen=self.max_size)
            self.by_id[key] = {}
        
        # Если дек полон, при добавлении нового удалится самый старый.
        # Нам нужно вручную удалить его из by_id.
        if len(self.cache[key]) >= self.max_size:
            oldest_msg = self.cache[key][0]
            if hasattr(oldest_msg, 'id'):
                self.by_id[key].pop(oldest_msg.id, None)
        
        self.cache[key].append(message)
        self.by_id[key][message.id] = message
        
        # Обновляем время последнего доступа
        import time
        self.last_access[key] = time.time()
    
    def get_last_message(self, user_id: int, chat_id: int):
        key = (user_id, chat_id)
        if key not in self.cache or len(self.cache[key]) == 0:
            return None
        return self.cache[key][-1]
    
    def get_message(self, user_id: int, chat_id: int, message_id: int):
        key = (user_id, chat_id)
        return self.by_id.get(key, {}).get(message_id)

    def cleanup_user(self, user_id: int):
        """Удаляет все кеши для конкретного пользователя"""
        keys_to_remove = [k for k in self.cache.keys() if k[0] == user_id]
        for k in keys_to_remove:
            self.cache.pop(k, None)
            self.by_id.pop(k, None)
            self.last_access.pop(k, None)
    
    def cleanup_old(self, max_age_seconds: int = 3600):
        """Удаляет чаты, к которым не было доступа более max_age_seconds"""
        import time
        current_time = time.time()
        keys_to_remove = [
            k for k, last_time in self.last_access.items()
            if current_time - last_time > max_age_seconds
        ]
        for k in keys_to_remove:
            logger.debug(f"Cleaning up old chat from cache: {k}")
            self.cache.pop(k, None)
            self.by_id.pop(k, None)
            self.last_access.pop(k, None)
    
    def get_memory_usage(self):
        """Возвращает примерное использование памяти в байтах"""
        total_messages = sum(len(msgs) for msgs in self.cache.values())
        return {
            'total_chats': len(self.cache),
            'total_messages': total_messages,
            'estimated_mb': (total_messages * 1024) / (1024 * 1024)  # Примерно 1KB на сообщение
        }

message_cache = MessageCache()
