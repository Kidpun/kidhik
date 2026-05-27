"""
Команды для работы с сетью:
.ip - информация об IP-адресе
.домен - информация о домене
.whois - WHOIS информация о домене
"""
import logging
import re
import aiohttp
import socket
import asyncio
from telethon import events

logger = logging.getLogger(__name__)

async def check_ip_info(ip: str) -> dict:
    """Получает информацию об IP через ipwhois.io (бесплатный API, до 10k запросов/месяц)"""
    try:
        # Валидация IP
        try:
            socket.inet_aton(ip)
        except socket.error:
            return {'error': 'Неверный формат IP-адреса'}
        
        # Используем ipwhois.io (бесплатно до 10,000 запросов/месяц, без регистрации)
        url = f"https://ipwho.is/{ip}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get('success'):
                        connection = data.get('connection', {})
                        timezone = data.get('timezone', {})
                        currency = data.get('currency', {})
                        security = data.get('security', {})
                        flag = data.get('flag', {})
                        
                        return {
                            'success': True,
                            'ip': data.get('ip'),
                            'type': data.get('type'),
                            'country': data.get('country'),
                            'country_code': data.get('country_code'),
                            'continent': data.get('continent'),
                            'region': data.get('region'),
                            'city': data.get('city'),
                            'postal': data.get('postal'),
                            'lat': data.get('latitude'),
                            'lon': data.get('longitude'),
                            'timezone': timezone.get('id'),
                            'timezone_offset': timezone.get('utc'),
                            'timezone_current': timezone.get('current_time'),
                            'isp': connection.get('isp'),
                            'org': connection.get('org'),
                            'asn': connection.get('asn'),
                            'domain': connection.get('domain'),
                            'currency': currency.get('name'),
                            'currency_code': currency.get('code'),
                            'currency_symbol': currency.get('symbol'),
                            'is_proxy': security.get('proxy', False),
                            'is_vpn': security.get('vpn', False),
                            'is_tor': security.get('tor', False),
                            'is_hosting': security.get('hosting', False),
                            'flag_emoji': flag.get('emoji', '')
                        }
                    else:
                        return {'error': data.get('message', 'Ошибка API')}
    except asyncio.TimeoutError:
        return {'error': 'Таймаут запроса'}
    except Exception as e:
        logger.error(f"IP check error: {e}")
        return {'error': str(e)}

async def check_domain_info(domain: str) -> dict:
    """Получает информацию о домене (DNS, WHOIS через API)"""
    try:
        # Очистка домена
        domain = domain.lower().strip()
        domain = domain.replace('http://', '').replace('https://', '').replace('www.', '')
        domain = domain.split('/')[0].split('?')[0]
        
        # Валидация домена
        if not re.match(r'^[a-z0-9]([a-z0-9\-]{0,61}[a-z0-9])?(\.[a-z0-9]([a-z0-9\-]{0,61}[a-z0-9])?)*\.[a-z]{2,}$', domain):
            return {'error': 'Неверный формат домена'}
        
        result = {
            'domain': domain,
            'dns': {},
            'whois': {}
        }
        
        # 1. DNS записи (через socket)
        try:
            # A записи
            try:
                a_records = socket.gethostbyname_ex(domain)
                result['dns']['ip'] = a_records[2][0] if a_records[2] else None
                result['dns']['aliases'] = a_records[1] if a_records[1] else []
            except:
                result['dns']['ip'] = None
            
            # MX записи
            try:
                mx_records = socket.getaddrinfo(domain, None, socket.AF_INET)
                # Это не совсем MX, но пока так
            except:
                pass
        except Exception as e:
            logger.debug(f"DNS lookup error: {e}")
        
        # 2. Получаем информацию об IP домена через ipwhois.io
        if result['dns'].get('ip'):
            try:
                ip_info = await check_ip_info(result['dns']['ip'])
                if ip_info.get('success'):
                    result['whois'] = {
                        'registrar': ip_info.get('org'),
                        'country': ip_info.get('country'),
                        'city': ip_info.get('city'),
                        'isp': ip_info.get('isp'),
                        'org': ip_info.get('org'),
                        'asn': ip_info.get('asn')
                    }
            except Exception as e:
                logger.debug(f"IPWHOIS.io error: {e}")
        
        # 3. Дополнительная информация через socket
        try:
            # Проверка доступности
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result['dns']['online'] = sock.connect_ex((result['dns'].get('ip') or domain, 80)) == 0
            sock.close()
        except:
            result['dns']['online'] = False
        
        return result
        
    except Exception as e:
        logger.error(f"Domain check error: {e}")
        return {'error': str(e)}

async def get_whois_data(domain: str) -> dict:
    """
    Получает WHOIS данные о домене
    Сначала получает IP домена, затем использует ipwhois.io для получения информации
    """
    try:
        domain = domain.lower().strip()
        domain = domain.replace('http://', '').replace('https://', '').replace('www.', '')
        domain = domain.split('/')[0].split('?')[0]
        
        # 1. Получаем IP адрес домена
        try:
            domain_ip = socket.gethostbyname(domain)
        except socket.gaierror:
            return {'error': 'Не удалось разрешить домен в IP-адрес'}
        except Exception as e:
            logger.debug(f"DNS resolution error: {e}")
            return {'error': f'Ошибка DNS: {str(e)}'}
        
        # 2. Используем ipwhois.io для получения информации об IP
        # (это даст нам информацию о провайдере, локации и т.д.)
        ip_info = await check_ip_info(domain_ip)
        
        if 'error' in ip_info:
            return {'error': f'Не удалось получить информацию об IP домена: {ip_info["error"]}'}
        
        # 3. Пробуем получить дополнительную WHOIS информацию через whoisapi.live
        whois_extra = {}
        try:
            url = f"https://whoisapi.live/api/whois"
            params = {'domain': domain}
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get('status') == 'success' or data.get('domain'):
                            whois_extra = {
                                'registrar': data.get('registrar'),
                                'created': data.get('creation_date'),
                                'updated': data.get('updated_date'),
                                'expires': data.get('expiry_date'),
                                'name_servers': data.get('name_servers', []),
                                'status': data.get('status'),
                                'registrant': data.get('registrant_name')
                            }
        except Exception as e:
            logger.debug(f"whoisapi.live error: {e}")
        
        # Объединяем данные
        result = {
            'success': True,
            'domain': domain,
            'ip': domain_ip,
            'registrar': whois_extra.get('registrar') or ip_info.get('org', 'Неизвестно'),
            'created': whois_extra.get('created'),
            'updated': whois_extra.get('updated'),
            'expires': whois_extra.get('expires'),
            'name_servers': whois_extra.get('name_servers', []),
            'status': whois_extra.get('status'),
            'registrant': whois_extra.get('registrant'),
            'country': ip_info.get('country', 'Неизвестно'),
            'city': ip_info.get('city'),
            'isp': ip_info.get('isp', 'Неизвестно'),
            'org': ip_info.get('org'),
            'asn': ip_info.get('asn')
        }
        
        return result
            
    except Exception as e:
        logger.error(f"WHOIS error: {e}")
        return {'error': str(e)}

async def ip_command(event: events.NewMessage.Event):
    """
    .ip <IP-адрес> - Информация об IP-адресе
    """
    text = event.message.text.strip()
    parts = text.split(maxsplit=1)
    
    if len(parts) < 2:
        await event.respond(
            "🌐 <b>Команда .ip</b>\n\n"
            "Использование: <code>.ip 8.8.8.8</code>\n\n"
            "📊 Показывает:\n"
            "• Страну и город\n"
            "• Провайдера (ISP)\n"
            "• Координаты\n"
            "• Часовой пояс\n"
            "• AS номер",
            parse_mode='html'
        )
        return
    
    ip = parts[1].strip()
    status_msg = await event.respond("🔍 <b>Проверяю IP...</b>", parse_mode='html')
    
    info = await check_ip_info(ip)
    
    try:
        await status_msg.delete()
    except:
        pass
    
    if 'error' in info:
        await event.respond(f"❌ <b>Ошибка:</b> {info['error']}", parse_mode='html')
        return
    
    if not info.get('success'):
        await event.respond("❌ Не удалось получить информацию об IP", parse_mode='html')
        return
    
    # Формируем ответ
    res = f"🌐 <b>Информация об IP:</b> <code>{info['ip']}</code>"
    if info.get('type'):
        res += f" ({info.get('type')})"
    res += "\n\n"
    
    res += f"📍 <b>Геолокация:</b>\n"
    flag_emoji = info.get('flag_emoji', '')
    res += f"🏳️ Страна: {info.get('country', 'Неизвестно')} {flag_emoji}"
    if info.get('country_code'):
        res += f" ({info.get('country_code')})"
    res += "\n"
    if info.get('continent'):
        res += f"🌍 Континент: {info.get('continent')}\n"
    if info.get('region'):
        res += f"🗺 Регион: {info.get('region')}\n"
    if info.get('city'):
        res += f"🏙 Город: {info.get('city')}\n"
    if info.get('postal'):
        res += f"📮 Индекс: {info.get('postal')}\n"
    if info.get('lat') and info.get('lon'):
        res += f"🗺 Координаты: {info.get('lat')}, {info.get('lon')}\n"
        res += f"🔗 <a href='https://www.google.com/maps?q={info.get('lat')},{info.get('lon')}'>Открыть на карте</a>\n"
    res += "\n"
    
    res += f"🌐 <b>Провайдер:</b>\n"
    if info.get('isp'):
        res += f"📡 ISP: {info.get('isp')}\n"
    if info.get('org'):
        res += f"🏢 Организация: {info.get('org')}\n"
    if info.get('asn'):
        res += f"🔢 ASN: {info.get('asn')}\n"
    if info.get('domain'):
        res += f"🌐 Домен: {info.get('domain')}\n"
    res += "\n"
    
    if info.get('timezone'):
        res += f"⏰ <b>Часовой пояс:</b> {info.get('timezone')}"
        if info.get('timezone_offset'):
            res += f" ({info.get('timezone_offset')})"
        res += "\n"
        if info.get('timezone_current'):
            res += f"🕐 Текущее время: {info.get('timezone_current')}\n"
    res += "\n"
    
    if info.get('currency'):
        res += f"💰 <b>Валюта:</b> {info.get('currency')}"
        if info.get('currency_symbol'):
            res += f" ({info.get('currency_symbol')})"
        res += "\n\n"
    
    # Безопасность
    security_info = []
    if info.get('is_proxy'):
        security_info.append("🔴 Прокси")
    if info.get('is_vpn'):
        security_info.append("🔴 VPN")
    if info.get('is_tor'):
        security_info.append("🔴 Tor")
    if info.get('is_hosting'):
        security_info.append("🏢 Хостинг")
    
    if security_info:
        res += f"🔒 <b>Безопасность:</b> {', '.join(security_info)}\n"
    
    await event.respond(res, parse_mode='html', link_preview=False)

async def domain_command(event: events.NewMessage.Event):
    """
    .домен <домен> - Информация о домене
    """
    text = event.message.text.strip()
    parts = text.split(maxsplit=1)
    
    if len(parts) < 2:
        await event.respond(
            "🌐 <b>Команда .домен</b>\n\n"
            "Использование: <code>.домен google.com</code>\n\n"
            "📊 Показывает:\n"
            "• IP-адрес\n"
            "• DNS записи\n"
            "• Статус доступности\n"
            "• WHOIS данные",
            parse_mode='html'
        )
        return
    
    domain = parts[1].strip()
    status_msg = await event.respond("🔍 <b>Проверяю домен...</b>", parse_mode='html')
    
    info = await check_domain_info(domain)
    
    try:
        await status_msg.delete()
    except:
        pass
    
    if 'error' in info:
        await event.respond(f"❌ <b>Ошибка:</b> {info['error']}", parse_mode='html')
        return
    
    # Формируем ответ
    res = f"🌐 <b>Информация о домене:</b> <code>{info['domain']}</code>\n\n"
    
    res += f"📡 <b>DNS:</b>\n"
    if info.get('dns', {}).get('ip'):
        res += f"🆔 IP-адрес: <code>{info['dns']['ip']}</code>\n"
    else:
        res += f"❌ IP-адрес: не найден\n"
    
    if info.get('dns', {}).get('aliases'):
        res += f"🔗 Алиасы: {', '.join(info['dns']['aliases'])}\n"
    
    online_status = "🟢 Онлайн" if info.get('dns', {}).get('online') else "🔴 Офлайн"
    res += f"📶 Статус: {online_status}\n\n"
    
    if info.get('whois'):
        res += f"📋 <b>WHOIS:</b>\n"
        if info['whois'].get('registrar'):
            res += f"🏢 Регистратор: {info['whois']['registrar']}\n"
        if info['whois'].get('country'):
            res += f"🏳️ Страна: {info['whois']['country']}\n"
        if info['whois'].get('city'):
            res += f"🏙 Город: {info['whois']['city']}\n"
        if info['whois'].get('isp'):
            res += f"📡 ISP: {info['whois']['isp']}\n"
    
    await event.respond(res, parse_mode='html')

async def whois_command(event: events.NewMessage.Event):
    """
    .whois <домен> - Детальная WHOIS информация
    """
    text = event.message.text.strip()
    parts = text.split(maxsplit=1)
    
    if len(parts) < 2:
        await event.respond(
            "📋 <b>Команда .whois</b>\n\n"
            "Использование: <code>.whois google.com</code>\n\n"
            "📊 Показывает детальную WHOIS информацию о домене",
            parse_mode='html'
        )
        return
    
    domain = parts[1].strip()
    status_msg = await event.respond("🔍 <b>Получаю WHOIS данные...</b>", parse_mode='html')
    
    info = await get_whois_data(domain)
    
    try:
        await status_msg.delete()
    except:
        pass
    
    if 'error' in info:
        await event.respond(f"❌ <b>Ошибка:</b> {info['error']}", parse_mode='html')
        return
    
    if not info.get('success'):
        await event.respond("❌ Не удалось получить WHOIS данные", parse_mode='html')
        return
    
    res = f"📋 <b>WHOIS:</b> <code>{info['domain']}</code>\n\n"
    
    res += f"🏢 <b>Регистратор:</b> {info.get('registrar', 'Неизвестно')}\n"
    
    if info.get('registrant'):
        res += f"👤 <b>Регистрант:</b> {info.get('registrant')}\n"
    
    if info.get('created'):
        res += f"📅 <b>Создан:</b> {info.get('created')}\n"
    if info.get('updated'):
        res += f"🔄 <b>Обновлен:</b> {info.get('updated')}\n"
    if info.get('expires'):
        res += f"⏰ <b>Истекает:</b> {info.get('expires')}\n"
    
    if info.get('name_servers'):
        ns_list = info['name_servers']
        if isinstance(ns_list, list) and len(ns_list) > 0:
            ns_str = ', '.join(ns_list[:3])  # Показываем первые 3
            if len(ns_list) > 3:
                ns_str += f" (+{len(ns_list) - 3})"
            res += f"🌐 <b>Name Servers:</b> {ns_str}\n"
    
    if info.get('status'):
        res += f"📊 <b>Статус:</b> {info.get('status')}\n"
    
    if info.get('country'):
        res += f"🏳️ <b>Страна:</b> {info.get('country')}\n"
    if info.get('city'):
        res += f"🏙 <b>Город:</b> {info.get('city')}\n"
    if info.get('isp'):
        res += f"📡 <b>ISP:</b> {info.get('isp')}\n"
    if info.get('ip'):
        res += f"🆔 <b>IP:</b> <code>{info['ip']}</code>\n"
    
    await event.respond(res, parse_mode='html')

