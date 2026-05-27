"""
Команда .сбой
Проверяет статус сервисов через detector404.ru
"""
import logging
import aiohttp
import re
import time
from telethon import events

logger = logging.getLogger(__name__)

# Кеш запросов: {service_name: (timestamp, response_text)}
_down_cache = {}
CACHE_TTL = 600  # 10 минут

async def down_command(event: events.NewMessage.Event):
    """
    Обработчик команды .сбой <сервис>
    """
    try:
        args = event.message.text.split(maxsplit=1)
        if len(args) < 2:
            await event.edit("❌ Укажите сервис.\nПример: <code>.сбой telegram</code>", parse_mode='html')
            return
            
        raw_name = args[1].strip().lower()
        
        # Маппинг популярных сокращений
        aliases = {
            'tg': 'telegram',
            'vk': 'vkontakte',
            'ds': 'discord',
            'yt': 'youtube',
            'wa': 'whatsapp',
            'steam': 'steam'
        }
        service_name = aliases.get(raw_name, raw_name)
        
        # 1. Проверка кеша
        current_time = time.time()
        if service_name in _down_cache:
            ts, cached_resp = _down_cache[service_name]
            if current_time - ts < CACHE_TTL:
                await event.edit(cached_resp + f"\n\n⏳ <i>Актуально на {time.strftime('%H:%M', time.localtime(ts))}</i>", parse_mode='html', link_preview=False)
                return
        
        url = f"https://detector404.ru/{service_name}"
        
        await event.edit(f"🔍 Ищу информацию о <b>{service_name}</b>...", parse_mode='html')
        
        async with aiohttp.ClientSession() as session:
            try:
                # Добавляем User-Agent, чтобы не заблочили
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                async with session.get(url, headers=headers, timeout=10) as resp:
                    if resp.status != 200:
                        # Попробуем поискать (если страница поиска есть), но пока просто ошибка
                        await event.edit(f"❌ Сервис <b>{service_name}</b> не найден на detector404.", parse_mode='html')
                        return
                    
                    html = await resp.text()
            except Exception as e:
                await event.edit(f"❌ Ошибка соединения: {e}")
                return

        # --- ПАРСИНГ HTML (RegEx) ---
        
        # 1. Заголовок сервиса (обычно в H1)
        title = service_name.capitalize()
        title_match = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.IGNORECASE)
        if title_match:
            # Убираем теги внутри H1 если есть
            clean_title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()
            if clean_title: title = clean_title
            
        # 2. Статус
        # На detector404 статус часто кодируется в тексте или классе
        status = "Неизвестно"
        status_color = "⚪"
        
        # Простые проверки по тексту страницы
        if "Сбоев нет" in html or "работает стабильно" in html or "No problems at" in html:
            status = "Работает стабильно"
            status_color = "🟢"
        elif "Сбой" in html or "Проблемы" in html or "Problems at" in html:
            status = "Наблюдаются сбои"
            status_color = "🔴"
            # Если "Возможны сбои"
            if "Возможны сбои" in html or "Possible problems" in html:
                status = "Возможны сбои"
                status_color = "🟡"
        
        # 3. Попытка найти количество жалоб (сложно без структуры, ищем цифры рядом с "отчетов")
        complaints = ""
        # Пример: "123 отчетов за последние 24 часа"
        comp_match = re.search(r'(\d+)\s+(отчетов|жалоб)', html, re.IGNORECASE)
        if comp_match:
            complaints = f"\n📉 <b>Жалоб:</b> {comp_match.group(1)}"
            
        # Формируем ответ
        response = (
            f"📊 <b>{title}</b>\n\n"
            f"{status_color} <b>Статус:</b> {status}"
            f"{complaints}\n\n"
            f"🔗 <a href='{url}'>Подробнее на Detector404</a>"
        )
        
        # Сохраняем в кеш
        _down_cache[service_name] = (time.time(), response)
        
        await event.edit(response, parse_mode='html', link_preview=False)
        
    except Exception as e:
        logger.error(f"Error in down command: {e}")
        await event.respond("❌ Ошибка при проверке статуса")

