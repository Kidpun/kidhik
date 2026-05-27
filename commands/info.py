"""
Команда .инфо
Показывает расширенную информацию о пользователе
"""
import logging
from telethon import events
from telethon.tl.types import User
from datetime import datetime, timedelta
from utils.username_helper import get_user_username

logger = logging.getLogger(__name__)


def estimate_registration_date(user_id: int) -> str:
    """
    Вычисляет примерную дату регистрации аккаунта по Telegram ID
    Основано на последовательном росте ID с момента запуска Telegram
    """
    # Известные опорные точки (ID: timestamp)
    # Источник: анализ реальных данных и публичная информация
    reference_points = [
        (1, datetime(2013, 8, 1)),           # Запуск Telegram
        (10000000, datetime(2013, 11, 1)),   # ~10M - ноябрь 2013
        (50000000, datetime(2014, 3, 1)),    # ~50M - март 2014
        (100000000, datetime(2014, 8, 1)),   # ~100M - август 2014
        (200000000, datetime(2015, 4, 1)),   # ~200M - апрель 2015
        (300000000, datetime(2015, 11, 1)),  # ~300M - ноябрь 2015
        (400000000, datetime(2016, 5, 1)),   # ~400M - май 2016
        (500000000, datetime(2016, 10, 1)),  # ~500M - октябрь 2016
        (600000000, datetime(2017, 3, 1)),   # ~600M - март 2017
        (700000000, datetime(2017, 7, 1)),   # ~700M - июль 2017
        (800000000, datetime(2017, 11, 1)),  # ~800M - ноябрь 2017
        (900000000, datetime(2018, 3, 1)),   # ~900M - март 2018
        (1000000000, datetime(2018, 6, 1)),  # ~1B - июнь 2018
        (1500000000, datetime(2019, 6, 1)),  # ~1.5B - июнь 2019
        (2000000000, datetime(2020, 4, 1)),  # ~2B - апрель 2020
        (3000000000, datetime(2021, 6, 1)),  # ~3B - июнь 2021
        (4000000000, datetime(2022, 4, 1)),  # ~4B - апрель 2022
        (5000000000, datetime(2023, 1, 1)),  # ~5B - январь 2023
        (6000000000, datetime(2023, 9, 1)),  # ~6B - сентябрь 2023
        (7000000000, datetime(2024, 4, 1)),  # ~7B - апрель 2024
        (8000000000, datetime(2024, 11, 1)), # ~8B - ноябрь 2024
        (9000000000, datetime(2025, 5, 1)),  # ~9B - май 2025 (прогноз)
    ]
    
    # Находим ближайшие опорные точки
    if user_id < reference_points[0][0]:
        return reference_points[0][1].strftime("%d.%m.%Y")
    
    for i in range(len(reference_points) - 1):
        id1, date1 = reference_points[i]
        id2, date2 = reference_points[i + 1]
        
        if id1 <= user_id <= id2:
            # Линейная интерполяция между двумя точками
            id_range = id2 - id1
            date_range = (date2 - date1).total_seconds()
            position = (user_id - id1) / id_range
            
            estimated_timestamp = date1.timestamp() + (date_range * position)
            estimated_date = datetime.fromtimestamp(estimated_timestamp)
            
            return estimated_date.strftime("%d.%m.%Y")
    
    # Если ID больше последней известной точки - экстраполяция
    last_id, last_date = reference_points[-1]
    prev_id, prev_date = reference_points[-2]
    
    id_diff = last_id - prev_id
    date_diff = (last_date - prev_date).days
    rate = date_diff / id_diff  # дней на ID
    
    days_since = (user_id - last_id) * rate
    estimated_date = last_date + timedelta(days=days_since)
    
    return estimated_date.strftime("%d.%m.%Y")


async def info_command(event: events.NewMessage.Event):
    """
    Обработчик команды .инфо
    Показывает расширенную информацию о пользователе (ID, дата регистрации, био и т.д.)
    Использование: .инфо (реплай) или .инфо @username
    """
    try:
        target_user = None
        
        # Если есть ответ на сообщение - показываем инфо автора
        if event.message.is_reply:
            replied_msg = await event.get_reply_message()
            if replied_msg:
                target_user = await replied_msg.get_sender()
        else:
            # Проверяем аргументы команды
            text = event.message.text.strip()
            parts = text.split()
            
            if len(parts) > 1:
                arg = parts[1]
                
                # Проверяем, это ID (число) или username
                if arg.isdigit():
                    # Это ID
                    try:
                        user_id = int(arg)
                        target_user = await event.client.get_entity(user_id)
                    except Exception as e:
                        logger.debug(f"Error getting entity by ID {arg}: {e}")
                        await event.respond(f"❌ Пользователь с ID {arg} не найден")
                        return
                elif arg.startswith('@'):
                    # Это username
                    username = arg[1:]
                    try:
                        target_user = await event.client.get_entity(username)
                    except Exception as e:
                        logger.debug(f"Error getting entity by username {username}: {e}")
                        await event.respond(f"❌ Пользователь @{username} не найден")
                        return
                else:
                    # Возможно это username без @
                    try:
                        target_user = await event.client.get_entity(arg)
                    except Exception as e:
                        logger.debug(f"Error getting entity {arg}: {e}")
                        await event.respond(f"❌ Пользователь {arg} не найден")
                        return
            else:
                # Если просто .инфо без параметров - показываем себя
                target_user = await event.client.get_me()
        
        if not target_user:
            await event.respond("❌ Не удалось найти пользователя. Используй реплай или укажи @username")
            return
        
        # Проверяем, что это пользователь, а не канал/группа
        if not isinstance(target_user, User):
            await event.respond("❌ Это не пользователь")
            return
        
        # Получаем базовую информацию
        user_id = target_user.id
        first_name = getattr(target_user, 'first_name', '')
        last_name = getattr(target_user, 'last_name', '') or ''
        username = await get_user_username(event.client, target_user)
        
        full_name = f"{first_name} {last_name}".strip() or "Unknown"
        username_text = f"@{username}" if username else "нет"
        
        # Пытаемся получить полную информацию (включая био)
        try:
            full_user = await event.client.get_entity(user_id)
            bio = getattr(full_user, 'about', None) or "не указано"
        except Exception:
            bio = "не доступно"
        
        # Вычисляем примерную дату регистрации
        reg_date = estimate_registration_date(user_id)
        
        # Формируем сообщение
        text = f"👤 <b>Информация о пользователе</b>\n\n"
        text += f"📝 <b>Имя:</b> {full_name}\n"
        text += f"📱 <b>Username:</b> {username_text}\n"
        text += f"🆔 <b>ID:</b> <code>{user_id}</code>\n"
        text += f"📅 <b>Регистрация:</b> ~{reg_date}\n"
        
        # Дополнительная информация
        is_bot = getattr(target_user, 'bot', False)
        if is_bot:
            text += f"🤖 <b>Статус:</b> БОТ\n"
        
        is_verified = getattr(target_user, 'verified', False)
        if is_verified:
            text += f"✅ <b>Верифицирован</b>\n"
        
        is_premium = getattr(target_user, 'premium', False)
        if is_premium:
            text += f"⭐ <b>Telegram Premium</b>\n"
        
        is_scam = getattr(target_user, 'scam', False)
        if is_scam:
            text += f"⚠️ <b>SCAM (мошенник)</b>\n"
        
        is_fake = getattr(target_user, 'fake', False)
        if is_fake:
            text += f"⚠️ <b>FAKE (фейк)</b>\n"
        
        # Статус
        status = getattr(target_user, 'status', None)
        if status:
            status_type = type(status).__name__
            if status_type == 'UserStatusOnline':
                text += f"🟢 <b>Онлайн</b>\n"
            elif status_type == 'UserStatusOffline':
                try:
                    was_online = getattr(status, 'was_online', None)
                    if was_online:
                        now = datetime.now()
                        diff = now - was_online
                        if diff.days > 0:
                            text += f"🔴 <b>Был(а) онлайн:</b> {diff.days} дн. назад\n"
                        elif diff.seconds >= 3600:
                            hours = diff.seconds // 3600
                            text += f"🔴 <b>Был(а) онлайн:</b> {hours} ч. назад\n"
                        elif diff.seconds >= 60:
                            minutes = diff.seconds // 60
                            text += f"🔴 <b>Был(а) онлайн:</b> {minutes} мин. назад\n"
                        else:
                            text += f"🔴 <b>Был(а) онлайн:</b> только что\n"
                except Exception:
                    text += f"🔴 <b>Оффлайн</b>\n"
            elif status_type == 'UserStatusRecently':
                text += f"🟡 <b>Был(а) недавно</b>\n"
            elif status_type == 'UserStatusLastWeek':
                text += f"🟡 <b>Был(а) на неделе</b>\n"
            elif status_type == 'UserStatusLastMonth':
                text += f"🟡 <b>Был(а) в месяце</b>\n"
        
        # Биография (если есть)
        if bio != "не указано" and bio != "не доступно":
            # Обрезаем, если слишком длинное
            bio_short = bio[:200] + "..." if len(bio) > 200 else bio
            text += f"\n📄 <b>О себе:</b>\n{bio_short}"
        
        await event.respond(text, parse_mode='html')
        
    except Exception as e:
        logger.error(f"Ошибка в команде .инфо: {e}", exc_info=True)
        await event.respond(f"❌ Ошибка при получении информации: {e}")
