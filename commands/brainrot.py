"""
Команда .бреинрот
Отправляет случайное название бреинрота из файла text/brainrot.txt
"""
import logging
import random
from pathlib import Path
from telethon import events

logger = logging.getLogger(__name__)

# Путь к файлу с бреинротами
BRAINROT_FILE = Path(__file__).parent.parent / "text" / "brainrot.txt"


def load_brainrots():
    """Загружает бреинроты из файла"""
    try:
        if not BRAINROT_FILE.exists():
            logger.warning(f"Файл {BRAINROT_FILE} не найден")
            return []
        
        with open(BRAINROT_FILE, 'r', encoding='utf-8') as f:
            brainrots = [line.strip() for line in f if line.strip()]
        
        logger.debug(f"Загружено {len(brainrots)} бреинротов из {BRAINROT_FILE}")
        return brainrots
    except Exception as e:
        logger.error(f"Ошибка при загрузке бреинротов: {e}")
        return []


async def brainrot_command(event: events.NewMessage.Event):
    """
    Обработчик команды .бреинрот
    Отправляет случайное название бреинрота из файла
    """
    brainrots = load_brainrots()
    
    if not brainrots:
        await event.respond("❌ Файл с бреинротами не найден или пуст.")
        return
    
    # Выбираем случайный бреинрот
    random_brainrot = random.choice(brainrots)
    
    await event.respond(random_brainrot)
    logger.info(f"Отправлен бреинрот пользователю {event.sender_id}")





















