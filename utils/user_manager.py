"""
Менеджер активных процессов пользователей
Управляет состоянием активных команд для каждого пользователя
"""
import asyncio
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class UserManager:
    """
    Управляет активными процессами пользователей
    Каждый пользователь может иметь только один активный процесс
    """
    
    def __init__(self):
        # Хранит активные задачи для каждого пользователя
        self.active_tasks: Dict[int, asyncio.Task] = {}
        # Хранит состояние активности для каждого пользователя
        self.active_states: Dict[int, str] = {}  # user_id -> command_name
    
    def is_active(self, user_id: int) -> bool:
        """Проверяет, есть ли у пользователя активный процесс"""
        return user_id in self.active_tasks and not self.active_tasks[user_id].done()
    
    def get_active_command(self, user_id: int) -> Optional[str]:
        """Возвращает название активной команды пользователя"""
        return self.active_states.get(user_id)
    
    def set_active(self, user_id: int, command_name: str, task: asyncio.Task):
        """Устанавливает активный процесс для пользователя"""
        # Останавливаем предыдущий процесс, если есть
        self.stop(user_id)
        
        self.active_tasks[user_id] = task
        self.active_states[user_id] = command_name
        logger.info(f"User {user_id} started command: {command_name}")
    
    def stop(self, user_id: int) -> bool:
        """
        Останавливает активный процесс пользователя
        Возвращает True, если процесс был остановлен
        """
        if user_id in self.active_tasks:
            task = self.active_tasks[user_id]
            if not task.done():
                task.cancel()
                logger.info(f"Stopped active process for user {user_id}")
            
            del self.active_tasks[user_id]
            if user_id in self.active_states:
                del self.active_states[user_id]
            return True
        return False
    
    def cleanup(self, user_id: int):
        """Очищает завершённые задачи"""
        if user_id in self.active_tasks:
            task = self.active_tasks[user_id]
            if task.done():
                del self.active_tasks[user_id]
                if user_id in self.active_states:
                    del self.active_states[user_id]


# Глобальный экземпляр менеджера
user_manager = UserManager()





































