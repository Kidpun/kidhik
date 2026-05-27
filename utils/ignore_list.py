"""
Управление списком игнорируемых чатов
"""
import json
import logging
from pathlib import Path
from typing import Set

logger = logging.getLogger(__name__)


class IgnoreListManager:
    """
    Управляет списком игнорируемых чатов для каждого пользователя
    """
    
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.ignore_file = self.base_dir / "data" / "ignore_list.json"
        self.ignore_file.parent.mkdir(exist_ok=True)
        
        # Структура: {user_id: {chat_id1, chat_id2, ...}}
        self.ignore_lists: dict = self._load_ignore_lists()
    
    def _load_ignore_lists(self) -> dict:
        """Загружает список игнорируемых чатов из файла"""
        if not self.ignore_file.exists():
            return {}
        try:
            with open(self.ignore_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Конвертируем списки в множества для быстрого поиска
                return {int(uid): set(data[uid]) for uid in data}
        except Exception as e:
            logger.error(f"Error loading ignore lists: {e}")
            return {}
    
    def _save_ignore_lists(self):
        """Сохраняет список игнорируемых чатов в файл"""
        try:
            # Конвертируем множества обратно в списки для JSON
            data = {str(uid): list(chat_ids) for uid, chat_ids in self.ignore_lists.items()}
            with open(self.ignore_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving ignore lists: {e}")
    
    def toggle_ignore(self, user_id: int, chat_id: int) -> bool:
        """
        Переключает игнорирование чата для пользователя
        Возвращает True если чат теперь игнорируется, False если больше не игнорируется
        """
        if user_id not in self.ignore_lists:
            self.ignore_lists[user_id] = set()
        
        if chat_id in self.ignore_lists[user_id]:
            # Убираем из игнора
            self.ignore_lists[user_id].remove(chat_id)
            if not self.ignore_lists[user_id]:
                del self.ignore_lists[user_id]
            self._save_ignore_lists()
            return False
        else:
            # Добавляем в игнор
            self.ignore_lists[user_id].add(chat_id)
            self._save_ignore_lists()
            return True
    
    def is_ignored(self, user_id: int, chat_id: int) -> bool:
        """Проверяет, игнорируется ли чат для пользователя, нормализуя chat_id (-100... для каналов)"""
        normed_id = int(chat_id)
        # Если id группы/канала положительный и длиннее 9 символов — это реально канал, нужно -100...
        if abs(normed_id) > 1e11 or str(normed_id).startswith('-100'):
            normed_id = int(normed_id)
        elif abs(normed_id) > 1e9:
            normed_id = int(f'-100{abs(normed_id)}')
        return normed_id in self.ignore_lists.get(user_id, set())
    
    def get_ignored_chats(self, user_id: int) -> Set[int]:
        """Возвращает множество игнорируемых чатов для пользователя"""
        return self.ignore_lists.get(user_id, set())


ignore_manager = IgnoreListManager()



















