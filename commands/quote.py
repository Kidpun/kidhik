"""
Команда .цитата (Quote)
Локальная генерация через Pillow
"""
import logging
import io
import textwrap
from telethon import events
from telethon.utils import get_display_name
from PIL import Image, ImageDraw, ImageFont, ImageOps

logger = logging.getLogger(__name__)

def create_quote_image(text, author_name, avatar_bytes=None):
    # Настройки
    width = 512
    padding = 20
    avatar_size = 50
    bg_color = (25, 25, 35)
    text_color = (255, 255, 255)
    name_color = (100, 200, 255)
    font_size = 20
    
    # Шрифты (попытка загрузить системные)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", font_size)
        name_font = ImageFont.truetype("DejaVuSans-Bold.ttf", font_size)
    except:
        font = ImageFont.load_default()
        name_font = ImageFont.load_default()

    # Подготовка текста
    draw = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    lines = textwrap.wrap(text, width=40) # Примерная ширина
    
    # Расчет высоты
    line_height = draw.textbbox((0, 0), "A", font=font)[3] + 5
    text_height = len(lines) * line_height
    total_height = max(avatar_size, text_height) + padding * 2
    
    # Создаем холст
    img = Image.new('RGB', (width, total_height), bg_color)
    draw = ImageDraw.Draw(img)
    
    # Аватар
    if avatar_bytes:
        try:
            avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
            avatar = avatar.resize((avatar_size, avatar_size), Image.Resampling.LANCZOS)
            
            # Маска для круга
            mask = Image.new('L', (avatar_size, avatar_size), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse((0, 0, avatar_size, avatar_size), fill=255)
            
            img.paste(avatar, (padding, padding), mask)
        except:
            pass # Если ошибка с аватаркой, пропускаем
    else:
        # Плейсхолдер
        draw.ellipse((padding, padding, padding + avatar_size, padding + avatar_size), fill=(100, 100, 100))

    # Имя
    name_x = padding + avatar_size + 15
    draw.text((name_x, padding), author_name, font=name_font, fill=name_color)
    
    # Текст
    text_y = padding + 25
    for line in lines:
        draw.text((name_x, text_y), line, font=font, fill=text_color)
        text_y += line_height
        
    return img

async def quote_command(event: events.NewMessage.Event):
    """
    .цитата - Локальная генерация цитаты
    """
    reply = await event.get_reply_message()
    if not reply or not reply.message:
        await event.edit("❌ Ответьте на текстовое сообщение!")
        return
        
    await event.edit("🎨 Рисую...")
    
    try:
        sender = await reply.get_sender()
        name = get_display_name(sender) if sender else "Unknown"
        
        # Качаем аватар
        avatar_bytes = await event.client.download_profile_photo(sender, bytes)
        
        # Генерируем (в отдельном потоке, чтобы не блочить)
        # Но для простоты пока синхронно
        img = create_quote_image(reply.message, name, avatar_bytes)
        
        # Сохраняем в буфер
        out = io.BytesIO()
        img.save(out, format='PNG')
        out.seek(0)
        
        await event.delete()
        await event.respond(file=out)
        
    except Exception as e:
        logger.error(f"Quote gen error: {e}")
        try: await event.edit(f"❌ Ошибка: {e}")
        except: pass
