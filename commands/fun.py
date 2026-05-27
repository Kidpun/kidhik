"""
Развлекательные команды:
.процент - Случайный процент
.тайп - Имитация набора текста
.кто - Выбор случайного участника
"""
import asyncio
import random
from telethon import events
from telethon.tl.types import ChannelParticipantsAdmins

async def percent_command(event: events.NewMessage.Event):
    """
    .процент <текст> - Выдает случайный процент
    """
    text = event.message.text.split(maxsplit=1)
    query = text[1] if len(text) > 1 else "Удача"
    
    percent = random.randint(0, 100)
    
    # Emoji
    emoji = "😐"
    if percent == 100: emoji = "😎"
    elif percent > 80: emoji = "🔥"
    elif percent > 50: emoji = "👍"
    elif percent < 10: emoji = "💀"
    
    await event.edit(f"{emoji} <b>{query}:</b> {percent}%", parse_mode='html')

async def type_command(event: events.NewMessage.Event):
    """
    .тайп <секунды> - Имитирует набор текста
    """
    args = event.message.text.split()
    try:
        seconds = int(args[1]) if len(args) > 1 else 10
    except:
        seconds = 10
        
    if seconds > 300: seconds = 300 # Лимит 5 минут
    
    try:
        await event.delete()
    except: pass
    
    # Имитируем тайпинг
    async with event.client.action(event.chat_id, 'typing'):
        await asyncio.sleep(seconds)

async def who_command(event: events.NewMessage.Event):
    """
    .кто <текст> - Выбрать случайного участника чата
    """
    if not event.is_group:
        await event.edit("❌ Работает только в группах!")
        return
        
    text = event.message.text.split(maxsplit=1)
    query = text[1] if len(text) > 1 else "красавчик"
    
    await event.edit(f"🤔 <b>Кто {query}?</b>\nИщу кандидата...")
    
    try:
        # Берем случайных участников (агрессивно)
        # Получаем всех (до 2000 для скорости)
        users = await event.client.get_participants(event.chat_id, limit=500)
        
        if not users:
            await event.edit("❌ Не удалось получить список участников.")
            return
            
        winner = random.choice(users)
        
        # Формируем имя
        first = getattr(winner, 'first_name', '') or ''
        last = getattr(winner, 'last_name', '') or ''
        name = f"{first} {last}".strip() or "User"
        
        mention = f"<a href='tg://user?id={winner.id}'>{name}</a>"
        
        await event.edit(f"🤔 <b>Кто {query}?</b>\n\n👉 {mention}!", parse_mode='html')
        
    except Exception as e:
        await event.edit(f"❌ Ошибка: {e}")
