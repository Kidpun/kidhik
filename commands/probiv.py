"""
Команда .пробив
Поиск информации по номеру телефона:
1. Проверка через Telegram (Import Contact)
2. NumVerify API (Оператор, Страна, Тип)
3. Локальная база (Резерв)
4. Ссылки на мессенджеры
"""
import logging
import re
import aiohttp
import random
from telethon import events
from telethon.tl.functions.contacts import ImportContactsRequest, DeleteContactsRequest
from telethon.tl.types import InputPhoneContact
from telethon.tl.functions.users import GetFullUserRequest
from telethon.errors import FloodWaitError

logger = logging.getLogger(__name__)

NUMVERIFY_KEY = 'b279aeb36ee06c9586f0e7a3f3d99177'

# Расширенная база кодов операторов РФ (Резерв)
OPERATOR_CODES = {
    # МТС
    '910': 'МТС', '911': 'МТС', '912': 'МТС', '913': 'МТС', '914': 'МТС', 
    '915': 'МТС', '916': 'МТС', '917': 'МТС', '918': 'МТС', '919': 'МТС',
    '980': 'МТС', '981': 'МТС', '982': 'МТС', '983': 'МТС', '984': 'МТС', 
    '985': 'МТС', '986': 'МТС', '987': 'МТС', '988': 'МТС', '989': 'МТС',
    # Мегафон
    '920': 'Мегафон', '921': 'Мегафон', '922': 'Мегафон', '923': 'Мегафон', 
    '924': 'Мегафон', '925': 'Мегафон', '926': 'Мегафон', '927': 'Мегафон', 
    '928': 'Мегафон', '929': 'Мегафон', '930': 'Мегафон', '931': 'Мегафон', 
    '932': 'Мегафон', '933': 'Мегафон', '934': 'Мегафон', '936': 'Мегафон', 
    '937': 'Мегафон', '938': 'Мегафон', '939': 'Мегафон',
    # Билайн
    '903': 'Билайн', '905': 'Билайн', '906': 'Билайн', '909': 'Билайн', 
    '960': 'Билайн', '961': 'Билайн', '962': 'Билайн', '963': 'Билайн', 
    '964': 'Билайн', '965': 'Билайн', '966': 'Билайн', '967': 'Билайн', 
    '968': 'Билайн', '969': 'Билайн',
    # Теле2 / Ростелеком
    '900': 'Теле2', '901': 'Теле2', '902': 'Теле2', '904': 'Теле2', 
    '908': 'Теле2', '950': 'Теле2', '951': 'Теле2', '952': 'Теле2', 
    '953': 'Теле2', '991': 'Ростелеком/Теле2', '992': 'Теле2', 
    '993': 'Теле2', '994': 'Теле2', '995': 'Теле2', '996': 'Теле2',
    # Yota
    '999': 'Yota',
    # Виртуальные
    '958': 'Виртуальный (Газпром/Сбер/Тинькофф)',
    '959': 'Тинькофф Мобайл',
    '969': 'Билайн/Тинькофф',
}

def normalize_phone(phone: str) -> str:
    """Нормализует номер телефона до формата +7XXXXXXXXXX"""
    digits = re.sub(r'\D', '', phone)
    if digits.startswith('8') and len(digits) == 11:
        digits = '7' + digits[1:]
    if digits.startswith('7') and len(digits) == 11:
        return '+' + digits
    if len(digits) == 10:
        return '+7' + digits
    return '+' + digits # Для международных номеров

async def check_numverify(phone: str) -> dict:
    """Запрос к NumVerify API"""
    try:
        clean_phone = phone.replace('+', '')
        url = f"http://apilayer.net/api/validate?access_key={NUMVERIFY_KEY}&number={clean_phone}&format=1"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get('valid'):
                        return {
                            'success': True,
                            'country': data.get('country_name'),
                            'carrier': data.get('carrier'),
                            'line_type': data.get('line_type'),
                            'location': data.get('location'),
                            'format': data.get('international_format')
                        }
    except Exception as e:
        logger.error(f"Numverify error: {e}")
    return None

async def check_telegram_account(client, phone: str):
    """Проверяет наличие Telegram аккаунта"""
    contact_input = InputPhoneContact(
        client_id=random.randint(1000000, 9999999),
        phone=phone,
        first_name="Probiv",
        last_name="Check"
    )
    
    try:
        result = await client(ImportContactsRequest([contact_input]))
        user_info = None
        
        if result.imported:
            user_id = result.imported[0].user_id
            full_user = await client(GetFullUserRequest(user_id))
            user = full_user.users[0]
            await client(DeleteContactsRequest([user_id]))
            
            user_info = {
                'id': user.id,
                'first_name': getattr(user, 'first_name', '') or '',
                'last_name': getattr(user, 'last_name', '') or '',
                'username': getattr(user, 'username', None),
                'bio': getattr(full_user.full_user, 'about', None),
                'premium': getattr(user, 'premium', False),
                'scam': getattr(user, 'scam', False),
                'fake': getattr(user, 'fake', False)
            }
        return user_info
    except FloodWaitError as e:
        return {'error': f'FloodWait {e.seconds}s'}
    except Exception as e:
        logger.error(f"Tg check error: {e}")
        return None

async def check_local_base(phone: str) -> dict:
    """Локальная проверка (Резерв)"""
    phone_clean = phone.replace('+', '')
    if not phone_clean.startswith('7') or len(phone_clean) != 11:
        return {'valid': False}
    
    operator_code = phone_clean[1:4]
    carrier = OPERATOR_CODES.get(operator_code, "Не определен")
    location = "РФ"
    return {'valid': True, 'carrier': carrier, 'location': location}

async def probiv_command(event: events.NewMessage.Event):
    """
    .пробив <номер>
    """
    text = event.message.text.strip()
    parts = text.split(maxsplit=1)
    
    if len(parts) < 2:
        await event.respond(
            "📱 <b>Команда .пробив</b>\n\n"
            "Использование: <code>.пробив +79991234567</code>\n\n"
            "🔍 Проверяет:\n"
            "• Оператора/Страну (API)\n"
            "• Telegram аккаунт\n"
            "• Мессенджеры",
            parse_mode='html'
        )
        return
    
    phone = parts[1].strip()
    normalized = normalize_phone(phone)
    status_msg = await event.respond("🔍 <b>Выполняю поиск...</b>", parse_mode='html')
    
    # 1. API NumVerify
    api_info = await check_numverify(normalized)
    
    # 2. Telegram
    tg_info = await check_telegram_account(event.client, normalized)
    
    # 3. Локальная база (если API молчит)
    local_info = await check_local_base(normalized)
    
    try: await status_msg.delete()
    except Exception: pass
    
    # --- СБОРКА ОТЧЕТА ---
    res = f"🕵️‍♂️ <b>Досье на номер:</b> <code>{normalized}</code>\n\n"
    
    # Блок Связи
    res += f"📞 <b>Связь:</b>\n"
    
    if api_info:
        country = api_info.get('country', 'Неизвестно')
        carrier = api_info.get('carrier', 'Неизвестно')
        line = api_info.get('line_type', '')
        loc = api_info.get('location', '')
        
        res += f"🏳️ Страна: {country}\n"
        res += f"📱 Оператор: <b>{carrier}</b>\n"
        if line: res += f"📞 Тип: {line}\n"
        if loc: res += f"📍 Локация: {loc}\n"
        res += "✅ Источник: NumVerify API\n\n"
    elif local_info['valid']:
        res += f"🏳️ Страна: Россия 🇷🇺\n"
        res += f"📱 Оператор: <b>{local_info['carrier']}</b>\n"
        res += f"📍 Регион: {local_info['location']}\n"
        res += "⚠️ Источник: Локальная база\n\n"
    else:
        res += "❓ Инфо об операторе не найдено\n\n"
        
    # Блок Telegram
    res += f"✈️ <b>Telegram:</b>\n"
    if tg_info and 'error' not in tg_info:
        name = f"{tg_info['first_name']} {tg_info['last_name']}".strip()
        username = f"@{tg_info['username']}" if tg_info['username'] else "Нет"
        res += f"✅ <b>Аккаунт найден!</b>\n"
        res += f"👤 Имя: {name}\n"
        res += f"🆔 ID: <code>{tg_info['id']}</code>\n"
        res += f"🌐 Юзернейм: {username}\n"
        if tg_info.get('bio'): res += f"📝 Био: {tg_info['bio']}\n"
        if tg_info.get('premium'): res += f"🌟 Premium\n"
        if tg_info.get('scam'): res += f"⚠️ SCAM\n"
    elif tg_info and 'error' in tg_info:
        res += f"⚠️ Ошибка: {tg_info['error']}\n"
    else:
        res += f"❌ Аккаунт не найден\n"

    # Ссылки
    clean_ph = normalized.replace('+', '')
    res += f"\n🔗 <b>Ссылки:</b>\n"
    res += f"• <a href='https://wa.me/{clean_ph}'>WhatsApp</a>\n"
    res += f"• <a href='viber://chat?number={clean_ph}'>Viber</a>\n"
    res += f"• <a href='https://t.me/{clean_ph}'>Telegram</a>\n"
    
    await event.respond(res, parse_mode='html', link_preview=False)
