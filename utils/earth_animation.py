"""
Красивая надпись KIDHIK ROOT с эффектом стекания символов
"""
import os
import sys
import time
import threading
import random
from datetime import datetime
import pytz
import logging

logger = logging.getLogger(__name__)

# ASCII арт для "KIDHIK ROOT"
KIDHIK_ASCII = """
██╗  ██╗██╗██████╗ ██╗  ██╗██╗██╗  ██╗
██║ ██╔╝██║██╔══██╗██║  ██║██║██║ ██╔╝
█████╔╝ ██║██║  ██║███████║██║█████╔╝ 
██╔═██╗ ██║██║  ██║██╔══██║██║██╔═██╗ 
██║  ██╗██║██████╔╝██║  ██║██║██║  ██╗
╚═╝  ╚═╝╚═╝╚═════╝ ╚═╝  ╚═╝╚═╝╚═╝  ╚═╝
                                       
██████╗  ██████╗  ██████╗ ████████╗
██╔══██╗██╔═══██╗██╔═══██╗   ██║   
██████╔╝██║   ██║██║   ██║   ██║   
██╔══██╗██║   ██║██║   ██║   ██║   
██║  ██║╚██████╔╝╚██████╔╝   ██║   
╚═╝  ╚═╝ ╚═════╝  ╚═════╝    ╚═╝   
"""


class TerminalDisplay:
    """Красивая надпись KIDHIK ROOT с эффектом стекания символов"""
    
    def __init__(self):
        self.running = False
        self.thread = None
        self.error_lines = []
        self.lock = threading.Lock()
        self.chars = "01"  # Символы для эффекта стекания
        self.columns = []
        self.column_positions = []
        self.title_lines = []
        self.visible_lines = 0  # Количество видимых строк надписи
        self.animation_complete = False
        
    def _get_terminal_size(self):
        """Получает размер терминала"""
        try:
            rows, cols = os.get_terminal_size()
            return rows, cols
        except:
            return 24, 80
    
    def _clear_screen(self):
        """Очищает экран используя ANSI escape codes"""
        sys.stdout.write('\033[2J\033[H')
        sys.stdout.flush()
    
    def _init_matrix_effect(self, cols):
        """Инициализирует эффект стекания для колонок"""
        if len(self.columns) != cols:
            self.columns = []
            self.column_positions = []
            for i in range(cols):
                self.columns.append(random.randint(-20, 0))
                self.column_positions.append(random.randint(0, 10))
    
    def _update_matrix_effect(self, rows):
        """Обновляет эффект стекания"""
        for i in range(len(self.columns)):
            if random.random() < 0.05:  # 5% шанс начать новую колонку
                self.columns[i] = 0
                self.column_positions[i] = random.randint(0, 10)
            else:
                self.columns[i] += 1
                if self.columns[i] > rows + 5:
                    self.columns[i] = random.randint(-20, 0)
    
    def _get_matrix_line(self, row, cols):
        """Получает строку с эффектом стекания для определенной строки"""
        line = ""
        for i in range(cols):
            col_pos = self.columns[i]
            if col_pos <= row < col_pos + 10:
                # Яркость зависит от позиции в колонке
                pos_in_col = row - col_pos
                if pos_in_col == 0:
                    line += random.choice(self.chars)
                elif pos_in_col < 8:
                    line += random.choice(self.chars)
                else:
                    line += ' '
            else:
                line += ' '
        return line
    
    def _get_title_lines(self):
        """Получает строки ASCII арта заголовка"""
        if not self.title_lines:
            lines = KIDHIK_ASCII.strip().split('\n')
            # Фильтруем пустые строки
            self.title_lines = [line for line in lines if line.strip()]
        return self.title_lines
    
    def add_error(self, error_msg):
        """Добавляет ошибку для отображения"""
        with self.lock:
            timestamp = datetime.now(pytz.timezone('Europe/Moscow')).strftime('%H:%M:%S')
            # Обрезаем длинные сообщения
            msg = error_msg[:80] if len(error_msg) > 80 else error_msg
            self.error_lines.append(f"[{timestamp}] {msg}")
            # Ограничиваем количество строк ошибок
            if len(self.error_lines) > 10:
                self.error_lines.pop(0)
    
    def _animate(self):
        """Анимационный цикл"""
        frame_count = 0
        
        while self.running:
            try:
                rows, cols = self._get_terminal_size()
                
                # Инициализируем эффект стекания
                self._init_matrix_effect(cols)
                self._update_matrix_effect(rows)
                
                # Получаем строки заголовка
                title_lines = self._get_title_lines()
                title_height = len(title_lines)
                
                # Вычисляем позиции
                with self.lock:
                    error_count = len(self.error_lines)
                    error_height = error_count + 3 if error_count > 0 else 0  # +3 для разделителя и заголовка
                
                # Вычисляем отступ сверху для заголовка
                top_padding = max(2, (rows - title_height - error_height) // 4)
                
                # Эффект стекания надписи: постепенно показываем строки сверху вниз
                if not self.animation_complete:
                    # Каждые 3 кадра добавляем одну строку
                    if frame_count % 3 == 0:
                        self.visible_lines = min(self.visible_lines + 1, title_height)
                    if self.visible_lines >= title_height:
                        self.animation_complete = True
                
                # Очищаем экран
                self._clear_screen()
                
                # Печатаем эффект стекания сверху
                for i in range(top_padding):
                    matrix_line = self._get_matrix_line(i, cols)
                    print(f'\033[32m{matrix_line}\033[0m')  # Зеленый цвет
                
                # Печатаем заголовок с эффектом стекания
                for i, line in enumerate(title_lines):
                    if i < self.visible_lines:
                        padding = max(0, (cols - len(line)) // 2)
                        # Яркий белый цвет для заголовка
                        print(' ' * padding + f'\033[1m\033[37m{line}\033[0m')
                    else:
                        # Показываем матричный эффект вместо невидимых строк
                        matrix_line = self._get_matrix_line(top_padding + i, cols)
                        print(f'\033[32m{matrix_line}\033[0m')
                
                # Печатаем эффект стекания между заголовком и ошибками
                remaining_rows = rows - top_padding - title_height - error_height
                for i in range(min(remaining_rows, 5)):
                    row_idx = top_padding + title_height + i
                    matrix_line = self._get_matrix_line(row_idx, cols)
                    print(f'\033[32m{matrix_line}\033[0m')
                
                # Печатаем ошибки снизу
                with self.lock:
                    if self.error_lines:
                        print()
                        separator = "─" * min(70, cols - 4)
                        padding = max(0, (cols - len(separator)) // 2)
                        print(" " * padding + f'\033[31m{separator}\033[0m')  # Красный разделитель
                        print(" " * padding + f'\033[31mОшибки:\033[0m')
                        for error_line in self.error_lines[-8:]:  # Последние 8 ошибок
                            padding_err = max(0, (cols - len(error_line)) // 2)
                            print(" " * padding_err + f'\033[33m{error_line}\033[0m')  # Желтый цвет для ошибок
                
                frame_count += 1
                # Обновляем каждые 0.1 секунды для плавной анимации
                time.sleep(0.1)
                
            except Exception as e:
                logger.debug(f"Ошибка в анимации: {e}")
                time.sleep(0.5)
    
    def start(self):
        """Запускает анимацию"""
        if self.running:
            return
        
        # Сбрасываем состояние анимации
        self.visible_lines = 0
        self.animation_complete = False
        
        self.running = True
        self.thread = threading.Thread(target=self._animate, daemon=True)
        self.thread.start()
    
    def stop(self):
        """Останавливает анимацию"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)
        self._clear_screen()


# Глобальный экземпляр (переименовываем для совместимости)
earth_anim = TerminalDisplay()
