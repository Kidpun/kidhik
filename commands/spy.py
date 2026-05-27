"""
Команда .слежка <@user>
Отслеживает онлайн статус пользователей
"""
import asyncio
import logging
from datetime import datetime, timezone
from telethon import events
from telethon.tl.types import UserStatusOnline, UserStatusOffline

logger = logging.getLogger(__name__)

# Список отслеживаемых: {user_id: {'last_online': bool, 'name': str}}
SPY_LIST = {}
SPY_TASK = None

async def start_spy_task(client):
    global SPY_TASK
    if SPY_TASK is None or SPY_TASK.done():
        SPY_TASK = asyncio.create_task(spy_loop(client))

async def spy_loop(client):
    """Фоновая проверка статусов"""
    logger.info("🕵️‍♂️ Spy task started")
    while True:
        if not SPY_LIST:
            await asyncio.sleep(10)
            continue
            
        try:
            for user_id in list(SPY_LIST.keys()):
                try:
                    user = await client.get_entity(user_id)
                    is_online = isinstance(user.status, UserStatusOnline)
                    
                    # Если статус изменился
                    if is_online != SPY_LIST[user_id]['last_online']:
                        old_status = SPY_LIST[user_id]['last_online']
                        SPY_LIST[user_id]['last_online'] = is_online
                        name = SPY_LIST[user_id]['name']
                        
                        # Уведомляем об изменении статуса
                        try:
                            if is_online:
                                # Вход в сеть
                                await client.send_message(
                                    'me', 
                                    f"🕵️‍♂️ <b>Слежка:</b>\n"
                                    f"👤 <a href='tg://user?id={user_id}'>{name}</a> сейчас <b>ОНЛАЙН</b> 🟢",
                                    parse_mode='html'
                                )
                                logger.info(f"Spy: User {user_id} ({name}) is now ONLINE")
                            else:
                                # Выход из сети (опционально - можно закомментировать)
                                from datetime import datetime
                                now = datetime.now().strftime("%H:%M:%S")
                                await client.send_message(
                                    'me', 
                                    f"🕵️‍♂️ <b>Слежка:</b>\n"
                                    f"👤 <a href='tg://user?id={user_id}'>{name}</a> вышел(а) из сети 🔴\n"
                                    f"⏰ Время: {now}",
                                    parse_mode='html'
                                )
                                logger.info(f"Spy: User {user_id} ({name}) went OFFLINE")
                        except Exception as send_error:
                            logger.error(f"Failed to send spy notification: {send_error}")
                except Exception as e:
                    logger.error(f"Spy check error for {user_id}: {e}")
                    
        except Exception as e:
            logger.error(f"Spy loop error: {e}")
            
        await asyncio.sleep(15) # Проверка каждые 15 сек

async def spy_command(event: events.NewMessage.Event):
    """
    .слежка <@user> - Вкл/Выкл слежку за онлайном
    """
    args = event.message.text.split()
    target = None
    
    if len(args) > 1:
        target = args[1]
    else:
        reply = await event.get_reply_message()
        if reply:
            target = reply.sender_id
            
    if not target:
        # Показать список
        if not SPY_LIST:
            await event.edit("🕵️‍♂️ Список слежки пуст.")
        else:
            text = "🕵️‍♂️ <b>Список слежки:</b>\n"
            for uid, data in SPY_LIST.items():
                status = "🟢" if data['last_online'] else "🔴"
                text += f"{status} <a href='tg://user?id={uid}'>{data['name']}</a>\n"
            await event.edit(text, parse_mode='html')
        return

    try:
        user = await event.client.get_entity(target)
        user_id = user.id
        name = getattr(user, 'first_name', 'User')
        
        if user_id in SPY_LIST:
            del SPY_LIST[user_id]
            await event.edit(f"❌ Слежка за <b>{name}</b> выключена.", parse_mode='html')
        else:
            is_online = isinstance(user.status, UserStatusOnline)
            
            # Получаем информацию о статусе
            status_info = "🟢 <b>ОНЛАЙН</b>" if is_online else "🔴 <b>ОФФЛАЙН</b>"
            
            # Если оффлайн, пытаемся получить время последнего визита
            if not is_online and isinstance(user.status, UserStatusOffline):
                was_online = user.status.was_online
                if was_online:
                    from datetime import datetime, timezone
                    now = datetime.now(timezone.utc)
                    diff = now - was_online
                    
                    if diff.days > 0:
                        status_info += f"\n⏰ Был(а) в сети: {diff.days} дн. назад"
                    elif diff.seconds >= 3600:
                        hours = diff.seconds // 3600
                        status_info += f"\n⏰ Был(а) в сети: {hours} ч. назад"
                    elif diff.seconds >= 60:
                        minutes = diff.seconds // 60
                        status_info += f"\n⏰ Был(а) в сети: {minutes} мин. назад"
                    else:
                        status_info += f"\n⏰ Был(а) в сети: только что"
            
            SPY_LIST[user_id] = {
                'last_online': is_online,
                'name': name
            }
            
            # Запускаем задачу, если не запущена
            await start_spy_task(event.client)
            
            await event.edit(
                f"✅ Слежка за <b>{name}</b> включена.\n\n"
                f"📊 <b>Текущий статус:</b>\n{status_info}\n\n"
                f"💬 Уведомления будут приходить в Избранное.",
                parse_mode='html'
            )
            
    except Exception as e:
        logger.error(f"Spy command error: {e}", exc_info=True)
        await event.edit(f"❌ Ошибка: {e}")


