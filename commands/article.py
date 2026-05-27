import logging
import random
from telethon import events
from config import BASE_DIR

logger = logging.getLogger(__name__)

# Грузим статьи УК РФ
ARTICLES_FILE = BASE_DIR / 'text' / 'ykrf.txt'
_articles = []

def load_articles():
    global _articles
    try:
        with open(ARTICLES_FILE, encoding='utf-8') as f:
            lines = f.readlines()
        for line in lines:
            line = line.strip()
            # Формат: "Статья 105. Убийство"
            if line and line.startswith('Статья ') and '. ' in line:
                # Убираем слово "Статья " и разделяем по первой точке
                line_without_prefix = line.replace('Статья ', '', 1)
                if '. ' in line_without_prefix:
                    num, title = line_without_prefix.split('. ', 1)
                    _articles.append((num.strip(), title.strip()))
    except Exception as e:
        logger.error(f"Не удалось загрузить статьи УК РФ: {e}")
        _articles.clear()

# загружаем при старте
load_articles()

async def article_command(event: events.NewMessage.Event):
    """
    .статья — выдает случайную статью УК РФ:
    ваша статья ук рф - номерстатьи название
    """
    if not _articles:
        try:
            load_articles()
        except Exception:
            pass
    if not _articles:
        await event.respond("❌ Статьи УК РФ недоступны!")
        return
    num, title = random.choice(_articles)
    await event.respond(f"Ваша статья УК РФ - {num} {title}")



