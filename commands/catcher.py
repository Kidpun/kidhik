"""
Модуль для авто-ловли чеков CryptoBot
Поддерживает:
- Поиск в тексте и кнопках
- Активацию чеков с паролем (Brute-force из контекста)
- Работу в фоне
"""
import logging
import re
import asyncio
from telethon import events

logger = logging.getLogger(__name__)

# Глобальный флаг работы ловца
CATCHER_ACTIVE = False

# Регулярка для чеков CryptoBot / send
CHECK_REGEX = re.compile(r'(?:t\.me\/|https:\/\/t\.me\/)(?:send|CryptoBot)\?start=([A-Za-z0-9_-]+)')

def extract_potential_passwords(text):
    """
    Извлекает возможные пароли из текста сообщения
    """
    if not text: return []
    passwords = []
    
    # 1. Текст в кавычках (обычных и елочках)
    passwords.extend(re.findall(r'"([^"]+)"', text))
    passwords.extend(re.findall(r"'([^']+)'", text))
    passwords.extend(re.findall(r'«([^»]+)»', text))
    
    # 2. Текст в моноширинном формате (`код`)
    passwords.extend(re.findall(r'`([^`]+)`', text))
    
    # 3. После слова "пароль" (берем следующее слово)
    # Пример: Пароль: 1234
    match = re.search(r'(?:пароль|pass|password)[:\s-]*([A-Za-z0-9]+)', text, re.IGNORECASE)
    if match: passwords.append(match.group(1))
    
    # 4. Текст в скобках
    # passwords.extend(re.findall(r'\(([^)]+)\)', text)) # Слишком много мусора
    
    # Чистим и фильтруем
    clean_passwords = []
    for p in passwords:
        p = p.strip()
        if len(p) > 0 and len(p) < 30 and "http" not in p:
            clean_passwords.append(p)
            
    return list(set(clean_passwords)) # Уникальные

async def toggle_catcher(event: events.NewMessage.Event):
    """
    .чек - Включить/Выключить авто-ловлю чеков CryptoBot
    """
    global CATCHER_ACTIVE
    CATCHER_ACTIVE = not CATCHER_ACTIVE
    
    status = "🟢 <b>ВКЛЮЧЕН</b>" if CATCHER_ACTIVE else "🔴 <b>ВЫКЛЮЧЕН</b>"
    try:
        await event.edit(f"💰 <b>Ловец чеков CryptoBot</b>\nСтатус: {status}", parse_mode='html')
    except Exception:
        await event.respond(f"💰 <b>Ловец чеков CryptoBot</b>\nСтатус: {status}", parse_mode='html')

async def check_catcher_handler(event):
    """
    Фоновый обработчик сообщений для ловли чеков
    """
    if not CATCHER_ACTIVE:
        return

    original_text = getattr(event.message, 'message', "") or ""
    found_code = None

    # 1. Проверяем текст сообщения
    if original_text and ("t.me/" in original_text or "start=" in original_text):
        match = CHECK_REGEX.search(original_text)
        if match:
            found_code = match.group(1)
            logger.info(f"💰 Найден чек (текст): {found_code} в чате {event.chat_id}")

    # 2. Проверяем кнопки (если в тексте не нашли или нашли другое)
    if not found_code and event.message.reply_markup and hasattr(event.message.reply_markup, 'rows'):
        for row in event.message.reply_markup.rows:
            for button in row.buttons:
                if hasattr(button, 'url') and button.url:
                    match = CHECK_REGEX.search(button.url)
                    if match:
                        found_code = match.group(1)
                        logger.info(f"💰 Найден чек (кнопка): {found_code} в чате {event.chat_id}")
                        break
            if found_code: break
    
    if found_code:
        # Активируем асинхронно
        asyncio.create_task(activate_check(event.client, found_code, original_text))

async def activate_check(client, code, original_text):
    """
    Активация чека с поддержкой паролей
    """
    try:
        # Используем conversation для диалога с ботом
        # timeout=5 чтобы не висеть вечно
        async with client.conversation('send', timeout=5, exclusive=False) as conv:
            # 1. Отправляем старт
            await conv.send_message(f"/start {code}")
            logger.info(f"🚀 [Catcher] Старт чека: {code}")
            
            # 2. Ждем ответ
            try:
                response = await conv.get_response()
            except asyncio.TimeoutError:
                logger.warning(f"⏳ [Catcher] Таймаут ответа от CryptoBot")
                return

            text_resp = response.text.lower()
            
            # 3. Анализируем ответ
            if "вы получили" in text_resp:
                logger.info(f"✅ [Catcher] Чек активирован!")
                return
                
            if "введите пароль" in text_resp or "enter password" in text_resp:
                logger.info("🔐 [Catcher] Требуется пароль. Ищем...")
                
                passwords = extract_potential_passwords(original_text)
                if not passwords:
                    logger.warning("❌ [Catcher] Пароли не найдены в тексте.")
                    return
                
                logger.info(f"💡 [Catcher] Пробуем пароли: {passwords}")
                
                # Пробуем до 3 паролей
                for pwd in passwords[:3]:
                    await conv.send_message(pwd)
                    try:
                        resp2 = await conv.get_response()
                        if "вы получили" in resp2.text.lower():
                            logger.info(f"✅ [Catcher] Пароль подошел: {pwd}")
                            break
                        elif "неверный" in resp2.text.lower():
                            logger.info(f"❌ [Catcher] Неверный пароль: {pwd}")
                    except Exception:
                        break
                        
            elif "подпишитесь" in text_resp:
                logger.info("⚠️ [Catcher] Требуется подписка. Пропуск.")
                
    except Exception as e:
        logger.error(f"❌ [Catcher] Ошибка активации: {e}")
