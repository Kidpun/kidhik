"""
Команды для работы с FunStat API
Получение истории изменений профилей Telegram
"""
import logging
from telethon import events
from datetime import datetime

logger = logging.getLogger(__name__)


def format_date(date_str: str) -> str:
    """Форматирует дату из ISO в читаемый формат"""
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return dt.strftime("%d.%m.%Y %H:%M")
    except Exception:
        return date_str


async def get_target_user_id(event):
    """Получает ID целевого пользователя из реплая или @username"""
    # Проверяем реплай
    if event.message.is_reply:
        replied_msg = await event.get_reply_message()
        if replied_msg and replied_msg.sender_id:
            return replied_msg.sender_id
    
    # Проверяем @username в тексте
    text = event.message.text.strip()
    if '@' in text:
        parts = text.split()
        for part in parts:
            if part.startswith('@') and len(part) > 1:
                username = part[1:]
                try:
                    entity = await event.client.get_entity(username)
                    return entity.id
                except Exception:
                    return None
    
    return None


async def history_command(event: events.NewMessage.Event):
    """
    Команда .история
    Показывает полную историю изменений профиля
    Использование: .история @username или реплай
    """
    from utils.funstat import funstat_api
    
    if not funstat_api:
        await event.edit("❌ FunStat API не настроен. Добавьте FUNSTAT_TOKEN в .env")
        return
    
    # Получаем ID пользователя
    user_id = await get_target_user_id(event)
    if not user_id:
        await event.edit("❌ Укажите пользователя: .история @username или реплай на сообщение")
        return
    
    await event.edit("🔍 Получаю историю изменений...")
    
    try:
        # Получаем полную историю
        data = await funstat_api.get_full_history(user_id)
        
        if not data:
            await event.edit("❌ Не удалось получить данные. Возможно пользователь не найден в базе FunStat.")
            return
        
        # Формируем сообщение
        text = f"📊 <b>История изменений профиля</b>\n"
        text += f"🆔 ID: <code>{user_id}</code>\n\n"
        
        # Username история
        if data.get('username_history'):
            text += f"📱 <b>История Username:</b>\n"
            for record in data['username_history'][:5]:  # Последние 5
                date = format_date(record.get('date', ''))
                username = record.get('username', 'неизвестно')
                text += f"  • @{username} — {date}\n"
            if len(data['username_history']) > 5:
                text += f"  <i>...и еще {len(data['username_history']) - 5}</i>\n"
            text += "\n"
        
        # Имя/фамилия история
        if data.get('name_history'):
            text += f"📝 <b>История имени:</b>\n"
            for record in data['name_history'][:5]:
                date = format_date(record.get('date', ''))
                first_name = record.get('first_name', '')
                last_name = record.get('last_name', '')
                full_name = f"{first_name} {last_name}".strip()
                text += f"  • {full_name} — {date}\n"
            if len(data['name_history']) > 5:
                text += f"  <i>...и еще {len(data['name_history']) - 5}</i>\n"
            text += "\n"
        
        # Фото история
        if data.get('photo_history'):
            text += f"🖼 <b>История фото:</b>\n"
            text += f"  Всего изменений: {len(data['photo_history'])}\n"
            if data['photo_history']:
                last_change = data['photo_history'][0]
                date = format_date(last_change.get('date', ''))
                text += f"  Последнее: {date}\n"
            text += "\n"
        
        # Bio история
        if data.get('bio_history'):
            text += f"📄 <b>История описания:</b>\n"
            for record in data['bio_history'][:3]:
                date = format_date(record.get('date', ''))
                bio = record.get('bio', '')[:50]
                text += f"  • {bio}... — {date}\n"
            text += "\n"
        
        # Номера телефонов
        if data.get('phone_history'):
            text += f"📞 <b>Известные номера:</b>\n"
            for record in data['phone_history']:
                phone = record.get('phone', 'скрыт')
                date = format_date(record.get('date', ''))
                text += f"  • <code>{phone}</code> — {date}\n"
            text += "\n"
        
        # Доп. инфо
        if data.get('is_premium'):
            text += f"⭐ Telegram Premium\n"
        if data.get('is_verified'):
            text += f"✅ Верифицирован\n"
        
        text += f"\n<i>Данные: FunStat API</i>"
        
        await event.edit(text, parse_mode='html')
        
    except Exception as e:
        logger.error(f"Ошибка в команде .история: {e}", exc_info=True)
        await event.edit(f"❌ Ошибка: {e}")


async def username_history_command(event: events.NewMessage.Event):
    """
    Команда .юзернейм_история
    Показывает историю изменений username
    """
    from utils.funstat import funstat_api
    
    if not funstat_api:
        await event.edit("❌ FunStat API не настроен")
        return
    
    user_id = await get_target_user_id(event)
    if not user_id:
        await event.edit("❌ Укажите пользователя")
        return
    
    await event.edit("🔍 Получаю историю username...")
    
    try:
        data = await funstat_api.get_username_history(user_id)
        
        if not data or not data.get('history'):
            await event.edit("❌ История username не найдена")
            return
        
        text = f"📱 <b>История Username</b>\n"
        text += f"🆔 ID: <code>{user_id}</code>\n\n"
        
        for record in data['history']:
            date = format_date(record.get('date', ''))
            username = record.get('username', 'неизвестно')
            text += f"@{username}\n"
            text += f"<i>{date}</i>\n\n"
        
        text += f"<i>Всего изменений: {len(data['history'])}</i>"
        
        await event.edit(text, parse_mode='html')
        
    except Exception as e:
        logger.error(f"Ошибка в .юзернейм_история: {e}")
        await event.edit(f"❌ Ошибка: {e}")


async def photo_history_command(event: events.NewMessage.Event):
    """
    Команда .фото_история
    Показывает историю фото профиля
    """
    from utils.funstat import funstat_api
    
    if not funstat_api:
        await event.edit("❌ FunStat API не настроен")
        return
    
    user_id = await get_target_user_id(event)
    if not user_id:
        await event.edit("❌ Укажите пользователя")
        return
    
    await event.edit("🔍 Получаю историю фото...")
    
    try:
        data = await funstat_api.get_photo_history(user_id)
        
        if not data or not data.get('history'):
            await event.edit("❌ История фото не найдена")
            return
        
        text = f"🖼 <b>История фото профиля</b>\n"
        text += f"🆔 ID: <code>{user_id}</code>\n\n"
        text += f"Всего изменений: {len(data['history'])}\n\n"
        
        for i, record in enumerate(data['history'][:10], 1):
            date = format_date(record.get('date', ''))
            photo_id = record.get('photo_id', 'N/A')
            text += f"{i}. {date}\n"
            text += f"   ID фото: <code>{photo_id}</code>\n"
        
        if len(data['history']) > 10:
            text += f"\n<i>...и еще {len(data['history']) - 10}</i>"
        
        await event.edit(text, parse_mode='html')
        
    except Exception as e:
        logger.error(f"Ошибка в .фото_история: {e}")
        await event.edit(f"❌ Ошибка: {e}")


async def search_phone_command(event: events.NewMessage.Event):
    """
    Команда .поиск_номер
    Поиск пользователя по номеру телефона
    Использование: .поиск_номер +79991234567
    """
    from utils.funstat import funstat_api
    
    if not funstat_api:
        await event.edit("❌ FunStat API не настроен")
        return
    
    text = event.message.text.strip()
    parts = text.split(maxsplit=1)
    
    if len(parts) < 2:
        await event.edit("❌ Использование: .поиск_номер +79991234567")
        return
    
    phone = parts[1].strip()
    await event.edit(f"🔍 Ищу пользователя по номеру {phone}...")
    
    try:
        data = await funstat_api.search_by_phone(phone)
        
        if not data or not data.get('user'):
            await event.edit(f"❌ Пользователь с номером {phone} не найден")
            return
        
        user = data['user']
        
        text = f"📱 <b>Результат поиска</b>\n\n"
        text += f"🆔 ID: <code>{user.get('id')}</code>\n"
        text += f"📝 Имя: {user.get('first_name', '')} {user.get('last_name', '')}\n"
        
        if user.get('username'):
            text += f"📱 Username: @{user['username']}\n"
        
        text += f"📞 Номер: <code>{phone}</code>\n"
        
        if user.get('bio'):
            text += f"📄 Био: {user['bio'][:100]}\n"
        
        if user.get('is_premium'):
            text += f"⭐ Telegram Premium\n"
        
        await event.edit(text, parse_mode='html')
        
    except Exception as e:
        logger.error(f"Ошибка в .поиск_номер: {e}")
        await event.edit(f"❌ Ошибка: {e}")


async def related_users_command(event: events.NewMessage.Event):
    """
    Команда .связи
    Показывает связанных пользователей
    """
    from utils.funstat import funstat_api
    
    if not funstat_api:
        await event.edit("❌ FunStat API не настроен")
        return
    
    user_id = await get_target_user_id(event)
    if not user_id:
        await event.edit("❌ Укажите пользователя")
        return
    
    await event.edit("🔍 Ищу связи...")
    
    try:
        data = await funstat_api.get_related_users(user_id)
        
        if not data or not data.get('related'):
            await event.edit("❌ Связанные пользователи не найдены")
            return
        
        text = f"🔗 <b>Связанные пользователи</b>\n"
        text += f"🆔 ID: <code>{user_id}</code>\n\n"
        
        for i, related in enumerate(data['related'][:15], 1):
            name = f"{related.get('first_name', '')} {related.get('last_name', '')}".strip()
            username = f"@{related['username']}" if related.get('username') else ""
            rel_type = related.get('relation_type', 'unknown')
            
            text += f"{i}. {name} {username}\n"
            text += f"   ID: <code>{related['id']}</code> | Тип: {rel_type}\n"
        
        if len(data['related']) > 15:
            text += f"\n<i>Всего: {len(data['related'])}</i>"
        
        await event.edit(text, parse_mode='html')
        
    except Exception as e:
        logger.error(f"Ошибка в .связи: {e}")
        await event.edit(f"❌ Ошибка: {e}")
