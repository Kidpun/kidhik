"""
Команда .tr <язык>
Перевод текста через Google Translate (deep-translator)
"""
import logging
from telethon import events
try:
    from deep_translator import GoogleTranslator
    TRANS_AVAILABLE = True
except ImportError:
    TRANS_AVAILABLE = False

logger = logging.getLogger(__name__)

async def translate_command(event: events.NewMessage.Event):
    """
    .tr <lang> - Перевести реплай
    Пример: .tr en
    """
    if not TRANS_AVAILABLE:
        await event.edit("❌ Модуль deep-translator не установлен.\n`pip install deep-translator`")
        return

    args = event.message.text.split()
    target_lang = args[1] if len(args) > 1 else 'ru'
    
    reply = await event.get_reply_message()
    if not reply or not reply.text:
        await event.edit("❌ Ответьте на текстовое сообщение!")
        return
        
    try:
        await event.edit(f"🔄 Перевожу на {target_lang}...")
        
        translator = GoogleTranslator(source='auto', target=target_lang)
        translated = translator.translate(reply.text)
        
        await event.edit(
            f"🌍 <b>Перевод ({target_lang}):</b>\n\n"
            f"{translated}",
            parse_mode='html'
        )
    except Exception as e:
        logger.error(f"Translation error: {e}")
        await event.edit(f"❌ Ошибка перевода: {e}")


