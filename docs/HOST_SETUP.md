# 🚀 Инструкция по установке KidHik Bot на хосте

## 📍 Текущая директория: `/home/allah/kidhik/`

---

## ⚡ Быстрая установка (пошагово)

### Шаг 1: Переход в директорию проекта

```bash
cd /home/allah/kidhik
```

### Шаг 2: Проверка Python

```bash
python3 --version
# Должно быть Python 3.10 или выше
```

Если Python не установлен:
```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv
```

### Шаг 3: Создание виртуального окружения

```bash
# Создаем venv в текущей директории
python3 -m venv venv

# Или если хотите в отдельной директории:
python3 -m venv /home/allah/kidhik/venv
```

### Шаг 4: Активация виртуального окружения

```bash
# Если venv в текущей директории:
source venv/bin/activate

# Или если в отдельной директории:
source /home/allah/kidhik/venv/bin/activate
```

**После активации в начале строки появится `(venv)`**

### Шаг 5: Обновление pip

```bash
pip install --upgrade pip setuptools wheel
```

### Шаг 6: Установка зависимостей

**Вариант А: Использовать оптимизированный скрипт (рекомендуется)**

```bash
# Убедитесь что скрипт исполняемый
chmod +x install.sh

# Запустите скрипт
./install.sh
```

**Вариант Б: Установка вручную**

```bash
# Сначала устанавливаем aiohttp (часто вызывает проблемы)
pip install "aiohttp>=3.9.0" --no-build-isolation

# Затем остальные зависимости
pip install -r requirements.txt
```

### Шаг 7: Проверка установки

```bash
# Проверяем что модули установлены
python3 -c "import telethon; print('telethon OK')"
python3 -c "import aiohttp; print('aiohttp OK')"
python3 -c "import spotipy; print('spotipy OK')"
python3 -c "import dotenv; print('dotenv OK')"
```

### Шаг 8: Создание необходимых директорий

```bash
mkdir -p sessions session data deleted_messages saved_media temp_media text
chmod 755 sessions session data deleted_messages saved_media temp_media text
```

### Шаг 9: Настройка .env файла

```bash
# Создаем .env файл если его нет
nano .env
```

Добавьте следующие переменные (замените на свои значения):

```env
# Telegram API (получите на https://my.telegram.org/apps)
API_ID=ваш_api_id
API_HASH=ваш_api_hash

# Токен бота-помощника (получите у @BotFather)
BOT_TOKEN=ваш_bot_token

# ID владельца бота
OWNER_ID=123456789

# Spotify API (опционально)
SPOTIFY_CLIENT_ID=
SPOTIFY_CLIENT_SECRET=
SPOTIFY_REDIRECT_URI=https://kidwork.live/spotify/callback.html

# Яндекс Музыка (опционально)
YANDEX_CLIENT_ID=23cabbbdc6cd418abb4b39c32c41195d
YANDEX_REDIRECT_URI=https://kidwork.live/spotify/yandex_callback.html

# Языковые настройки
LANG_CODE=ru
SYSTEM_LANG_CODE=en-US
```

Сохраните: `Ctrl+O`, `Enter`, `Ctrl+X`

Установите права:
```bash
chmod 600 .env
```

### Шаг 10: Первый запуск (для авторизации)

```bash
# Убедитесь что venv активирован
source venv/bin/activate

# Запустите бота
python3 main.py
```

При первом запуске:
1. Введите номер телефона (с кодом страны, например: +79991234567)
2. Введите код подтверждения из Telegram
3. Если включена 2FA, введите пароль

После успешной авторизации остановите бота: `Ctrl+C`

---

## 🔄 Настройка автозапуска через systemd

### Создание systemd сервиса

```bash
sudo nano /etc/systemd/system/kidhik.service
```

Добавьте следующее содержимое (замените пути если нужно):

```ini
[Unit]
Description=KidHik Userbot Service
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=allah
WorkingDirectory=/home/allah/kidhik
ExecStart=/home/allah/kidhik/venv/bin/python main.py
Restart=always
RestartSec=10
StandardOutput=append:/home/allah/kidhik/kidhik.log
StandardError=append:/home/allah/kidhik/kidhik.log

# Ограничения ресурсов
LimitNOFILE=65536
MemoryMax=512M
CPUQuota=100%

# Переменные окружения
Environment="PATH=/home/allah/kidhik/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Environment="PYTHONUNBUFFERED=1"

[Install]
WantedBy=multi-user.target
```

**Важно:** Замените `User=allah` на вашего пользователя, если он другой!

### Активация сервиса

```bash
# Перезагружаем systemd
sudo systemctl daemon-reload

# Включаем автозапуск
sudo systemctl enable kidhik

# Запускаем сервис
sudo systemctl start kidhik

# Проверяем статус
sudo systemctl status kidhik
```

---

## 📊 Управление ботом

### Через systemd:

```bash
# Запустить
sudo systemctl start kidhik

# Остановить
sudo systemctl stop kidhik

# Перезапустить
sudo systemctl restart kidhik

# Статус
sudo systemctl status kidhik

# Логи (systemd)
sudo journalctl -u kidhik -f

# Логи (файл)
tail -f /home/allah/kidhik/kidhik.log
```

### Ручной запуск:

```bash
cd /home/allah/kidhik
source venv/bin/activate
python3 main.py
```

---

## 🔍 Проверка работы

### 1. Проверка статуса сервиса:
```bash
sudo systemctl status kidhik
```

Должно быть: `Active: active (running)`

### 2. Проверка логов:
```bash
tail -50 /home/allah/kidhik/kidhik.log
```

### 3. Проверка в Telegram:
- Отправьте команду `.помощь` боту-помощнику
- Попробуйте команду `.музыка` (если настроен Spotify/Yandex)

---

## 🛠️ Решение проблем

### Проблема: "venv/bin/activate: No such file or directory"

**Решение:**
```bash
cd /home/allah/kidhik
python3 -m venv venv
source venv/bin/activate
```

### Проблема: "ModuleNotFoundError: No module named 'telethon'"

**Решение:**
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Проблема: "Permission denied" при установке

**Решение:**
```bash
# Убедитесь что venv активирован
source venv/bin/activate

# Используйте pip из venv, не системный pip3
which pip  # Должно показать путь к venv/bin/pip
```

### Проблема: Бот не запускается через systemd

**Решение:**
1. Проверьте логи:
   ```bash
   sudo journalctl -u kidhik -n 50
   ```

2. Проверьте права:
   ```bash
   ls -la /home/allah/kidhik/venv/bin/python
   chmod +x /home/allah/kidhik/venv/bin/python
   ```

3. Проверьте путь к venv:
   ```bash
   /home/allah/kidhik/venv/bin/python --version
   ```

### Проблема: "aiohttp не устанавливается"

**Решение:**
```bash
source venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install "aiohttp>=3.9.0" --no-build-isolation
```

---

## 📝 Краткая шпаргалка

```bash
# 1. Переход в директорию
cd /home/allah/kidhik

# 2. Создание venv (если еще не создан)
python3 -m venv venv

# 3. Активация venv
source venv/bin/activate

# 4. Установка зависимостей
pip install --upgrade pip
pip install -r requirements.txt

# 5. Создание директорий
mkdir -p sessions session data deleted_messages saved_media temp_media text

# 6. Настройка .env
nano .env  # Заполните переменные

# 7. Запуск
python3 main.py
```

---

## 📁 Структура директорий

```
/home/allah/kidhik/
├── venv/                    # Виртуальное окружение
├── sessions/                # Сессии пользователей
├── data/                    # База данных
├── deleted_messages/        # Удаленные сообщения
├── saved_media/             # Сохраненное медиа
├── temp_media/              # Временные файлы
├── text/                    # Текстовые файлы (facts.txt, brainrot.txt)
├── .env                     # Конфигурация (ВАЖНО: chmod 600)
├── main.py                  # Главный файл
├── requirements.txt         # Зависимости
└── kidhik.log              # Логи бота
```

---

**Готово!** Бот должен работать. Если возникнут проблемы, проверьте логи.




















