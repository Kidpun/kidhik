"""
Session Persistence - сохранение состояния сессий при перезапуске
"""
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger(__name__)

SESSION_STATE_FILE = Path(__file__).parent.parent / "data" / "session_states.json"


class SessionPersistence:
    """Управление сохранением состояния сессий"""
    
    def __init__(self):
        self.states: Dict[int, dict] = {}
        self.load()
    
    def load(self):
        """Загружает сохраненные состояния сессий"""
        try:
            if SESSION_STATE_FILE.exists():
                with open(SESSION_STATE_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Конвертируем ключи обратно в int
                    self.states = {int(k): v for k, v in data.items()}
                    logger.info(f"📂 Загружено {len(self.states)} состояний сессий")
            else:
                self.states = {}
                logger.info("📂 Файл состояний не найден, создаем новый")
        except Exception as e:
            logger.error(f"Ошибка загрузки состояний сессий: {e}")
            self.states = {}
    
    def save(self):
        """Сохраняет текущие состояния сессий"""
        try:
            SESSION_STATE_FILE.parent.mkdir(exist_ok=True)
            with open(SESSION_STATE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.states, f, indent=2, ensure_ascii=False)
            logger.debug(f"💾 Сохранено {len(self.states)} состояний сессий")
        except Exception as e:
            logger.error(f"Ошибка сохранения состояний сессий: {e}")
    
    def update_session(self, user_id: int, **kwargs):
        """
        Обновляет состояние сессии
        
        Доступные параметры:
        - last_active: datetime - последняя активность
        - status: str - статус (active, disconnected, error)
        - error_count: int - количество ошибок
        - last_error: str - последняя ошибка
        - device: str - устройство
        - reconnect_count: int - количество переподключений
        """
        if user_id not in self.states:
            self.states[user_id] = {
                'user_id': user_id,
                'created_at': datetime.now().isoformat(),
                'last_active': datetime.now().isoformat(),
                'status': 'active',
                'error_count': 0,
                'reconnect_count': 0
            }
        
        # Обновляем переданные поля
        for key, value in kwargs.items():
            if isinstance(value, datetime):
                value = value.isoformat()
            self.states[user_id][key] = value
        
        # Всегда обновляем last_active
        self.states[user_id]['last_active'] = datetime.now().isoformat()
        
        # Автосохранение каждые 10 обновлений
        if len(self.states) % 10 == 0:
            self.save()
    
    def get_session_state(self, user_id: int) -> Optional[dict]:
        """Получает состояние сессии"""
        return self.states.get(user_id)
    
    def remove_session(self, user_id: int):
        """Удаляет состояние сессии"""
        if user_id in self.states:
            del self.states[user_id]
            self.save()
            logger.info(f"🗑️ Удалено состояние сессии {user_id}")
    
    def get_active_sessions(self) -> list:
        """Возвращает список активных сессий"""
        return [
            uid for uid, state in self.states.items()
            if state.get('status') == 'active'
        ]
    
    def get_session_stats(self) -> dict:
        """Статистика по всем сессиям"""
        if not self.states:
            return {
                'total': 0,
                'active': 0,
                'disconnected': 0,
                'error': 0
            }
        
        stats = {
            'total': len(self.states),
            'active': 0,
            'disconnected': 0,
            'error': 0
        }
        
        for state in self.states.values():
            status = state.get('status', 'unknown')
            if status in stats:
                stats[status] += 1
        
        return stats
    
    def cleanup_old_sessions(self, days: int = 7):
        """Удаляет старые неактивные сессии"""
        from datetime import timedelta
        
        now = datetime.now()
        to_remove = []
        
        for uid, state in self.states.items():
            try:
                last_active = datetime.fromisoformat(state['last_active'])
                if (now - last_active).days > days:
                    to_remove.append(uid)
            except:
                pass
        
        for uid in to_remove:
            del self.states[uid]
        
        if to_remove:
            self.save()
            logger.info(f"🧹 Очищено {len(to_remove)} старых состояний сессий")
        
        return len(to_remove)


# Глобальный экземпляр
session_persistence = SessionPersistence()
