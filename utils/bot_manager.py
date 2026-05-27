import asyncio
import logging
import os
import re
import random
import json
import ssl
import time
import aiohttp
from pathlib import Path
from telethon import TelegramClient, Button
from telethon.errors import (
    SessionPasswordNeededError, 
    PhoneCodeInvalidError, 
    PhoneCodeExpiredError,
    PhoneNumberInvalidError,
    FloodWaitError,
    AuthRestartError
)
from utils.database import (
    add_user, add_api_to_pool, get_random_api, 
    is_global_enabled, set_global_enabled, get_all_user_ids,
    get_business_connections as get_db_business_connections
)
from config import (
    API_ID as DEFAULT_API_ID, 
    API_HASH as DEFAULT_API_HASH, 
    BOT_TOKEN,
    OWNER_ID
)

logger = logging.getLogger(__name__)
auth_states = {}

# Lock для предотвращения одновременного подключения клиентов (database is locked fix)
client_connect_lock = asyncio.Lock()

# Хранилище активных бизнес-подключений: {user_id: connection_id}
business_connections = {}

# Тексты
_facts = []
_troll_phrases = []

def load_text_file(filename):
    path = Path(__file__).parent.parent / 'text' / filename
    if path.exists():
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return [line.strip() for line in f.readlines() if line.strip()]
        except Exception as e:
            logger.error(f"Error loading {filename}: {e}")
    return []

def get_random_device():
    """55+ профилей устройств для обхода защиты"""
    devices = [
        ("iPhone 15 Pro Max", "iOS 17.5.1", "10.12.1"),
        ("Samsung Galaxy S24 Ultra", "Android 14", "10.5.2"),
        ("PC 64bit", "Windows 11", "4.16.2 x64"),
        ("MacBook Pro M3", "macOS 14.4.1", "4.15.0"),
        ("Xiaomi 14 Pro", "Android 14", "10.3.1"),
        ("Huawei Mate 60 Pro", "HarmonyOS 4.0", "10.2.5"),
        ("Google Pixel 8 Pro", "Android 14", "10.8.0"),
        ("iPad Pro M2", "iPadOS 17.4", "10.11.0"),
        ("Sony Xperia 1 V", "Android 13", "9.5.0"),
        ("OnePlus 12", "Android 14", "10.4.0"),
        ("Redmi Note 13 Pro", "Android 13", "9.9.5"),
        ("Poco F6 Pro", "Android 14", "10.2.8")
    ]
    return random.choice(devices)

# --- SAFE TASK WRAPPER ---
async def safe_task(coro, task_name="unknown"):
    """Оборачивает корутину для безопасной обработки ошибок"""
    try:
        await coro
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"Ошибка в задаче {task_name}: {e}", exc_info=True)

# --- BOT API HELPERS ---

async def bot_api_request(method, data=None, retries=3):
    if not BOT_TOKEN: return None
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    timeout = aiohttp.ClientTimeout(total=30, connect=10)
    
    for attempt in range(retries):
        try:
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                async with session.post(url, json=data) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    else:
                        # Пытаемся прочитать JSON с ошибкой
                        try:
                            error_json = await resp.json()
                            error_code = error_json.get('error_code')
                            description = error_json.get('description', '')
                            
                            # Для callback query игнорируем ошибки устаревших запросов
                            if method == 'answerCallbackQuery':
                                if error_code == 400 and ('too old' in description.lower() or 'timeout' in description.lower() or 'invalid' in description.lower()):
                                    logger.debug(f"Ignoring old callback query error: {description}")
                                    return None
                            
                            error_text = description or str(error_json)
                        except:
                            error_text = await resp.text()
                        
                        # Логируем только критические ошибки (не 400 для callback query)
                        if method != 'answerCallbackQuery' or error_code != 400:
                            logger.error(f"Bot API Error ({method}): status {resp.status}, {error_text}")
                        if attempt < retries - 1:
                            await asyncio.sleep(1 * (attempt + 1))  # Экспоненциальная задержка
                            continue
                        return None
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            error_str = str(e).lower()
            # Игнорируем "Session is closed" и таймауты - это нормально
            if 'session is closed' in error_str or 'timeout' in error_str:
                if attempt < retries - 1:
                    await asyncio.sleep(0.5 * (attempt + 1))
                    continue
                else:
                    return None
            # Логируем только критические ошибки
            if attempt == retries - 1:
                logger.error(f"Bot API Error ({method}): {e}")
            if attempt < retries - 1:
                await asyncio.sleep(1 * (attempt + 1))  # Экспоненциальная задержка
                continue
            return None
        except Exception as e:
            error_str = str(e).lower()
            if 'session is closed' in error_str or 'timeout' in error_str:
                return None
            logger.error(f"Bot API Error ({method}): {e}")
            return None
    return None

def prepare_keyboard(buttons):
    if not buttons: return None
    keyboard = []
    for row in buttons:
        new_row = []
        for btn in row:
            if isinstance(btn, dict):
                new_row.append(btn)
            elif hasattr(btn, 'text') and hasattr(btn, 'data'): # Telethon Button
                data = btn.data
                if isinstance(data, bytes):
                    data = data.decode('utf-8')
                new_row.append({'text': btn.text, 'callback_data': data})
        keyboard.append(new_row)
    return {'inline_keyboard': keyboard}

async def send_message(chat_id, text, buttons=None, parse_mode='HTML'):
    data = {'chat_id': chat_id, 'text': text, 'parse_mode': parse_mode}
    if buttons:
        data['reply_markup'] = prepare_keyboard(buttons)
    result = await bot_api_request('sendMessage', data)
    if result and not result.get('ok'):
        logger.error(f"send_message failed for chat {chat_id}: {result}")
    return result

async def edit_message(chat_id, message_id, text, buttons=None, parse_mode='HTML'):
    """Редактирует сообщение. Возвращает результат или None при ошибке."""
    try:
        data = {'chat_id': chat_id, 'message_id': message_id, 'text': text, 'parse_mode': parse_mode}
        if buttons:
            data['reply_markup'] = prepare_keyboard(buttons)
        result = await bot_api_request('editMessageText', data)
        if result and result.get('ok'):
            return result
        # Если не ok или None - возвращаем None (fallback отправит новое сообщение)
        return None
    except Exception as e:
        logger.debug(f"edit_message exception: {e}")
        return None

async def answer_callback(callback_query_id, text=None, show_alert=False):
    """
    Отвечает на callback query.
    Игнорирует ошибки для устаревших запросов.
    """
    data = {'callback_query_id': callback_query_id, 'show_alert': show_alert}
    if text:
        data['text'] = text
    try:
        result = await bot_api_request('answerCallbackQuery', data)
        # Проверяем, не является ли это ошибкой устаревшего запроса
        if result and not result.get('ok'):
            error_code = result.get('error_code')
            description = result.get('description', '')
            # Игнорируем ошибки устаревших запросов
            if error_code == 400 and ('too old' in description.lower() or 'timeout' in description.lower() or 'invalid' in description.lower()):
                logger.debug(f"Ignoring old callback query {callback_query_id}")
                return None
        return result
    except Exception as e:
        error_str = str(e).lower()
        # Игнорируем ошибки закрытой сессии и устаревших запросов
        if 'session is closed' in error_str or 'too old' in error_str or 'timeout' in error_str:
            logger.debug(f"Ignoring callback query error: {e}")
            return None
        logger.warning(f"Error answering callback query: {e}")
        return None

async def send_business_message(chat_id, connection_id, text):
    data = {
        'business_connection_id': connection_id,
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML'
    }
    return await bot_api_request('sendMessage', data)

async def delete_business_message(chat_id, message_id):
    """Удаление сообщения через Bot API"""
    data = {'chat_id': chat_id, 'message_id': message_id}
    return await bot_api_request('deleteMessage', data)

async def copy_message(chat_id, from_chat_id, message_id, caption=None):
    """Копирование сообщения через Bot API"""
    data = {
        'chat_id': chat_id,
        'from_chat_id': from_chat_id,
        'message_id': message_id
    }
    if caption:
        data['caption'] = caption
        data['parse_mode'] = 'HTML'
    return await bot_api_request('copyMessage', data)

# --- BUSINESS LOGIC ---

async def handle_business_connection_update(data):
    connection_id = data.get('id')
    user_data = data.get('user', {})
    user_id = user_data.get('id')
    is_enabled = data.get('is_enabled', False)
    first_name = user_data.get('first_name', 'Пользователь')
    
    logger.info(f"🔗 Бизнес-подключение: user_id={user_id}, connection_id={connection_id}, enabled={is_enabled}")
    
    if is_enabled:
        business_connections[user_id] = connection_id
        logger.info(f"✅ Бизнес-подключение добавлено: user_id={user_id}, connection_id={connection_id}")
        
        # Сохраняем пользователя в БД (как бизнес)
        phone = f"business_{user_id}"
        api_id, api_hash = get_random_api(DEFAULT_API_ID, DEFAULT_API_HASH)
        add_user(user_id, phone, f"user_{user_id}", api_id, api_hash, None, None, None, is_business=True, business_connection_id=connection_id)
        
        logger.info(f"✅ Бизнес-аккаунт {user_id} ({first_name}) подключен через Bot API")
        
        # Уведомляем пользователя
        try:
            await send_message(
                user_id,
                f"🎉 <b>Бизнес-аккаунт {first_name} успешно подключен!</b>\n\n"
                "✅ Все команды теперь доступны через Bot API.\n\n"
                "💡 <b>Важно:</b> Убедитесь, что все разрешения в 'Управление сообщениями' включены."
            )
        except Exception as e:
            logger.error(f"Error sending business connection notification to {user_id}: {e}")
    else:
        if user_id in business_connections:
            del business_connections[user_id]
            logger.info(f"❌ Бизнес-подключение удалено: user_id={user_id}")
        logger.info(f"❌ Бизнес-аккаунт {user_id} отключен")
        from utils.instance_manager import instance_manager
        if user_id in instance_manager.clients:
            await instance_manager.stop_client(user_id)

async def handle_business_message(message_data, is_edited=False):
    user_id = message_data.get('from', {}).get('id')
    chat_id = message_data.get('chat', {}).get('id')
    message_id = message_data.get('message_id')
    text = message_data.get('text', '').strip()
    connection_id = message_data.get('business_connection_id')
    
    if not user_id or not connection_id: return

    # Log all business messages for debugging
    logger.info(f"📨 Business Message from {user_id}: '{text}' (conn: {connection_id})")
    
    owner_id = None
    for uid, conn_id in business_connections.items():
        if conn_id == connection_id:
            owner_id = uid
            break
            
    if not owner_id: return
    is_own = (user_id == owner_id)

    # КОМАНДЫ (ТОЛЬКО ДЛЯ ВЛАДЕЛЬЦА)
    if is_own and text.startswith('.'):
        response_text = None

        if text == '.тест':
            if message_id: await delete_business_message(chat_id, message_id)
            response_text = "✅ <b>Бот успешно подключен и работает!</b>"
        
        elif text == '.музыка':
            from utils.spotify import spotify_manager
            track = await spotify_manager.get_current_track(owner_id)
            if track: response_text = f"🎵 <b>Сейчас играет:</b>\n{track['text']}"
            else: response_text = "🔇 Сейчас ничего не играет"
        
        elif text == '.id':
            response_text = f"🆔 <b>Chat ID:</b> <code>{chat_id}</code>\n👤 <b>User ID:</b> <code>{user_id}</code>"

        elif text == '.пинг':
            import time
            start = time.time()
            await send_business_message(chat_id, connection_id, "🏓 <b>Понг!</b>")
            end = time.time()
            ping = (end - start) * 1000
            await send_business_message(chat_id, connection_id, f"📶 <b>Ping:</b> {ping:.2f}ms")
            return

        elif text == '.факт':
            global _facts
            if not _facts: _facts = load_text_file('facts.txt')
            if _facts:
                response_text = f"💡 <b>Факт:</b>\n{random.choice(_facts)}"
            else:
                response_text = "❌ Факты не найдены."

        elif text.startswith('.тролль'):
            global _troll_phrases
            if not _troll_phrases: _troll_phrases = load_text_file('troll.txt')
            count = 1
            parts = text.split()
            if len(parts) > 1 and parts[1].isdigit():
                count = int(parts[1])
                if count > 5: count = 5
            
            if _troll_phrases:
                for _ in range(count):
                    phrase = random.choice(_troll_phrases)
                    await send_business_message(chat_id, connection_id, phrase)
                    await asyncio.sleep(0.5)
                return
            else:
                response_text = "❌ Фразы не найдены."

        elif text == '.инфо':
            try:
                chat_info = await bot_api_request('getChat', {'chat_id': chat_id})
                if chat_info and chat_info.get('ok'):
                    ci = chat_info['result']
                    first = ci.get('first_name', '')
                    last = ci.get('last_name', '')
                    username = ci.get('username', 'Нет')
                    bio = ci.get('bio', 'Нет')
                    response_text = (
                        f"👤 <b>Информация о пользователе:</b>\n\n"
                        f"🆔 ID: <code>{ci['id']}</code>\n"
                        f"👤 Имя: {first} {last}\n"
                        f"🌐 Username: @{username}\n"
                        f"📝 Bio: {bio}\n"
                    )
                else:
                    response_text = "❌ Не удалось получить информацию."
            except Exception as e:
                response_text = f"❌ Ошибка: {e}"

        elif text == '.помощь':
            response_text = (
                "📖 <b>Список команд (Бизнес-мод)</b>\n\n"
                "🚀 <b>Развлечения:</b>\n"
                "• <code>.факт</code> - Случайный факт\n"
                "• <code>.тролль [кол-во]</code> - Отправить тролль-фразы\n"
                "• <code>.монетка</code> - Бросить монетку\n"
                "• <code>.статья</code> - Статья УК РФ\n\n"
                "🛠 <b>Утилиты:</b>\n"
                "• <code>.инфо</code> - Информация о собеседнике\n"
                "• <code>.пинг</code> - Проверка скорости\n"
                "• <code>.id</code> - ID чата и юзера\n"
                "• <code>.тест</code> - Тест работы\n"
                "• <code>.музыка</code> - Spotify трек\n\n"
                "⚠️ Это демо-версия бота."
            )
        elif text == '.монетка':
            import random
            result = random.choice(['Орел', 'Решка'])
            response_text = f"🪙 <b>Монетка:</b> {result}"
        elif text == '.статья':
            from commands.article import load_articles, _articles
            if not _articles: load_articles()
            if _articles:
                import random
                num, title = random.choice(_articles)
                response_text = f"Ваша статья УК РФ - {num} {title}"
            else:
                response_text = "❌ Статьи недоступны"

        if response_text:
            await send_business_message(chat_id, connection_id, response_text)

# --- HANDLERS ---

async def handle_start(chat_id, user_id):
    logger.info(f"🚀 /start команда от пользователя {user_id}")
    try:
        import time
        if user_id in auth_states:
            del auth_states[user_id]
        
        auth_states[user_id] = {'step': 'choose_auth', 'timestamp': time.time()}
        buttons = [
            [Button.inline("Подключить по номеру телефона", b"by_phone")],
            [Button.inline("Подключить через бизнес-мод", b"by_business")]
        ]
        text = (
            "Выберите способ подключения бота к своему аккаунту:\n\n"
            "1️⃣ По номеру телефона\n2️⃣ Через бизнес-мод (Business)"
        )
        result = await send_message(chat_id, text, buttons=buttons)
        if result and not result.get('ok'):
            logger.error(f"Failed to send start message: {result}")
    except Exception as e:
        logger.error(f"Error in handle_start for user {user_id}: {e}", exc_info=True)

async def handle_admin(chat_id, user_id):
    logger.info(f"🔍 /admin команда от пользователя {user_id}")
    if user_id != OWNER_ID:
        return

    enabled = is_global_enabled()
    status = "🟢 ВКЛЮЧЕН" if enabled else "🔴 ВЫКЛЮЧЕН"
    buttons = [
        [Button.inline(f"Бот: {'ВЫКЛЮЧИТЬ' if enabled else 'ВКЛЮЧИТЬ'}", b"toggle_bot")],
        [Button.inline("📢 Сделать рассылку", b"start_broadcast")],
        [Button.inline("🔄 Перезапустить всех", b"restart_all")]
    ]
    await send_message(chat_id, f"🛠 <b>Админ-панель KidHik</b>\n\nСтатус системы: {status}", buttons=buttons)

async def handle_message_update(message):
    chat_id = message.get('chat', {}).get('id')
    user_id = message.get('from', {}).get('id')
    text = message.get('text', '').strip()
    
    if not text or not chat_id: return
    
    # Команды
    if text == '/start':
        await handle_start(chat_id, user_id)
        return
    elif text == '/admin':
        await handle_admin(chat_id, user_id)
        return
    
    # Обработка ввода (телефон, код, пароль)
    state = auth_states.get(user_id)
    if not state: return
    
    step = state.get('step')
    
    if step == 'enter_phone':
        phone = text.replace(' ', '').replace('-', '')
        state['phone'] = phone
        state['step'] = 'wait_code'
        
        # Получаем данные API
        api_id, api_hash = get_random_api(DEFAULT_API_ID, DEFAULT_API_HASH)
        
        # Создаем клиента Telethon для авторизации
        session_name = f"user_{user_id}"
        
        # Получаем параметры устройства
        dev_model, sys_ver, app_ver = state.get('device_params') or get_random_device()
        
        # Уникальный путь для сессии (создаем директорию если нужно)
        # Используем sessions_local для совместимости с instance_manager
        base_dir = Path(__file__).parent.parent
        sessions_dir = base_dir / "sessions_local"
        sessions_dir.mkdir(exist_ok=True)
        session_path = str(sessions_dir / f"{session_name}.session")
        client = TelegramClient(session_path, api_id, api_hash, 
                              device_model=dev_model,
                              system_version=sys_ver,
                              app_version=app_ver)
        state['client'] = client
        
        try:
            # Подключаемся к клиенту
            if not client.is_connected():
                await client.connect()
            
            # Проверяем подключение перед отправкой кода
            if not client.is_connected():
                await client.connect()
            
            # Отправляем запрос на код (с повторными попытками при AuthRestartError)
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    sent = await client.send_code_request(phone)
                    state['phone_code_hash'] = sent.phone_code_hash
                    state['api_id'] = api_id
                    state['api_hash'] = api_hash
                    await send_message(chat_id, "📲 <b>Введите код из Telegram:</b>\n\n🚨 <b>ОБЯЗАТЕЛЬНО с пробелами/разделителями!</b>\n\n✅ Правильно:\n• <code>1 2 3 4 5</code>\n• <code>12-34-5</code>\n• <code>1.2.3.4.5</code>\n\n❌ НЕЛЬЗЯ:\n• <code>12345</code> (слитно - Telegram забанит!)")
                    break
                except AuthRestartError:
                    logger.warning(f"AuthRestartError при отправке кода (попытка {attempt + 1}/{max_retries}), переподключаемся...")
                    # Переподключаемся при AuthRestartError
                    try:
                        if client.is_connected():
                            await client.disconnect()
                    except:
                        pass
                    await asyncio.sleep(1)
                    await client.connect()
                    if attempt == max_retries - 1:
                        raise
                except ConnectionError as ce:
                    logger.warning(f"ConnectionError при отправке кода (попытка {attempt + 1}/{max_retries}), переподключаемся...")
                    # Переподключаемся при ConnectionError
                    try:
                        if client.is_connected():
                            await client.disconnect()
                    except:
                        pass
                    await asyncio.sleep(1)
                    await client.connect()
                    if attempt == max_retries - 1:
                        raise
        except Exception as e:
            logger.error(f"Auth error: {e}", exc_info=True)
            # Закрываем клиент при ошибке
            try:
                if client.is_connected():
                    await client.disconnect()
            except:
                pass
            error_msg = str(e)
            if "AuthRestartError" in error_msg or "Restart the authorization" in error_msg:
                await send_message(chat_id, "❌ <b>Ошибка авторизации Telegram</b>\n\nTelegram просит перезапустить процесс авторизации. Попробуйте еще раз через несколько секунд.")
            elif "ConnectionError" in error_msg or "disconnected" in error_msg.lower():
                await send_message(chat_id, "❌ <b>Ошибка подключения</b>\n\nНе удалось подключиться к Telegram. Проверьте интернет-соединение и попробуйте еще раз.")
            else:
                await send_message(chat_id, f"❌ Ошибка: {e}")
            if user_id in auth_states:
                del auth_states[user_id]
            
    elif step == 'wait_code':
        # ВАЖНО: Telegram требует чтобы код вводился с разделителями (антибот мера)
        # Проверяем что в тексте есть пробелы, тире или другие символы
        has_separator = bool(re.search(r'[^0-9]', text))
        
        if not has_separator:
            # Код введен слитно (12345) - ОТКЛОНЯЕМ!
            await send_message(
                chat_id, 
                "❌ <b>КОД ДОЛЖЕН БЫТЬ С РАЗДЕЛИТЕЛЯМИ!</b>\n\n"
                "Telegram банит за ввод кода слитно (это признак бота).\n\n"
                "✅ Введите код правильно:\n"
                "• <code>1 2 3 4 5</code> (с пробелами)\n"
                "• <code>12-34-5</code> (с тире)\n"
                "• <code>1.2.3.4.5</code> (с точками)"
            )
            return
        
        # Очищаем код от всех символов кроме цифр
        code = re.sub(r'[^0-9]', '', text)
        
        if not code:
            await send_message(chat_id, "❌ Код должен содержать цифры. Попробуйте еще раз.")
            return
        
        client = state.get('client')
        phone = state.get('phone')
        phone_code_hash = state.get('phone_code_hash')
        
        if not client:
            await send_message(chat_id, "❌ <b>Ошибка:</b> Клиент авторизации не найден. Начните процесс заново.")
            if user_id in auth_states:
                del auth_states[user_id]
            return
        
        try:
            # Проверяем подключение перед входом
            if not client.is_connected():
                logger.info(f"Клиент отключен, переподключаемся для пользователя {user_id}")
                await client.connect()
            
            await client.sign_in(phone, code, phone_code_hash=phone_code_hash)
            # Успех - закрываем клиент авторизации
            try:
                await client.disconnect()
            except:
                pass
            
            dev_model, sys_ver, app_ver = state.get('device_params') or get_random_device()
            add_user(user_id, phone, f"user_{user_id}", state['api_id'], state['api_hash'],
                     device_model=dev_model, system_version=sys_ver, app_version=app_ver)
            await send_message(chat_id, "✅ <b>Авторизация успешна!</b>\nБот запущен.")
            del auth_states[user_id]
            
            # Небольшая задержка для освобождения блокировок БД
            await asyncio.sleep(0.5)
            
            # Запускаем инстанс в фоне (не блокируем выполнение)
            from utils.instance_manager import instance_manager
            asyncio.create_task(instance_manager.start_client(user_id, f"user_{user_id}", state['api_id'], state['api_hash'],
                                              device_model=dev_model, system_version=sys_ver, app_version=app_ver))
            
            # Отправляем финальное сообщение с рекомендациями
            await send_message(
                chat_id,
                "✅ <b>Авторизация завершена!</b>\n\n"
                f"🔧 Устройство: <code>{dev_name}</code>\n\n"
                "⏳ <b>КАРАНТИН БЕЗОПАСНОСТИ: 5 МИНУТ</b>\n\n"
                "🔒 Команды будут заблокированы первые 5 минут.\n"
                "Это защита от бана Telegram за подозрительную активность.\n\n"
                "💡 Через 5 минут используйте /help для списка команд"
            )
            
            # Очищаем состояние авторизации
            if user_id in auth_states:
                del auth_states[user_id]
            
        except SessionPasswordNeededError:
            state['step'] = 'wait_password'
            await send_message(chat_id, "🔐 <b>Введите пароль 2FA:</b>")
        except PhoneCodeInvalidError:
            await send_message(chat_id, "❌ <b>Неверный код</b>\n\nКод подтверждения неверный. Попробуйте еще раз или начните процесс заново.")
        except PhoneCodeExpiredError:
            await send_message(chat_id, "❌ <b>Код истек</b>\n\nКод подтверждения истек. Начните процесс авторизации заново.")
            if user_id in auth_states:
                del auth_states[user_id]
        except (ConnectionError, AuthRestartError) as e:
            logger.error(f"Ошибка подключения при авторизации пользователя {user_id}: {e}", exc_info=True)
            # Переподключаемся и просим повторить
            try:
                if client.is_connected():
                    await client.disconnect()
                await asyncio.sleep(1)
                await client.connect()
                await send_message(chat_id, "⚠️ <b>Проблема с подключением</b>\n\nПопробуйте ввести код еще раз.")
            except:
                await send_message(chat_id, "❌ <b>Ошибка подключения</b>\n\nНе удалось подключиться к Telegram. Начните процесс авторизации заново.")
                if user_id in auth_states:
                    del auth_states[user_id]
        except Exception as e:
            logger.error(f"Ошибка при авторизации пользователя {user_id}: {e}", exc_info=True)
            # Закрываем клиент при ошибке
            try:
                if client and client.is_connected():
                    await client.disconnect()
            except:
                pass
            error_msg = str(e)
            if "disconnected" in error_msg.lower():
                await send_message(chat_id, "❌ <b>Ошибка подключения</b>\n\nКлиент отключился. Начните процесс авторизации заново.")
            else:
                await send_message(chat_id, f"❌ Ошибка: {e}")
            if user_id in auth_states:
                del auth_states[user_id]
            
    elif step == 'wait_password':
        password = text
        client = state.get('client')
        
        if not client:
            await send_message(chat_id, "❌ <b>Ошибка:</b> Клиент авторизации не найден. Начните процесс заново.")
            if user_id in auth_states:
                del auth_states[user_id]
            return
        
        try:
            # Проверяем подключение перед входом
            if not client.is_connected():
                logger.info(f"Клиент отключен, переподключаемся для пользователя {user_id} (2FA)")
                await client.connect()
            
            await client.sign_in(password=password)
            # Успех - закрываем клиент авторизации
            try:
                await client.disconnect()
            except:
                pass
            
            dev_model, sys_ver, app_ver = state.get('device_params') or get_random_device()
            dev_name = state.get('device_name', 'Неизвестно')
            add_user(user_id, state['phone'], f"user_{user_id}", state['api_id'], state['api_hash'],
                     device_model=dev_model, system_version=sys_ver, app_version=app_ver)
            
            # Очищаем состояние авторизации
            del auth_states[user_id]
            
            # Небольшая задержка для освобождения блокировок БД
            await asyncio.sleep(0.5)
            
            # Запускаем инстанс в фоне (не блокируем выполнение)
            from utils.instance_manager import instance_manager
            asyncio.create_task(instance_manager.start_client(user_id, f"user_{user_id}", state['api_id'], state['api_hash'],
                                              device_model=dev_model, system_version=sys_ver, app_version=app_ver))
            
            # Отправляем финальное сообщение с рекомендациями (для 2FA тоже)
            await send_message(
                chat_id,
                "✅ <b>Авторизация завершена!</b>\n\n"
                f"🔧 Устройство: <code>{dev_name}</code>\n\n"
                "⏳ <b>КАРАНТИН БЕЗОПАСНОСТИ: 5 МИНУТ</b>\n\n"
                "🔒 Команды будут заблокированы первые 5 минут.\n"
                "Это защита от бана Telegram за подозрительную активность.\n\n"
                "💡 Через 5 минут используйте /help для списка команд"
            )
        except (ConnectionError, AuthRestartError) as e:
            logger.error(f"Ошибка подключения при авторизации пользователя {user_id} (2FA): {e}", exc_info=True)
            # Переподключаемся и просим повторить
            try:
                if client.is_connected():
                    await client.disconnect()
                await asyncio.sleep(1)
                await client.connect()
                await send_message(chat_id, "⚠️ <b>Проблема с подключением</b>\n\nПопробуйте ввести пароль еще раз.")
            except:
                await send_message(chat_id, "❌ <b>Ошибка подключения</b>\n\nНе удалось подключиться к Telegram. Начните процесс авторизации заново.")
                if user_id in auth_states:
                    del auth_states[user_id]
        except Exception as e:
            logger.error(f"Ошибка при авторизации пользователя {user_id} (2FA): {e}", exc_info=True)
            # Закрываем клиент при ошибке
            try:
                if client and client.is_connected():
                    await client.disconnect()
            except:
                pass
            error_msg = str(e)
            if "disconnected" in error_msg.lower():
                await send_message(chat_id, "❌ <b>Ошибка подключения</b>\n\nКлиент отключился. Начните процесс авторизации заново.")
            elif "password" in error_msg.lower() or "invalid" in error_msg.lower():
                await send_message(chat_id, "❌ <b>Неверный пароль</b>\n\nПароль 2FA неверный. Попробуйте еще раз.")
            else:
                await send_message(chat_id, f"❌ Ошибка: {e}")
            if user_id in auth_states:
                del auth_states[user_id]

async def handle_callback_query(callback):
    chat_id = callback.get('message', {}).get('chat', {}).get('id')
    user_id = callback.get('from', {}).get('id')
    data_raw = callback.get('data')
    callback_id = callback.get('id')
    message_id = callback.get('message', {}).get('message_id')
    
    if not data_raw or not user_id: 
        logger.debug(f"Empty callback query data or user_id: data={data_raw}, user_id={user_id}")
        return
    
    # Декодируем данные callback query (могут быть bytes или строка)
    if isinstance(data_raw, bytes):
        data = data_raw.decode('utf-8')
    else:
        data = str(data_raw)
    
    logger.debug(f"📱 Callback query from {user_id}: data='{data}'")
    
    # Отвечаем на callback query (игнорируем ошибки для старых запросов)
    try:
        await answer_callback(callback_id)
    except Exception as e:
        # Игнорируем ошибки устаревших callback query
        error_str = str(e).lower()
        if 'too old' not in error_str and 'timeout' not in error_str and 'session is closed' not in error_str:
            logger.warning(f"Error answering callback query: {e}")
    
    # Обработка admin команд
    if data == 'toggle_bot':
        if user_id != OWNER_ID: return
        try:
            current = is_global_enabled()
            set_global_enabled(not current)
            status = "🟢 ВКЛЮЧЕН" if not current else "🔴 ВЫКЛЮЧЕН"
            await send_message(chat_id, f"Система переключена: {status}")
        except Exception as e:
            logger.error(f"Ошибка toggle_bot: {e}", exc_info=True)
            await send_message(chat_id, f"❌ Ошибка: {e}")
        return
        
    elif data == 'start_broadcast':
        if user_id != OWNER_ID: return
        await send_message(chat_id, "📢 Рассылка начата...")
        users = get_all_user_ids()
        count = 0
        failed = 0
        blocked = 0
        
        # Запускаем рассылку в фоне чтобы не блокировать бота
        async def do_broadcast():
            nonlocal count, failed, blocked
            for uid in users:
                try:
                    result = await send_message(uid, "📢 <b>Важное обновление!</b>\nБот был обновлен.")
                    if result and result.get('ok'):
                        count += 1
                    else:
                        # Проверяем причину ошибки
                        error_desc = result.get('description', '') if result else ''
                        if 'blocked' in error_desc.lower() or 'forbidden' in error_desc.lower():
                            blocked += 1
                            logger.info(f"User {uid} заблокировал бота")
                        else:
                            failed += 1
                            logger.warning(f"Не удалось отправить сообщение пользователю {uid}: {error_desc}")
                    # Задержка для избежания FloodWait
                    await asyncio.sleep(0.5)
                except FloodWaitError as e:
                    # Если словили FloodWait - ждем требуемое время
                    logger.warning(f"FloodWait: ждем {e.seconds} секунд")
                    await asyncio.sleep(e.seconds)
                    # Повторная попытка
                    try:
                        result = await send_message(uid, "📢 <b>Важное обновление!</b>\nБот был обновлен.")
                        if result and result.get('ok'):
                            count += 1
                    except Exception as retry_err:
                        failed += 1
                        logger.error(f"Повторная ошибка для {uid}: {retry_err}")
                except Exception as e:
                    failed += 1
                    logger.error(f"Ошибка рассылки пользователю {uid}: {e}")
            
            # Отправляем итоговый отчет
            report = (
                f"✅ <b>Рассылка завершена!</b>\n\n"
                f"📤 Успешно отправлено: {count}\n"
                f"❌ Ошибок: {failed}\n"
                f"🚫 Заблокировали бота: {blocked}\n"
                f"📊 Всего пользователей: {len(users)}"
            )
            await send_message(chat_id, report)
        
        # Запускаем в фоне
        try:
            asyncio.create_task(safe_task(do_broadcast(), "broadcast"))
            await send_message(chat_id, f"⏳ Рассылка запущена ({len(users)} пользователей)...\nОтчет придет после завершения.")
        except Exception as e:
            logger.error(f"Ошибка запуска рассылки: {e}", exc_info=True)
            await send_message(chat_id, f"❌ Ошибка запуска рассылки: {e}")
        return
        
    elif data == 'restart_all':
        if user_id != OWNER_ID: return
        try:
            await send_message(chat_id, "⏳ Перезапуск всех клиентов...")
            from utils.instance_manager import instance_manager
            await instance_manager.restart_all()
            await send_message(chat_id, "✅ Все клиенты перезапущены!")
        except Exception as e:
            logger.error(f"Ошибка перезапуска клиентов: {e}", exc_info=True)
            await send_message(chat_id, f"❌ Ошибка перезапуска: {e}")
        return
        
    # AUTH FLOW
    try:
        state = auth_states.get(user_id)
        logger.debug(f"Callback query state for user {user_id}: state={state}, data='{data}'")
        
        # Если состояние не найдено, но это кнопки авторизации - создаем состояние заново
        if not state and data in ['by_phone', 'by_business', 'business_confirmed', 'check_business', 'phone_warning_ok', 'dev_iphone', 'dev_android', 'dev_pc', 'dev_random']:
            logger.info(f"State not found for user {user_id}, creating new state for callback '{data}'")
            import time
            # Определяем начальный шаг в зависимости от callback
            if data == 'business_confirmed':
                auth_states[user_id] = {'step': 'by_business_confirm', 'timestamp': time.time()}
            elif data == 'check_business':
                auth_states[user_id] = {'step': 'check_business', 'timestamp': time.time()}
            elif data == 'phone_warning_ok':
                auth_states[user_id] = {'step': 'phone_warning', 'timestamp': time.time()}
            elif data in ['dev_iphone', 'dev_android', 'dev_pc', 'dev_random']:
                auth_states[user_id] = {'step': 'choose_device', 'timestamp': time.time()}
            else:
                auth_states[user_id] = {'step': 'choose_auth', 'timestamp': time.time()}
            state = auth_states[user_id]
        
        if not state:
            # Если состояния нет и это не auth callback - игнорируем
            logger.debug(f"No auth state for user {user_id}, callback data: {data}")
            return
        
        step = state.get('step')
        logger.info(f"Processing callback: user={user_id}, step='{step}', data='{data}'")
        if step == 'choose_auth':
            if data == 'by_phone':
                state['step'] = 'phone_warning'
                text = (
                    "⚠️ <b>Предупреждение безопасности</b>\n\n"
                    "Вы собираетесь подключить бота через номер телефона.\n"
                    "Если страна вашего номера отличается от страны сервера (Россия), Telegram может заблокировать сессию.\n\n"
                    "Мы попытаемся замаскировать бота под обычный телефон, чтобы снизить риски."
                )
                buttons = [[Button.inline("Я понимаю, продолжить", b"phone_warning_ok")]]
                # Пытаемся отредактировать, если не получилось - отправляем новое
                if message_id:
                    try:
                        result = await edit_message(chat_id, message_id, text, buttons=buttons)
                        if not result:
                            await send_message(chat_id, text, buttons=buttons)
                    except Exception as e:
                        logger.debug(f"Error editing message, sending new: {e}")
                        await send_message(chat_id, text, buttons=buttons)
                else:
                    await send_message(chat_id, text, buttons=buttons)
                    
            elif data == 'by_business':
                logger.info(f"User {user_id} chose business mode, setting step to 'by_business_confirm'")
                state['step'] = 'by_business_confirm'
                # Сохраняем состояние явно
                auth_states[user_id] = state
                text = (
                    "⚠️ <b>ВНИМАНИЕ: Демо-режим!</b>\n\n"
                    "При подключении через бизнес-мод вы получите <b>ограниченную версию бота</b>.\n"
                    "❌ <b>НЕ БУДУТ работать:</b>\n"
                    "- Сохранение исчезающих (TTL) фото/видео\n"
                    "- Работа в группах и каналах\n"
                    "- Удаление чужих сообщений\n"
                    "- Примерно 60% функций основного бота\n\n"
                    "✅ <b>БУДУТ работать:</b>\n"
                    "- Ответы на команды (.помощь, .музыка, .факты и др.)\n"
                    "- Безопасность (нет риска бана)\n\n"
                    "Для полного функционала используйте подключение по номеру телефона."
                )
                buttons = [[Button.inline("Я понимаю, продолжить", b"business_confirmed")]]
                # Пытаемся отредактировать, если не получилось - отправляем новое
                if message_id:
                    result = await edit_message(chat_id, message_id, text, buttons=buttons)
                    if not result:
                        await send_message(chat_id, text, buttons=buttons)
                else:
                    await send_message(chat_id, text, buttons=buttons)
                    
        elif step == 'phone_warning' and data == 'phone_warning_ok':
            state['step'] = 'choose_device'
            text = (
                "📱 <b>Выберите устройство:</b>\n"
                "Как бот будет отображаться в 'Активных сеансах'?\n\n"
                "⚠️ <b>ВАЖНО:</b> Если у вас VPS/хостинг - используйте прокси!\n"
                "Desktop = меньше подозрений от Telegram"
            )
            buttons = [
                [Button.inline("💻 Desktop (Рекомендуется)", b"dev_pc")],
                [Button.inline("📱 Android", b"dev_android")],
                [Button.inline("📱 iPhone", b"dev_iphone")],
                [Button.inline("🎲 Случайное", b"dev_random")]
            ]
            if message_id:
                result = await edit_message(chat_id, message_id, text, buttons=buttons)
                if not result:
                    await send_message(chat_id, text, buttons=buttons)
            else:
                await send_message(chat_id, text, buttons=buttons)

        elif step == 'choose_device':
            dev_params = get_random_device()
            dev_name = "Случайное"
            
            if data == 'dev_iphone':
                dev_params = ("iPhone 15 Pro Max", "iOS 17.5.1", "10.12.1")
                dev_name = "iPhone 15 Pro Max"
            elif data == 'dev_android':
                dev_params = ("Samsung Galaxy S24 Ultra", "Android 14", "10.5.2")
                dev_name = "Samsung Galaxy S24 Ultra"
            elif data == 'dev_pc':
                dev_params = ("PC 64bit", "Windows 11", "4.16.30 x64")
                dev_name = "PC Windows 11"
            
            state['device_params'] = dev_params
            state['step'] = 'enter_phone'
            text = f"✅ Выбрано устройство: <b>{dev_name}</b>\n\n📱 <b>Введите номер телефона:</b>\n(например: +79991234567)"
            if message_id:
                result = await edit_message(chat_id, message_id, text)
                if not result:
                    await send_message(chat_id, text)
            else:
                await send_message(chat_id, text)
            
        elif step == 'by_business_confirm' and data == 'business_confirmed':
            logger.info(f"Processing business_confirmed for user {user_id}, step='{step}'")
            # Проверяем, есть ли уже подключение
            connection_id = business_connections.get(user_id)
            logger.info(f"Business connection check for user {user_id}: connection_id={connection_id}")
            if connection_id:
                text = "✅ У вас уже настроено бизнес-подключение!"
                if message_id:
                    result = await edit_message(chat_id, message_id, text)
                    if not result:
                        await send_message(chat_id, text)
                else:
                    await send_message(chat_id, text)
                if user_id in auth_states:
                    del auth_states[user_id]
            else:
                logger.info(f"Setting step to 'check_business' for user {user_id}")
                state['step'] = 'check_business'
                # Сохраняем состояние явно
                auth_states[user_id] = state
                text = (
                    "⚙️ <b>Настройка бизнес-режима</b>\n\n"
                    "1. Зайдите в Настройки Telegram -> Telegram Business -> Чат-боты.\n"
                    "2. Добавьте этого бота в список.\n"
                    "3. <b>ОБЯЗАТЕЛЬНО</b> включите все разрешения (особенно 'Управление сообщениями').\n"
                    "4. После этого нажмите кнопку ниже."
                )
                buttons = [[Button.inline("🔄 Проверить подключение", b"check_business")]]
                if message_id:
                    result = await edit_message(chat_id, message_id, text, buttons=buttons)
                    if not result:
                        await send_message(chat_id, text, buttons=buttons)
                else:
                    await send_message(chat_id, text, buttons=buttons)
                logger.info(f"Sent business setup message to user {user_id}")
                
        elif step == 'check_business' and data == 'check_business':
             if user_id in business_connections:
                 text = "✅ <b>Успешно!</b> Бот подключен в бизнес-режиме."
                 if message_id:
                     result = await edit_message(chat_id, message_id, text)
                     if not result:
                         await send_message(chat_id, text)
                 else:
                     await send_message(chat_id, text)
                 del auth_states[user_id]
             else:
                 text = "❌ Подключение не найдено. Попробуйте еще раз или подождите пару секунд."
                 buttons = [[Button.inline("🔄 Проверить снова", b"check_business")]]
                 if message_id:
                     result = await edit_message(chat_id, message_id, text, buttons=buttons)
                     if not result:
                         await send_message(chat_id, text, buttons=buttons)
                 else:
                     await send_message(chat_id, text, buttons=buttons)
    except Exception as e:
        logger.error(f"Ошибка обработки callback query для {user_id}: {e}", exc_info=True)
        try:
            await send_message(chat_id, f"❌ Произошла ошибка. Попробуйте начать заново с /start")
        except:
            pass

async def start_bot_manager():
    logger.info("🚀 Бот-менеджер запущен (Long Polling)")
    
    # Загружаем бизнес-подключения из БД
    try:
        conns = get_db_business_connections()
        for uid, conn_id in conns.items():
            business_connections[uid] = conn_id
        logger.debug(f"📂 Загружено {len(business_connections)} бизнес-подключений из БД")
    except Exception as e:
        logger.error(f"Ошибка загрузки бизнес-подключений: {e}")

    offset = 0
    consecutive_errors = 0
    max_consecutive_errors = 10
    
    while True:
        try:
            updates = await bot_api_request('getUpdates', {
                'offset': offset, 
                'timeout': 30,
                'allowed_updates': ['message', 'callback_query', 'business_connection', 'business_message', 'edited_business_message']
            })
            
            # Сбрасываем счетчик ошибок при успешном запросе
            consecutive_errors = 0
            
            if updates and updates.get('ok'):
                for update in updates['result']:
                    offset = update['update_id'] + 1
                    
                    try:
                        if 'message' in update:
                            bot_id = int(BOT_TOKEN.split(':')[0])
                            if update['message'].get('from', {}).get('id') != bot_id:
                                # Оборачиваем в safe_task для обработки ошибок
                                asyncio.create_task(safe_task(handle_message_update(update['message']), "handle_message_update"))
                        
                        elif 'callback_query' in update:
                            asyncio.create_task(safe_task(handle_callback_query(update['callback_query']), "handle_callback_query"))
                            
                        elif 'business_connection' in update:
                            asyncio.create_task(safe_task(handle_business_connection_update(update['business_connection']), "handle_business_connection"))
                            
                        elif 'business_message' in update:
                            asyncio.create_task(safe_task(handle_business_message(update['business_message']), "handle_business_message"))
                            
                        elif 'edited_business_message' in update:
                            asyncio.create_task(safe_task(handle_business_message(update['edited_business_message'], is_edited=True), "handle_edited_business_message"))
                    except Exception as e:
                        logger.error(f"Ошибка обработки update: {e}", exc_info=True)
                        # Продолжаем обработку следующих обновлений
                        continue
            elif updates is None:
                # Если updates None, это может быть таймаут или ошибка сети
                consecutive_errors += 1
                if consecutive_errors >= max_consecutive_errors:
                    logger.warning(f"Слишком много последовательных ошибок ({consecutive_errors}), ждем 30 секунд...")
                    await asyncio.sleep(30)
                    consecutive_errors = 0
                else:
                    await asyncio.sleep(1)
            else:
                # Если updates не ok, но не None - логируем и продолжаем
                logger.debug(f"getUpdates вернул не ok: {updates}")
                await asyncio.sleep(1)
                        
        except KeyboardInterrupt:
            raise
        except asyncio.CancelledError:
            logger.info("Bot manager отменен")
            break
        except Exception as e:
            consecutive_errors += 1
            logger.error(f"Manager Loop Error ({consecutive_errors}/{max_consecutive_errors}): {e}", exc_info=True)
            
            if consecutive_errors >= max_consecutive_errors:
                logger.critical(f"Критическая ошибка: {consecutive_errors} последовательных ошибок. Ждем 60 секунд...")
                await asyncio.sleep(60)
                consecutive_errors = 0
            else:
                wait_time = min(5 * consecutive_errors, 30)
                await asyncio.sleep(wait_time)

