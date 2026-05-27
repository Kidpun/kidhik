"""
Команда .пинг
Замеряет скорость ответа (latency) от серверов Telegram
"""
import time
import logging
from telethon import events

logger = logging.getLogger(__name__)

async def ping_command(event: events.NewMessage.Event):
    """
    Обработчик команды .пинг
    """
    try:
        start = time.perf_counter()
        
        # Редактируем сообщение (это отправляет запрос к серверу Telegram)
        msg = await event.edit("🏓")
        
        end = time.perf_counter()
        
        # Считаем разницу в миллисекундах
        delta_ms = (end - start) * 1000
        
        # Красивый вывод в зависимости от скорости
        speed_icon = "🟢"
        if delta_ms > 300: speed_icon = "🟡"
        if delta_ms > 1000: speed_icon = "🔴"
        
        await msg.edit(
            f"🏓 <b>Понг!</b>\n"
            f"{speed_icon} Отклик: <code>{delta_ms:.2f} мс</code>",
            parse_mode='html'
        )
        
        logger.info(f"Ping: {delta_ms:.2f} ms")
        
    except Exception as e:
        logger.error(f"Error in ping command: {e}")
        # Если не удалось отредактировать (например, сообщение удалено), шлем новое
        try:
            await event.respond("❌ Ошибка пинга")
        except Exception: pass


