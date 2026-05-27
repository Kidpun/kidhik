"""
Команда .факт
Отправляет случайный факт из файла text/facts.txt
"""
import logging
import random
from pathlib import Path
from telethon import events

logger = logging.getLogger(__name__)

# Путь к файлу с фактами
FACTS_FILE = Path(__file__).parent.parent / "text" / "facts.txt"


def load_facts():
    """Загружает факты из файла"""
    try:
        if not FACTS_FILE.exists():
            logger.warning(f"Файл {FACTS_FILE} не найден")
            return []
        
        with open(FACTS_FILE, 'r', encoding='utf-8') as f:
            facts = [line.strip() for line in f if line.strip()]
        
        logger.debug(f"Загружено {len(facts)} фактов из {FACTS_FILE}")
        return facts
    except Exception as e:
        logger.error(f"Ошибка при загрузке фактов: {e}")
        return []


async def fact_command(event: events.NewMessage.Event):
    """
    Обработчик команды .факт
    Отправляет случайный факт из файла
    """
    facts = load_facts()
    
    if not facts:
        await event.respond("❌ Файл с фактами не найден или пуст.")
        return
    
    # Выбираем случайный факт
    random_fact = random.choice(facts)
    
    await event.respond(random_fact)
    logger.info(f"Отправлен факт пользователю {event.sender_id}")





















