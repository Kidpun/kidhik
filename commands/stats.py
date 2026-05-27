"""
Команда .статистика - показывает статистику пользователей бота (только для владельца)
"""
import logging
from telethon import events, Button
from utils.database import get_active_users, get_all_user_ids
from config import OWNER_ID

logger = logging.getLogger(__name__)


async def stats_command(event: events.NewMessage.Event):
    """
    Команда .статистика - показывает статистику активных пользователей
    Доступна только для владельца бота
    """
    user_id = event.sender_id
    
    # Проверяем, что команду вызвал владелец
    # Если нет - просто молча игнорируем
    if user_id != OWNER_ID:
        return
    
    # Получаем статистику
    active_users = get_active_users()
    all_user_ids = get_all_user_ids()
    
    total_users = len(all_user_ids)
    active_count = len(active_users)
    
    # Формируем сообщение
    message = f"📊 **Статистика бота**\n\n"
    message += f"👥 Всего пользователей: **{total_users}**\n"
    message += f"✅ Активных: **{active_count}**\n"
    
    # Создаем кнопки
    buttons = [
        [Button.inline("👥 Список активных", b"stats_active")],
        [Button.inline("📋 Все пользователи", b"stats_all")],
        [Button.inline("📈 Подробная статистика", b"stats_detailed")],
    ]
    
    await event.respond(message, buttons=buttons)


async def handle_stats_callback(event, client):
    """
    Обработчик нажатий на кнопки статистики
    """
    user_id = event.sender_id
    
    # Проверяем, что кнопку нажал владелец
    # Если нет - просто молча игнорируем
    if user_id != OWNER_ID:
        await event.answer()
        return
    
    data = event.data
    
    if data == b"stats_active":
        # Показываем список активных пользователей
        active_users = get_active_users()
        
        if not active_users:
            await event.answer("Нет активных пользователей", alert=True)
            return
        
        message = "✅ **Активные пользователи:**\n\n"
        for idx, user in enumerate(active_users, 1):
            user_id_db, session_name, api_id, api_hash, device_model, system_version, app_version = user
            message += f"{idx}. ID: `{user_id_db}`\n"
            message += f"   📱 Сессия: {session_name}\n"
            if device_model:
                message += f"   💻 Устройство: {device_model}\n"
            if system_version:
                message += f"   🖥 Система: {system_version}\n"
            message += "\n"
        
        # Добавляем кнопку "Назад"
        buttons = [[Button.inline("◀️ Назад", b"stats_back")]]
        
        await event.edit(message, buttons=buttons)
    
    elif data == b"stats_all":
        # Показываем всех пользователей
        all_user_ids = get_all_user_ids()
        
        if not all_user_ids:
            await event.answer("Нет пользователей в базе", alert=True)
            return
        
        message = "📋 **Все пользователи в базе:**\n\n"
        message += f"Всего: **{len(all_user_ids)}** пользователей\n\n"
        
        # Разбиваем на колонки для компактности
        for idx, uid in enumerate(all_user_ids, 1):
            message += f"{idx}. `{uid}`\n"
            
            # Ограничиваем вывод, чтобы не превысить лимит сообщения
            if idx >= 50:
                remaining = len(all_user_ids) - 50
                if remaining > 0:
                    message += f"\n... и еще {remaining} пользователей"
                break
        
        # Добавляем кнопку "Назад"
        buttons = [[Button.inline("◀️ Назад", b"stats_back")]]
        
        await event.edit(message, buttons=buttons)
    
    elif data == b"stats_detailed":
        # Показываем подробную статистику
        active_users = get_active_users()
        all_user_ids = get_all_user_ids()
        
        total_users = len(all_user_ids)
        active_count = len(active_users)
        inactive_count = total_users - active_count
        
        # Собираем статистику по устройствам
        devices = {}
        systems = {}
        
        for user in active_users:
            user_id_db, session_name, api_id, api_hash, device_model, system_version, app_version = user
            
            if device_model:
                devices[device_model] = devices.get(device_model, 0) + 1
            
            if system_version:
                systems[system_version] = systems.get(system_version, 0) + 1
        
        message = "📈 **Подробная статистика:**\n\n"
        message += f"👥 Всего пользователей: **{total_users}**\n"
        message += f"✅ Активных: **{active_count}**\n"
        message += f"⏸ Неактивных: **{inactive_count}**\n\n"
        
        if devices:
            message += "💻 **Устройства:**\n"
            for device, count in sorted(devices.items(), key=lambda x: x[1], reverse=True):
                message += f"  • {device}: {count}\n"
            message += "\n"
        
        if systems:
            message += "🖥 **Системы:**\n"
            for system, count in sorted(systems.items(), key=lambda x: x[1], reverse=True):
                message += f"  • {system}: {count}\n"
        
        # Добавляем кнопку "Назад"
        buttons = [[Button.inline("◀️ Назад", b"stats_back")]]
        
        await event.edit(message, buttons=buttons)
    
    elif data == b"stats_back":
        # Возвращаемся к основному меню статистики
        active_users = get_active_users()
        all_user_ids = get_all_user_ids()
        
        total_users = len(all_user_ids)
        active_count = len(active_users)
        
        message = f"📊 **Статистика бота**\n\n"
        message += f"👥 Всего пользователей: **{total_users}**\n"
        message += f"✅ Активных: **{active_count}**\n"
        
        buttons = [
            [Button.inline("👥 Список активных", b"stats_active")],
            [Button.inline("📋 Все пользователи", b"stats_all")],
            [Button.inline("📈 Подробная статистика", b"stats_detailed")],
        ]
        
        await event.edit(message, buttons=buttons)
    
    # Подтверждаем обработку callback
    await event.answer()
