"""
Команда .id
Показывает ID пользователя или группы
"""
import logging
from telethon import events
from telethon.tl.types import User, Channel, Chat
from utils.username_helper import get_user_username

logger = logging.getLogger(__name__)


async def id_command(event: events.NewMessage.Event):
    """
    Обработчик команды .id
    Показывает ID пользователя или группы
    """
    try:
        # Если есть ответ на сообщение - показываем ID автора ответа
        if event.message.is_reply:
            replied_msg = await event.get_reply_message()
            if replied_msg:
                sender = await replied_msg.get_sender()
                if sender:
                    user_id = sender.id
                    first_name = getattr(sender, 'first_name', '')
                    last_name = getattr(sender, 'last_name', '') or ''
                    username = await get_user_username(event.client, sender)
                    
                    full_name = f"{first_name} {last_name}".strip() or "Unknown"
                    username_text = f"@{username}" if username else "нет"
                    
                    text = f"👤 <b>ID пользователя</b>\n\n"
                    text += f"📝 <b>Имя:</b> {full_name}\n"
                    text += f"🆔 <b>ID:</b> <code>{user_id}</code>\n"
                    text += f"📱 <b>Username:</b> {username_text}"
                    
                    await event.respond(text, parse_mode='html')
                    return
        
        # Проверяем аргументы команды
        text = event.message.text.strip()
        parts = text.split()
        
        if len(parts) > 1:
            arg = parts[1]
            
            # Проверяем, это ID (число) или username
            try:
                if arg.isdigit():
                    # Это ID
                    entity = await event.client.get_entity(int(arg))
                elif arg.startswith('@'):
                    # Это username с @
                    entity = await event.client.get_entity(arg[1:])
                else:
                    # Возможно username без @
                    entity = await event.client.get_entity(arg)
                
                # Получили entity, показываем инфо
                user_id = entity.id
                first_name = getattr(entity, 'first_name', '')
                last_name = getattr(entity, 'last_name', '') or ''
                entity_username = await get_user_username(event.client, entity)
                
                full_name = f"{first_name} {last_name}".strip() or "Unknown"
                username_text = f"@{entity_username}" if entity_username else "нет"
                
                response_text = f"👤 <b>ID пользователя</b>\n\n"
                response_text += f"📝 <b>Имя:</b> {full_name}\n"
                response_text += f"🆔 <b>ID:</b> <code>{user_id}</code>\n"
                response_text += f"📱 <b>Username:</b> {username_text}"
                
                await event.respond(response_text, parse_mode='html')
                return
            except Exception as e:
                logger.debug(f"Error getting entity {arg}: {e}")
                await event.respond(f"❌ Пользователь {arg} не найден")
                return
        
        # Если просто .id без параметров
        chat = await event.get_chat()
        
        # Проверяем тип чата
        if isinstance(chat, User):
            # Личные сообщения - показываем ID собеседника
            user_id = chat.id
            first_name = getattr(chat, 'first_name', '')
            last_name = getattr(chat, 'last_name', '') or ''
            username = await get_user_username(event.client, chat)
            
            full_name = f"{first_name} {last_name}".strip() or "Unknown"
            username_text = f"@{username}" if username else "нет"
            
            text = f"👤 <b>ID пользователя</b>\n\n"
            text += f"📝 <b>Имя:</b> {full_name}\n"
            text += f"🆔 <b>ID:</b> <code>{user_id}</code>\n"
            text += f"📱 <b>Username:</b> {username_text}"
            
        elif isinstance(chat, (Channel, Chat)):
            # Группа или канал — показываем правильный ID
            raw_id = chat.id
            chat_title = getattr(chat, 'title', 'Группа')
            chat_username = getattr(chat, 'username', None)
            
            # Правильное преобразование ID для разных типов
            if isinstance(chat, Channel):
                # Супергруппы и каналы: добавляем -100 к положительному ID
                if raw_id > 0:
                    chat_id = -1000000000000 - raw_id  # Правильная формула: -100{id}
                else:
                    chat_id = raw_id  # Уже в правильном формате
                    
                chat_type = "Супергруппа" if getattr(chat, 'megagroup', False) else "Канал"
            else:
                # Обычные группы (Chat): ID уже в правильном формате (отрицательный)
                chat_id = -raw_id if raw_id > 0 else raw_id
                chat_type = "Обычная группа"

            username_text = f"@{chat_username}" if chat_username else "нет"

            text = f"💬 <b>ID группы/канала</b>\n\n"
            text += f"📝 <b>Название:</b> {chat_title}\n"
            text += f"🆔 <b>ID:</b> <code>{chat_id}</code>\n"
            text += f"📱 <b>Username:</b> {username_text}\n"
            text += f"ℹ️ <b>Тип:</b> {chat_type}"
        else:
            # Неизвестный тип чата
            chat_id = getattr(chat, 'id', 'Unknown')
            text = f"🆔 <b>ID:</b> <code>{chat_id}</code>"
        
        await event.respond(text, parse_mode='html')
        
    except Exception as e:
        logger.error(f"Ошибка в команде .id: {e}", exc_info=True)
        await event.respond("❌ Ошибка при получении ID")

