# Быстрая установка (для Python 3.14)

Если у вас Python 3.14 и возникают проблемы с компиляцией aiohttp, выполните:

```bash
cd /Users/kid/Desktop/python/scr/kidhik

# Шаг 1: Обновите pip
pip3 install --upgrade pip setuptools wheel

# Шаг 2: Установите aiohttp отдельно (попробуйте предкомпилированные wheels)
pip3 install "aiohttp>=3.9.0" --only-binary :all: || pip3 install "aiohttp>=3.9.0"

# Шаг 3: Установите остальные зависимости
pip3 install aiogram==2.25.1 spotipy python-dotenv

# Шаг 4: Запустите бота
python3 main.py
```

Если это не работает, используйте Python 3.11 или 3.12 (см. INSTALL_FIX.md).





































