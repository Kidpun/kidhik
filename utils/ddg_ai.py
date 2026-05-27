"""
Утилита для работы с DuckDuckGo AI
Бесплатный доступ к GPT-4o mini и Llama 3.1 без ключей
"""
import logging
from typing import Optional
from duckduckgo_search import DDGS

logger = logging.getLogger(__name__)

def ask_ddg(prompt: str, model: str = "gpt-4o-mini") -> Optional[str]:
    """
    Отправляет запрос в DuckDuckGo AI Chat
    
    :param prompt: Запрос пользователя
    :param model: Модель ("gpt-4o-mini", "llama-3.1-70b", "claude-3-haiku", "mixtral-8x7b")
    :return: Ответ от нейросети или None при ошибке
    """
    try:
        # DDGS работает синхронно
        with DDGS() as ddgs:
            # chat() возвращает строку с ответом
            response = ddgs.chat(prompt, model=model)
            
            if response:
                logger.info(f"DDG ответ получен (длина: {len(response)} символов)")
                return response
            else:
                logger.warning("DDG вернул пустой ответ")
                return None
            
    except Exception as e:
        logger.error(f"Ошибка при запросе к DDG: {e}")
        return f"❌ Ошибка DuckDuckGo: {str(e)}"
























