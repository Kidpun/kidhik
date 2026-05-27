"""
KidHik - Многопользовательский Userbot для Telegram
"""
import asyncio
import logging
import sys
import signal
from pathlib import Path

from utils.database import init_db
from utils.instance_manager import instance_manager
from utils.bot_manager import start_bot_manager
from utils.earth_animation import earth_anim
from utils.log_rotator import setup_logging
from utils.funstat import init_funstat
from config import FUNSTAT_TOKEN

# Настройка логирования с ротацией и анимацией
logger = setup_logging('kidhik.log')

# Анимация отключена (ломает Termius)
# earth_anim.start()

async def shutdown(loop, signal=None):
    """Корректное завершение работы"""
    if signal:
        logger.info(f"Получен сигнал завершения {signal.name}...")
    
    logger.info("🛑 Остановка всех сервисов...")
    
    # Анимация отключена
    # earth_anim.stop()
    
    # Сначала останавливаем юзерботов
    await instance_manager.stop_all()
    
    # Даем время на закрытие соединений
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    [task.cancel() for task in tasks]
    
    logger.info(f"Отмена {len(tasks)} активных задач...")
    await asyncio.gather(*tasks, return_exceptions=True)
    
    loop.stop()
    logger.info("✅ Работа завершена.")

async def cleanup_temp_files():
    """Очистка старых временных файлов"""
    import time
    temp_dirs = [
        Path(__file__).parent / "temp_media",
        Path(__file__).parent / "saved_media"
    ]
    
    while True:
        try:
            await asyncio.sleep(1800)  # Каждые 30 минут
            
            for temp_dir in temp_dirs:
                if not temp_dir.exists():
                    continue
                    
                current_time = time.time()
                cleaned = 0
                
                for file_path in temp_dir.iterdir():
                    if not file_path.is_file():
                        continue
                    
                    # Удаляем файлы старше 1 часа
                    file_age = current_time - file_path.stat().st_mtime
                    if file_age > 3600:  # 1 час
                        try:
                            file_path.unlink()
                            cleaned += 1
                        except Exception as e:
                            logger.debug(f"Failed to delete old temp file {file_path}: {e}")
                
                if cleaned > 0:
                    logger.info(f"🧹 Cleaned {cleaned} old files from {temp_dir.name}")
                    
        except Exception as e:
            logger.error(f"Error in cleanup_temp_files: {e}")

async def memory_monitor():
    """Мониторинг памяти и автоматическая очистка кешей"""
    try:
        import psutil
        has_psutil = True
    except ImportError:
        logger.warning("psutil не установлен, мониторинг памяти отключен")
        has_psutil = False
    
    from utils.message_cache import message_cache
    
    while True:
        try:
            await asyncio.sleep(300)  # Каждые 5 минут
            
            # Очищаем старые сообщения (старше 1 часа)
            message_cache.cleanup_old(max_age_seconds=3600)
            
            # Проверяем память если есть psutil
            if has_psutil:
                process = psutil.Process()
                mem_info = process.memory_info()
                mem_mb = mem_info.rss / 1024 / 1024
                
                cache_stats = message_cache.get_memory_usage()
                logger.debug(
                    f"💾 Memory: {mem_mb:.1f}MB | "
                    f"Cache: {cache_stats['total_chats']} chats, "
                    f"{cache_stats['total_messages']} messages"
                )
                
                # Если память больше 800MB (для хоста с 1GB) - агрессивная очистка
                if mem_mb > 800:
                    logger.warning(f"⚠️ High memory usage: {mem_mb:.1f}MB, cleaning caches...")
                    message_cache.cleanup_old(max_age_seconds=600)  # Удаляем старше 10 минут
                    
                    # Очищаем старые auth_states (старше 30 минут)
                    from utils.bot_manager import auth_states
                    import time
                    current_time = time.time()
                    to_remove = []
                    for user_id, state in auth_states.items():
                        if 'timestamp' in state:
                            if current_time - state['timestamp'] > 1800:  # 30 минут
                                to_remove.append(user_id)
                    for user_id in to_remove:
                        auth_states.pop(user_id, None)
                        logger.debug(f"Removed old auth state for user {user_id}")
                    
                    # Форсим garbage collection
                    import gc
                    gc.collect()
                    
        except Exception as e:
            logger.error(f"Ошибка в memory_monitor: {e}")

async def run_with_restart(coro, name, max_restarts=10):
    """Запускает корутину с автоматическим перезапуском при ошибках"""
    restart_count = 0
    while restart_count < max_restarts:
        try:
            await coro
        except asyncio.CancelledError:
            logger.info(f"{name} отменен")
            break
        except Exception as e:
            restart_count += 1
            logger.error(f"Ошибка в {name} (перезапуск {restart_count}/{max_restarts}): {e}", exc_info=True)
            if restart_count < max_restarts:
                wait_time = min(5 * restart_count, 60)  # Максимум 60 секунд
                logger.info(f"Перезапуск {name} через {wait_time} секунд...")
                await asyncio.sleep(wait_time)
            else:
                logger.critical(f"{name} достиг максимального количества перезапусков")
        else:
            # Если корутина завершилась нормально, выходим
            break

async def main():
    """Главная функция"""
    logger.info("🚀 Запуск KidHik Multi-User System...")
    print("🚀 Запуск KidHik Multi-User System...")
    
    # Инициализируем БД
    try:
        init_db()
        logger.info("✅ База данных инициализирована")
        print("✅ База данных инициализирована")
    except Exception as e:
        logger.critical(f"Критическая ошибка инициализации БД: {e}", exc_info=True)
        return
    
    # Инициализируем FunStat API
    if FUNSTAT_TOKEN:
        init_funstat(FUNSTAT_TOKEN)
    else:
        logger.warning("⚠️ FunStat токен не установлен, команды истории будут недоступны")
    
    # Запускаем задачи с автоматическим перезапуском
    try:
        await asyncio.gather(
            run_with_restart(instance_manager.start_all(), "Instance Manager"),
            run_with_restart(start_bot_manager(), "Bot Manager"),
            run_with_restart(memory_monitor(), "Memory Monitor"),
            run_with_restart(cleanup_temp_files(), "Temp Files Cleaner"),
            return_exceptions=True
        )
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"Критическая ошибка в главном цикле: {e}", exc_info=True)

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Обработка сигналов завершения (Unix)
    if sys.platform != 'win32':
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(shutdown(loop, signal=s)))
    
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        # Для Windows/KeyboardInterrupt
        loop.run_until_complete(shutdown(loop))
    finally:
        loop.close()
