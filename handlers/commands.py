"""
Регистрация обработчиков команд для userbot
Работает во всех чатах через Telethon
Оптимизированная версия со словарем команд
"""
import logging
from telethon import events

# Импорты команд (прямые, чтобы избежать проблем с __init__)
from commands.otkat import otkat_command
from commands.troll import troll_command
from commands.snos import snos_command
from commands.music import music_command
from commands.stop import stop_command
from commands.stats import stats_command, handle_stats_callback
from commands.sglypa import sglypa_command
from commands.ignore import ignore_command
from commands.help import help_command
from commands.fact import fact_command
from commands.brainrot import brainrot_command
from commands.probiv import probiv_command
from commands.id import id_command
from commands.ping import ping_command
from commands.down import down_command
from commands.info import info_command
from commands.whoami import whoami_command
from commands.reactions import reactions_command, auto_react_to_message
from commands.coin import coin_command
from commands.article import article_command
from commands.catcher import toggle_catcher, check_catcher_handler

# Новые команды
from commands.fun import percent_command, type_command, who_command
from commands.translate import translate_command
from commands.download import download_command
from commands.video_note import video_note_command
from commands.quote import quote_command
from commands.spy import spy_command
from commands.shazam_cmd import shazam_command
from commands.network import ip_command, domain_command, whois_command
from commands.funstat_commands import (
    history_command, username_history_command, photo_history_command,
    search_phone_command, related_users_command
)
from commands.remind import remind_command
from commands.calc import calc_command

from handlers.messages import save_message_handler
from handlers.media import media_handler, deleted_message_handler, edited_message_handler
from config import BOT_TOKEN

logger = logging.getLogger(__name__)

# Словарь команд: 'команда': (функция, удалять_сообщение)
# should_delete=True -> Бот удаляет сообщение пользователя ПЕРЕД запуском функции
# should_delete=False -> Функция сама управляет сообщением (например, редактирует его)

SIMPLE_COMMANDS = {
    # Удаляемые (мгновенные или отправляют новое)
    ".откат": (otkat_command, True),
    ".троль": (troll_command, True),
    ".снос": (snos_command, True),
    ".музыка": (music_command, True),
    ".сглыпа": (sglypa_command, True),
    ".стоп": (stop_command, True),
    ".помощь": (help_command, True),
    ".монетка": (coin_command, True),
    ".статья": (article_command, True),
    ".факт": (fact_command, True),
    ".бреинрот": (brainrot_command, True),
    ".whoami": (whoami_command, True),
    ".статистика": (stats_command, True),
    
    # Не удаляемые (редактируемые или долгие)
    ".пинг": (ping_command, False),
    ".чек": (toggle_catcher, False),
    ".процент": (percent_command, False),
    ".тайп": (type_command, False),
    ".tr": (translate_command, False),
    ".dl": (download_command, False),
    ".круг": (video_note_command, False),
    ".цитата": (quote_command, False),
    ".шазам": (shazam_command, False),
    ".ip": (ip_command, False),
    ".домен": (domain_command, False),
    ".whois": (whois_command, False),
    ".calc": (calc_command, False),
}

# Команды, которые могут иметь аргументы (проверяем по первому слову)
PREFIX_COMMANDS = {
    ".игнор": (ignore_command, True),
    ".пробив": (probiv_command, True),
    ".id": (id_command, True),
    ".сбой": (down_command, False),
    ".down": (down_command, False),
    ".инфо": (info_command, False),
    ".реакции": (reactions_command, True),
    
    # Новые с аргументами
    ".кто": (who_command, False),
    ".слежка": (spy_command, False),
    
    ".напомни": (remind_command, False),

    # FunStat API команды (история изменений профилей)
    ".история": (history_command, False),
    ".юзернейм_история": (username_history_command, False),
    ".фото_история": (photo_history_command, False),
    ".поиск_номер": (search_phone_command, False),
    ".связи": (related_users_command, False),
}

def register_handlers(client, owner_id=None):
    """
    Регистрирует все обработчики команд и сообщений
    Работает во ВСЕХ чатах пользователя
    """
    me_id = owner_id
    
    async def get_me_id():
        nonlocal me_id
        if me_id is None:
            me = await client.get_me()
            me_id = me.id
        return me_id
    
    # Обработчик ВСЕХ сообщений (входящих и исходящих)
    @client.on(events.NewMessage())
    async def message_handler(event):
        """Обрабатывает все сообщения и команды"""
        try:
            # 0. Ловец чеков (работает всегда, если включен)
            try:
                await check_catcher_handler(event)
            except Exception as e:
                logger.error(f"Ошибка в catcher: {e}")

            current_me_id = await get_me_id()
            
            # Обработка медиа (1-view, таймеры)
            if event.message.media:
                try:
                    await media_handler(event, client, user_id=current_me_id)
                except Exception as e:
                    logger.error(f"Ошибка обработки медиа: {e}", exc_info=True)
            
            if not event.message.text:
                return
            
            text = event.message.text.strip()
            is_own = event.sender_id == current_me_id

            # Игнорируем сообщения в ЛС с ботом-менеджером
            manager_id = 0
            if BOT_TOKEN:
                try:
                    manager_id = int(BOT_TOKEN.split(':')[0])
                except: pass
                
            if manager_id and event.chat_id == manager_id:
                return
        except Exception as e:
            logger.error(f"Критическая ошибка в message_handler: {e}", exc_info=True)
            return  # Прерываем выполнение при критической ошибке

        # Обработка команд (только от себя)
        if is_own:
            cmd_key = text.split()[0].lower() if text else "" # Первое слово (.команда)
            
            # Проверяем, это вообще команда (начинается с точки)?
            if cmd_key.startswith('.'):
                # ПРИНУДИТЕЛЬНАЯ ПРОВЕРКА: клиент в карантине?
                from utils.instance_manager import instance_manager
                is_ready, seconds_left = instance_manager.is_client_ready(current_me_id)
                
                if not is_ready:
                    # Клиент еще в карантине, игнорируем команду
                    minutes_left = seconds_left // 60
                    seconds_left_display = seconds_left % 60
                    
                    warning_msg = (
                        f"⏳ <b>Карантин безопасности</b>\n\n"
                        f"Команды будут доступны через:\n"
                        f"<b>{minutes_left} мин {seconds_left_display} сек</b>\n\n"
                        f"🔒 Это защита от бана Telegram.\n"
                        f"Новые сессии должны \"прогреться\" перед активностью."
                    )
                    
                    try:
                        await event.reply(warning_msg, parse_mode='html')
                    except:
                        pass  # Если не удалось отправить, просто игнорируем
                    
                    logger.info(f"🚫 Команда {cmd_key} заблокирована для {current_me_id} (карантин: {seconds_left}с)")
                    return  # Прерываем обработку команды
                
                # 1. Проверка точных команд
                if text in SIMPLE_COMMANDS:
                    handler, should_delete = SIMPLE_COMMANDS[text]
                    logger.info(f"✅ {text} command detected from self!")
                    if should_delete:
                        try: 
                            await event.delete()
                        except Exception as e:
                            logger.debug(f"Не удалось удалить сообщение команды: {e}")
                    try:
                        await handler(event)
                    except Exception as e:
                        logger.error(f"Ошибка выполнения команды {text}: {e}", exc_info=True)
                        try:
                            await event.reply(f"❌ Ошибка выполнения команды: {e}")
                        except:
                            pass
                    return

                # 2. Проверка команд с аргументами (по первому слову)
                # Сначала проверяем точное совпадение ключа в SIMPLE (на всякий случай)
                if cmd_key in SIMPLE_COMMANDS:
                     handler, should_delete = SIMPLE_COMMANDS[cmd_key]
                     logger.info(f"✅ {cmd_key} command detected from self!")
                     if should_delete:
                        try: 
                            await event.delete()
                        except Exception as e:
                            logger.debug(f"Не удалось удалить сообщение команды: {e}")
                     try:
                         await handler(event)
                     except Exception as e:
                         logger.error(f"Ошибка выполнения команды {cmd_key}: {e}", exc_info=True)
                         try:
                             await event.reply(f"❌ Ошибка выполнения команды: {e}")
                         except:
                             pass
                     return

                if cmd_key in PREFIX_COMMANDS:
                    handler, should_delete = PREFIX_COMMANDS[cmd_key]
                    logger.info(f"✅ {cmd_key} command detected from self!")
                    if should_delete:
                        try: 
                            await event.delete()
                        except Exception as e:
                            logger.debug(f"Не удалось удалить сообщение команды: {e}")
                    try:
                        await handler(event)
                    except Exception as e:
                        logger.error(f"Ошибка выполнения команды {cmd_key}: {e}", exc_info=True)
                        try:
                            await event.reply(f"❌ Ошибка выполнения команды: {e}")
                        except:
                            pass
                    return
                
                # Если команда не найдена - логируем и уведомляем пользователя
                logger.warning(f"⚠️ Неизвестная команда: {cmd_key} (полный текст: {text})")
                # Не удаляем неизвестные команды, чтобы пользователь видел что он написал
                # Можно добавить подсказку (опционально)
                # await event.reply(f"❌ Команда {cmd_key} не найдена. Используйте .помощь для списка команд.")
        else:
            # Сохраняем чужие сообщения в кеш
            await save_message_handler(event, user_id=current_me_id)
            
            # Авто-реакции (если включены)
            await auto_react_to_message(event, client, current_me_id)
    
    # Обработчик удаленных сообщений
    @client.on(events.MessageDeleted())
    async def deleted_handler(event):
        try:
            current_me_id = await get_me_id()
            await deleted_message_handler(event, client, user_id=current_me_id)
        except Exception as e:
            logger.error(f"Ошибка в deleted_handler: {e}", exc_info=True)
    
    # Обработчик отредактированных сообщений
    @client.on(events.MessageEdited())
    async def edited_handler(event):
        try:
            current_me_id = await get_me_id()
            await edited_message_handler(event, client, user_id=current_me_id)
        except Exception as e:
            logger.error(f"Ошибка в edited_handler: {e}", exc_info=True)
    
    # Обработчик кнопок
    @client.on(events.CallbackQuery(pattern=b"stats_.*"))
    async def callback_handler(event):
        try:
            await handle_stats_callback(event, client)
        except Exception as e:
            logger.error(f"Ошибка в callback_handler: {e}", exc_info=True)

    logger.info("✅ Command handlers registered (optimized)")
