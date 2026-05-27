import asyncio
import logging
import os
from pathlib import Path
from telethon import TelegramClient
from utils.database import get_active_users, is_global_enabled, remove_user
from handlers import register_handlers
from utils.message_cache import message_cache
from utils.session_persistence import session_persistence
from config import LANG_CODE, SYSTEM_LANG_CODE
from utils.proxy import get_proxy

logger = logging.getLogger(__name__)

# Lock для предотвращения одновременного подключения клиентов (database is locked fix)
client_connect_lock = asyncio.Lock()

class MultiInstanceManager:
    def __init__(self):
        self.clients = {}  # user_id -> TelegramClient
        self.base_session_path = Path(__file__).parent.parent / "sessions_local"
        self.base_session_path.mkdir(exist_ok=True)
        self.check_task = None
        self.client_ready_times = {}  # user_id -> timestamp когда клиент будет готов принимать команды
        self.warmup_duration = 300  # 5 минут карантина (300 секунд)
    
    def is_client_ready(self, user_id: int) -> tuple[bool, int]:
        """
        Проверяет, готов ли клиент принимать команды после прогрева
        
        Returns:
            (ready: bool, seconds_remaining: int)
        """
        import time
        if user_id not in self.client_ready_times:
            return True, 0  # Если время не установлено, считаем что готов
        
        current_time = time.time()
        ready_time = self.client_ready_times[user_id]
        
        if current_time >= ready_time:
            return True, 0
        
        seconds_remaining = int(ready_time - current_time)
        return False, seconds_remaining

    async def start_all(self):
        """Запуск всех активных юзерботов из БД"""
        if not is_global_enabled():
            logger.warning("Бот выключен глобально.")
            return
        
        # Очищаем старые состояния сессий (>7 дней)
        cleaned = session_persistence.cleanup_old_sessions(days=7)
        if cleaned > 0:
            logger.info(f"🧹 Очищено {cleaned} старых состояний сессий")

        users = get_active_users()
        if not users:
            return

        # Запускаем клиентов последовательно с задержкой, чтобы избежать "database is locked"
        for user_id, session_name, api_id, api_hash, dev, sys_ver, app in users:
            asyncio.create_task(self.start_client(user_id, session_name, api_id, api_hash, dev, sys_ver, app))
            await asyncio.sleep(0.5)  # Задержка 500мс между запусками клиентов
        
        if self.check_task is None or self.check_task.done():
            self.check_task = asyncio.create_task(self.session_health_checker())
        
        # Показываем статистику
        stats = session_persistence.get_session_stats()
        logger.info(f"📊 Статистика сессий: {stats['active']} активных, {stats['total']} всего")

    async def start_client(self, user_id, session_name, api_id, api_hash, device_model=None, system_version=None, app_version=None):
        """Запуск конкретного юзербота"""
        if user_id in self.clients:
            logger.info(f"Клиент {user_id} уже запущен, пропускаем")
            return

        session_path = self.base_session_path / f"{session_name}.session"
        from config import DEFAULT_DEVICE_MODEL, DEFAULT_SYSTEM_VERSION, DEFAULT_APP_VERSION
        dev = device_model or DEFAULT_DEVICE_MODEL
        sys_ver = system_version or DEFAULT_SYSTEM_VERSION
        app_ver = app_version or DEFAULT_APP_VERSION

        proxy = get_proxy()
        client = TelegramClient(
            str(session_path), api_id, api_hash,
            device_model=dev, system_version=sys_ver, app_version=app_ver,
            proxy=proxy,
            lang_code=LANG_CODE, system_lang_code=SYSTEM_LANG_CODE
        )

        try:
            # Синхронизируем подключение, чтобы избежать "database is locked"
            async with client_connect_lock:
                await client.connect()
            
            if not await client.is_user_authorized():
                logger.warning(f"Клиент {user_id} не авторизован, удаляем из БД")
                try:
                    await client.disconnect()
                except:
                    pass
                remove_user(user_id)
                return

            # Регистрируем обработчики
            register_handlers(client, owner_id=user_id)
            self.clients[user_id] = client
            
            # Сохраняем состояние сессии
            session_persistence.update_session(
                user_id,
                status='active',
                device=device_model,
                error_count=0
            )
            
            logger.info(f"✅ Клиент {user_id} успешно запущен и подключен")
            
            # "Прогрев" сессии - имитируем реального пользователя
            import time
            try:
                logger.debug(f"🔥 Прогрев сессии {user_id}...")
                await asyncio.sleep(3)  # Пауза 3 секунды
                
                # Простой запрос для прогрева
                await client.get_dialogs(limit=5)
                await asyncio.sleep(2)
                
                # Получаем информацию о себе
                me = await client.get_me()
                logger.debug(f"✅ Сессия {user_id} прогрета ({me.first_name})")
            except Exception as e:
                logger.warning(f"⚠️ Ошибка прогрева сессии {user_id}: {e}")
            
            # Устанавливаем время готовности (через N минут после подключения)
            self.client_ready_times[user_id] = time.time() + self.warmup_duration
            logger.info(f"⏰ Клиент {user_id} будет готов через {self.warmup_duration // 60} минут")
            
            # Запускаем с автоматическим переподключением
            reconnect_count = 0
            max_reconnects = 50
            
            while reconnect_count < max_reconnects:
                try:
                    await client.run_until_disconnected()
                    # Если соединение разорвано, пытаемся переподключиться
                    reconnect_count += 1
                    if reconnect_count < max_reconnects:
                        logger.warning(f"Клиент {user_id} отключен, переподключение {reconnect_count}/{max_reconnects}...")
                        await asyncio.sleep(min(5 * reconnect_count, 60))  # Экспоненциальная задержка, макс 60 сек
                        
                        # Проверяем, что клиент еще нужен
                        active_users = get_active_users()
                        active_user_ids = [uid for uid, _, _, _, _, _, _ in active_users] if active_users else []
                        if user_id not in active_user_ids:
                            logger.info(f"Клиент {user_id} больше не активен, останавливаем")
                            break
                            
                        try:
                            async with client_connect_lock:
                                await client.connect()
                            if not await client.is_user_authorized():
                                logger.warning(f"Клиент {user_id} не авторизован после переподключения")
                                remove_user(user_id)
                                break
                            logger.info(f"✅ Клиент {user_id} переподключен")
                            reconnect_count = 0  # Сбрасываем счетчик при успешном переподключении
                        except Exception as reconnect_error:
                            logger.error(f"Ошибка переподключения клиента {user_id}: {reconnect_error}")
                            await asyncio.sleep(10)
                    else:
                        logger.error(f"Клиент {user_id} достиг максимального количества переподключений")
                        break
                except asyncio.CancelledError:
                    logger.info(f"Клиент {user_id} отменен")
                    break
                except Exception as e:
                    error_str = str(e).lower()
                    
                    # Проверяем на инвалидацию сессии
                    if 'key is not registered' in error_str or 'key not found' in error_str:
                        logger.critical(f"🔴 Сессия {user_id} ИНВАЛИДИРОВАНА Telegram! Удаляю...")
                        
                        # Удаляем сессию файл
                        try:
                            import os
                            session_file = f"sessions_local/{user_id}.session"
                            if os.path.exists(session_file):
                                os.remove(session_file)
                                logger.info(f"Удалён файл сессии: {session_file}")
                        except Exception as del_err:
                            logger.error(f"Не удалось удалить сессию: {del_err}")
                        
                        # Удаляем из БД
                        remove_user(user_id)
                        
                        # Уведомляем пользователя через бот
                        try:
                            from utils.bot_sender import send_to_owner
                            await send_to_owner(
                                user_id,
                                "🔴 <b>СЕССИЯ ИНВАЛИДИРОВАНА</b>\n\n"
                                "Telegram удалил вашу сессию из системы.\n\n"
                                "<b>Причины:</b>\n"
                                "• Подозрительная активность\n"
                                "• Конфликт устройств\n"
                                "• Вход с другого IP\n\n"
                                "Пожалуйста, подключитесь заново через /start"
                            )
                        except:
                            pass
                        
                        logger.critical(f"🔴 Клиент {user_id} требует переавторизации!")
                        session_persistence.remove_session(user_id)
                        break
                    
                    # Если это другая ошибка авторизации или критическая - не переподключаемся
                    if 'auth' in error_str or 'unauthorized' in error_str or 'session' in error_str:
                        logger.error(f"Критическая ошибка клиента {user_id}: {e}")
                        break
                    
                    reconnect_count += 1
                    logger.error(f"Ошибка клиента {user_id} (переподключение {reconnect_count}/{max_reconnects}): {e}")
                    
                    # Обновляем состояние сессии
                    session_persistence.update_session(
                        user_id,
                        status='error' if reconnect_count >= max_reconnects else 'reconnecting',
                        error_count=reconnect_count,
                        last_error=str(e),
                        reconnect_count=reconnect_count
                    )
                    
                    if reconnect_count < max_reconnects:
                        await asyncio.sleep(min(5 * reconnect_count, 60))
                    else:
                        break
        except asyncio.CancelledError:
            logger.info(f"Клиент {user_id} отменен")
        except Exception as e:
            logger.error(f"Ошибка клиента {user_id}: {e}", exc_info=True)
        finally:
            if user_id in self.clients:
                try:
                    client = self.clients[user_id]
                    if client.is_connected():
                        await client.disconnect()
                except:
                    pass
                del self.clients[user_id]
            
            # Обновляем состояние при остановке
            session_persistence.update_session(
                user_id,
                status='disconnected'
            )
            session_persistence.save()  # Принудительно сохраняем
            
            logger.info(f"Клиент {user_id} остановлен")

    async def session_health_checker(self):
        """
        Проверяет здоровье всех сессий каждые 2 часа
        - Проверяет соединение
        - Проверяет авторизацию
        - Проверяет что сессия валидна
        - Пытается восстановить при проблемах
        - НЕ проверяет свежие сессии (младше 10 минут)
        """
        logger.info("💊 Health checker запущен (проверка каждые 2 часа)")
        
        # Словарь для отслеживания времени подключения клиентов
        client_start_times = {}
        
        while True:
            try:
                await asyncio.sleep(7200)  # 2 часа
                
                active_ids = list(self.clients.keys())
                if not active_ids:
                    continue
                
                logger.debug(f"💊 Health check для {len(active_ids)} клиентов...")
                
                import time
                current_time = time.time()
                
                for uid in active_ids:
                    client = self.clients.get(uid)
                    if not client:
                        continue
                    
                    # Отслеживаем время подключения клиента
                    if uid not in client_start_times:
                        client_start_times[uid] = current_time
                    
                    # Пропускаем свежие клиенты (младше 10 минут)
                    time_since_start = current_time - client_start_times[uid]
                    if time_since_start < 600:  # 10 минут
                        logger.debug(f"⏭️ Пропускаем проверку клиента {uid} (подключен {int(time_since_start/60)} мин назад)")
                        continue
                    
                    try:
                        # Проверка 1: Соединение
                        if not client.is_connected():
                            logger.warning(f"⚠️ Клиент {uid} отключен, переподключаем...")
                            try:
                                await client.connect()
                                logger.info(f"✅ Клиент {uid} переподключен")
                            except Exception as e:
                                logger.error(f"❌ Не удалось переподключить {uid}: {e}")
                                continue
                        
                        # Проверка 2: Авторизация
                        try:
                            is_authorized = await asyncio.wait_for(
                                client.is_user_authorized(),
                                timeout=10.0
                            )
                            
                            if not is_authorized:
                                logger.critical(f"🔴 Клиент {uid} больше не авторизован!")
                                await self.stop_client(uid)
                                remove_user(uid)
                                
                                # Уведомляем пользователя
                                try:
                                    from utils.bot_sender import send_to_owner
                                    await send_to_owner(
                                        uid,
                                        "🔴 <b>Потеряна авторизация</b>\n\n"
                                        "Ваша сессия больше не авторизована.\n"
                                        "Пожалуйста, подключитесь заново через /start"
                                    )
                                except:
                                    pass
                                continue
                        except asyncio.TimeoutError:
                            logger.warning(f"⚠️ Timeout при проверке авторизации {uid}")
                            continue
                        
                        # Проверка 3: Тестовый запрос (пингуем Telegram)
                        try:
                            me = await asyncio.wait_for(
                                client.get_me(),
                                timeout=10.0
                            )
                            logger.debug(f"✅ Клиент {uid} здоров (ping OK)")
                        except asyncio.TimeoutError:
                            logger.warning(f"⚠️ Клиент {uid} не отвечает на ping")
                        except Exception as e:
                            error_str = str(e).lower()
                            if 'key is not registered' in error_str:
                                logger.critical(f"🔴 Health check: Сессия {uid} инвалидирована!")
                                # Обработка инвалидации
                                try:
                                    import os
                                    session_file = f"sessions_local/{uid}.session"
                                    if os.path.exists(session_file):
                                        os.remove(session_file)
                                except:
                                    pass
                                await self.stop_client(uid)
                                remove_user(uid)
                                
                                try:
                                    from utils.bot_sender import send_to_owner
                                    await send_to_owner(
                                        uid,
                                        "🔴 <b>СЕССИЯ ИНВАЛИДИРОВАНА</b>\n\n"
                                        "Health check обнаружил что Telegram удалил вашу сессию.\n"
                                        "Подключитесь заново через /start"
                                    )
                                except:
                                    pass
                            else:
                                logger.warning(f"⚠️ Ошибка при ping клиента {uid}: {e}")
                    
                    except Exception as e:
                        logger.error(f"Ошибка health check для клиента {uid}: {e}")
                
                logger.debug(f"💊 Health check завершен")
                
            except asyncio.CancelledError:
                logger.info("💊 Health checker остановлен")
                break
            except Exception as e:
                logger.error(f"Критическая ошибка в health checker: {e}", exc_info=True)
                await asyncio.sleep(60)  # Подождать минуту при ошибке

    async def stop_all(self):
        """Останавливает всех клиентов и сохраняет состояние"""
        logger.info("🛑 Остановка всех клиентов...")
        for user_id in list(self.clients.keys()):
            await self.stop_client(user_id)
        
        # Сохраняем все состояния
        session_persistence.save()
        logger.info("💾 Состояния сессий сохранены")

    async def stop_client(self, user_id):
        if user_id in self.clients:
            client = self.clients[user_id]
            try: await client.disconnect()
            except: pass
            del self.clients[user_id]
        
        # Очищаем время готовности
        if user_id in self.client_ready_times:
            del self.client_ready_times[user_id]
    
    async def restart_all(self):
        """Перезапускает всех активных клиентов"""
        logger.info("🔄 Перезапуск всех клиентов...")
        # Останавливаем всех
        await self.stop_all()
        # Ждем чтобы соединения закрылись
        await asyncio.sleep(2)
        # Запускаем заново
        await self.start_all()
        logger.info("✅ Все клиенты перезапущены")

instance_manager = MultiInstanceManager()
