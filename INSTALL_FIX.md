# Решение проблемы установки зависимостей

## Проблема
Python 3.14 слишком новый, и `aiohttp` не может скомпилироваться из исходников.

## Решения

### Вариант 1: Использовать Python 3.11 или 3.12 (рекомендуется)

```bash
# Установите Python 3.11 или 3.12 через pyenv или Homebrew
brew install python@3.11

# Используйте его для проекта
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

### Вариант 2: Установить предкомпилированные wheels

```bash
cd /Users/kid/Desktop/python/scr/kidhik

# Обновите pip и установите wheel
pip3 install --upgrade pip setuptools wheel

# Попробуйте установить aiohttp из предкомпилированных wheels
pip3 install aiohttp --only-binary :all:

# Если не работает, попробуйте установить более новую версию
pip3 install "aiohttp>=3.9.0" --only-binary :all:

# Затем установите остальные зависимости
pip3 install aiogram==2.25.1 spotipy python-dotenv
```

### Вариант 3: Использовать системный Python (если есть)

```bash
# Проверьте версию системного Python
/usr/bin/python3 --version

# Если это Python 3.11 или 3.12, используйте его
/usr/bin/python3 -m pip install -r requirements.txt
/usr/bin/python3 main.py
```

### Вариант 4: Установить через conda/miniconda

```bash
# Создайте окружение с Python 3.11
conda create -n kidhik python=3.11
conda activate kidhik
pip install -r requirements.txt
python main.py
```

## Быстрое решение (попробуйте сначала)

```bash
cd /Users/kid/Desktop/python/scr/kidhik
pip3 install --upgrade pip setuptools wheel
pip3 install "aiohttp>=3.9.0" --only-binary :all: || pip3 install aiohttp
pip3 install aiogram==2.25.1 spotipy python-dotenv
python3 main.py
```





































