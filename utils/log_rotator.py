"""
Ротация логов - очистка каждые 6 часов
"""
import os
import logging
import threading
from datetime import datetime
from pathlib import Path
import pytz

# Импортируем earth_anim лениво, чтобы избежать циклических импортов
def get_earth_anim():
    from utils.earth_animation import earth_anim
    return earth_anim


class RotatingFileHandler(logging.FileHandler):
    """FileHandler с автоматической ротацией каждые 6 часов"""

    def __init__(self, filename, mode='a', encoding='utf-8', delay=False):
        self.filename = filename
        self.last_rotation_hour = None
        super().__init__(filename, mode, encoding, delay)
        self._start_rotation_thread()

    def _start_rotation_thread(self):
        """Запускает поток для проверки времени ротации"""
        def check_rotation():
            import time
            msk_tz = pytz.timezone('Europe/Moscow')
            # Инициализируем час при старте (ближайший кратный 6 часам)
            if self.last_rotation_hour is None:
                now = datetime.now(msk_tz)
                # Вычисляем последний прошедший 6-часовой интервал
                self.last_rotation_hour = (now.hour // 6) * 6

            while True:
                try:
                    now = datetime.now(msk_tz)
                    current_6h_period = (now.hour // 6) * 6

                    # Если наступил новый 6-часовой интервал
                    if current_6h_period != self.last_rotation_hour:
                        self._rotate()
                        self.last_rotation_hour = current_6h_period
                        logging.getLogger(__name__).info(f"Логи очищены в {now.strftime('%H:%M')} МСК (каждые 6 часов)")

                    # Проверяем каждые 5 минут (300 секунд)
                    time.sleep(300)
                except Exception as e:
                    logging.getLogger(__name__).error(f"Ошибка в ротации логов: {e}")
                    time.sleep(300)

        thread = threading.Thread(target=check_rotation, daemon=True)
        thread.start()
    
    def _rotate(self):
        """Очищает файл лога (ротация каждые 6 часов)"""
        try:
            # Получаем размер файла до очистки
            file_size_before = 0
            if os.path.exists(self.filename):
                file_size_before = os.path.getsize(self.filename)

            self.close()
            # Очищаем файл полностью
            with open(self.filename, 'w', encoding='utf-8') as f:
                f.write('')
            # Переоткрываем файл
            self.stream = self._open()

            # Вычисляем освобожденное место
            file_size_after = 0
            if os.path.exists(self.filename):
                file_size_after = os.path.getsize(self.filename)

            freed_space = file_size_before - file_size_after
            if freed_space > 0:
                freed_mb = freed_space / (1024 * 1024)
                logging.getLogger(__name__).info(f"Логи очищены: освобождено {freed_mb:.2f} MB (ротация каждые 6 часов)")
            else:
                logging.getLogger(__name__).info("Файл логов очищен (ротация каждые 6 часов)")

        except Exception as e:
            logging.getLogger(__name__).error(f"Ошибка ротации логов: {e}")
            print(f"Ошибка ротации логов: {e}")


class TerminalErrorHandler(logging.Handler):
    """Handler для вывода только критических ошибок в терминал"""
    
    def emit(self, record):
        """Выводит только ERROR и CRITICAL в терминал через earth_animation"""
        if record.levelno >= logging.ERROR:
            try:
                msg = self.format(record)
                # Убираем лишние символы форматирования
                msg = msg.replace('\n', ' ')
                earth_anim = get_earth_anim()
                earth_anim.add_error(msg)
            except Exception:
                pass


def setup_logging(log_file='kidhik.log'):
    """Настраивает логирование с ротацией и анимацией"""
    log_path = Path(__file__).parent.parent / log_file
    
    # Создаём директорию если нужно
    log_path.parent.mkdir(exist_ok=True)
    
    # Очищаем файл при первом запуске (или оставляем старые логи)
    # Можно раскомментировать для очистки:
    # if log_path.exists():
    #     log_path.unlink()
    
    # Настраиваем root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Удаляем существующие handlers
    root_logger.handlers.clear()
    
    # File handler с ротацией
    file_handler = RotatingFileHandler(str(log_path), encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    
    # Terminal handler для вывода в консоль (INFO и выше)
    import sys
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S')
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # Terminal handler только для ошибок (через earth_animation, если нужно)
    terminal_handler = TerminalErrorHandler()
    terminal_handler.setLevel(logging.ERROR)
    terminal_formatter = logging.Formatter('%(levelname)s: %(message)s')
    terminal_handler.setFormatter(terminal_formatter)
    root_logger.addHandler(terminal_handler)
    
    # Снижаем шум от библиотек
    logging.getLogger('telethon').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    
    # Отключаем шумные WARNING от аудио-библиотек
    logging.getLogger('symphonia').setLevel(logging.ERROR)
    logging.getLogger('symphonia_core').setLevel(logging.ERROR)
    logging.getLogger('symphonia_bundle_mp3').setLevel(logging.ERROR)
    logging.getLogger('symphonia_bundle_mp3.demuxer').setLevel(logging.ERROR)
    logging.getLogger('symphonia_bundle_mp3.parser').setLevel(logging.ERROR)
    
    # Также отключаем шум от shazamio, если есть
    logging.getLogger('shazamio').setLevel(logging.WARNING)
    
    return root_logger


def cleanup_logs_manual():
    """Ручная очистка логов (можно вызывать по команде)"""
    try:
        log_file = Path(__file__).parent.parent / 'kidhik.log'
        if log_file.exists():
            file_size_before = log_file.stat().st_size
            log_file.write_text('', encoding='utf-8')
            freed_mb = file_size_before / (1024 * 1024)
            logging.getLogger(__name__).info(f"Логи очищены вручную: освобождено {freed_mb:.2f} MB")
            return True
        else:
            logging.getLogger(__name__).warning("Файл логов не найден для ручной очистки")
            return False
    except Exception as e:
        logging.getLogger(__name__).error(f"Ошибка ручной очистки логов: {e}")
        return False


def cleanup_temp_files():
    """Очистка временных файлов и кэшей"""
    try:
        import shutil
        from pathlib import Path

        # Директория проекта
        project_dir = Path(__file__).parent.parent
        cleaned_files = 0
        freed_space = 0

        # Очищаем __pycache__ директории
        for pycache_dir in project_dir.rglob('__pycache__'):
            if pycache_dir.is_dir():
                try:
                    shutil.rmtree(pycache_dir)
                    cleaned_files += 1
                    logging.getLogger(__name__).debug(f"Удалена директория: {pycache_dir}")
                except Exception as e:
                    logging.getLogger(__name__).debug(f"Не удалось удалить {pycache_dir}: {e}")

        # Очищаем .pyc файлы
        for pyc_file in project_dir.rglob('*.pyc'):
            try:
                file_size = pyc_file.stat().st_size
                pyc_file.unlink()
                freed_space += file_size
                cleaned_files += 1
            except Exception as e:
                logging.getLogger(__name__).debug(f"Не удалось удалить {pyc_file}: {e}")

        if cleaned_files > 0 or freed_space > 0:
            freed_mb = freed_space / (1024 * 1024)
            logging.getLogger(__name__).info(f"Очищено временных файлов: {cleaned_files}, освобождено: {freed_mb:.2f} MB")

        return cleaned_files, freed_space

    except Exception as e:
        logging.getLogger(__name__).error(f"Ошибка очистки временных файлов: {e}")
        return 0, 0

