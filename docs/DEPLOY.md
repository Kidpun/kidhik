# 🚀 Инструкция по установке и запуску KidHik Bot на Debian 12

> **Версия скрипта:** 2.0  
> **Оптимизации:** Прогресс-бары, валидация, улучшенная обработка ошибок, логирование

## 📋 Требования

- Debian 12 (или другая Linux система)
- Python 3.11 или 3.12 (рекомендуется 3.11)
- Root доступ или sudo права
- Минимум 512MB RAM
- Стабильное интернет-соединение

## 🚀 Быстрая установка (рекомендуется)

### Автоматическая установка через скрипт:

```bash
# 1. Скопируйте все файлы проекта на сервер в /root/kidhik/scr/kidhik
# 2. Запустите оптимизированный скрипт установки:
chmod +x deploy.sh
./deploy.sh
```

**Что делает скрипт:**
- ✅ Автоматически проверяет систему и зависимости
- ✅ Оптимизирует установку пакетов (пропускает уже установленные)
- ✅ Показывает прогресс-бары и красивый вывод
- ✅ Валидирует установку после завершения
- ✅ Создает systemd сервис с оптимизированными настройками
- ✅ Логирует все действия в `/tmp/kidhik_deploy.log`

## 🔧 Ручная установка (если нужен контроль)

### Шаг 1: Подготовка системы

```bash
# Обновляем систему
apt update && apt upgrade -y

# Устанавливаем необходимые пакеты
apt install -y python3 python3-pip python3-venv git curl nano build-essential python3-dev

# Проверяем версию Python (должна быть 3.10+)
python3 --version
```

### Шаг 2: Создание директории и клонирование проекта

```bash
# Создаем директорию для бота
mkdir -p /root/kidhik/scr/kidhik
cd /root/kidhik/scr/kidhik

# Скопируйте все файлы проекта сюда
# Или используйте git (если проект в репозитории):
# git clone <your-repo-url> .
```

### Шаг 3: Создание виртуального окружения

```bash
# Создаем виртуальное окружение
python3 -m venv /root/kidhik/venv

# Активируем виртуальное окружение
source /root/kidhik/venv/bin/activate

# Обновляем pip
pip install --upgrade pip setuptools wheel
```

### Шаг 4: Установка зависимостей

```bash
# Используйте оптимизированный скрипт:
./install.sh

# Или вручную:
pip install -r requirements.txt
pip install "aiohttp>=3.9.0" --no-build-isolation
```

## ⚙️ Шаг 5: Настройка переменных окружения

Создайте файл `.env` в директории проекта:

```bash
cd /root/kidhik/scr/kidhik
nano .env
```

Добавьте следующие переменные (замените значения на свои):

```env
# Telegram API (получите на https://my.telegram.org/apps)
API_ID=ваш_api_id
API_HASH=ваш_api_hash

# Токен бота-помощника (получите у @BotFather)
BOT_TOKEN=ваш_bot_token

# ID владельца бота (ваш Telegram ID)
OWNER_ID=123456789

# Spotify API (опционально, для функции музыки)
SPOTIFY_CLIENT_ID=ваш_spotify_client_id
SPOTIFY_CLIENT_SECRET=ваш_spotify_client_secret
SPOTIFY_REDIRECT_URI=https://kidwork.live/spotify/callback.html

# Яндекс Музыка (опционально)
YANDEX_CLIENT_ID=23cabbbdc6cd418abb4b39c32c41195d
YANDEX_REDIRECT_URI=https://kidwork.live/spotify/yandex_callback.html

# Языковые настройки (опционально)
LANG_CODE=ru
SYSTEM_LANG_CODE=en-US
```

Сохраните файл: `Ctrl+O`, `Enter`, `Ctrl+X`

## 📁 Шаг 6: Создание необходимых директорий

```bash
# Создаем необходимые директории (если их нет)
mkdir -p sessions session data deleted_messages saved_media temp_media text

# Устанавливаем права доступа
chmod 755 sessions session data deleted_messages saved_media temp_media text
```

## 🧪 Шаг 7: Первый запуск (тест)

```bash
# Убедитесь, что виртуальное окружение активировано
source /root/kidhik/venv/bin/activate

# Запускаем бота
cd /root/kidhik/scr/kidhik
python3 main.py
```

При первом запуске бот попросит:
1. Ввести номер телефона
2. Ввести код подтверждения из Telegram
3. Если включена 2FA, ввести пароль

После успешного запуска остановите бота: `Ctrl+C`

## 🔄 Шаг 8: Настройка автозапуска через systemd

Создайте файл сервиса:

```bash
nano /etc/systemd/system/kidhik.service
```

Добавьте следующее содержимое:

```ini
[Unit]
Description=KidHik Userbot Service
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/kidhik/scr/kidhik
ExecStart=/root/kidhik/venv/bin/python main.py
Restart=always
RestartSec=10
StandardOutput=append:/root/kidhik/scr/kidhik/kidhik.log
StandardError=append:/root/kidhik/scr/kidhik/kidhik.log

# Ограничения ресурсов (оптимизация)
LimitNOFILE=65536
MemoryMax=512M
CPUQuota=100%

# Переменные окружения
Environment="PATH=/root/kidhik/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Environment="PYTHONUNBUFFERED=1"

[Install]
WantedBy=multi-user.target
```

Сохраните и активируйте сервис:

```bash
# Перезагружаем systemd
systemctl daemon-reload

# Включаем автозапуск
systemctl enable kidhik.service

# Запускаем сервис
systemctl start kidhik.service

# Проверяем статус
systemctl status kidhik.service
```

## 📊 Управление сервисом

```bash
# Запустить бота
systemctl start kidhik

# Остановить бота
systemctl stop kidhik

# Перезапустить бота
systemctl restart kidhik

# Посмотреть статус
systemctl status kidhik

# Посмотреть логи
journalctl -u kidhik -f

# Или логи из файла
tail -f /root/kidhik/scr/kidhik/kidhik.log
```

## 🔍 Проверка работы

1. **Проверьте логи:**
   ```bash
   tail -f /root/kidhik/scr/kidhik/kidhik.log
   ```

2. **Проверьте статус сервиса:**
   ```bash
   systemctl status kidhik
   ```

3. **Проверьте в Telegram:**
   - Отправьте команду `.помощь` боту-помощнику
   - Попробуйте команду `.музыка` (если настроен Spotify/Yandex)

## 🛠️ Решение проблем

### Проблема: Бот не запускается

1. Проверьте логи установки:
   ```bash
   cat /tmp/kidhik_deploy.log
   ```

2. Проверьте логи бота:
   ```bash
   journalctl -u kidhik -n 50
   # или
   tail -100 /root/kidhik/scr/kidhik/kidhik.log
   ```

3. Проверьте права доступа:
   ```bash
   chmod +x /root/kidhik/venv/bin/python
   chmod 600 /root/kidhik/scr/kidhik/.env
   chmod 755 /root/kidhik/scr/kidhik/sessions
   ```

4. Проверьте переменные окружения:
   ```bash
   cat /root/kidhik/scr/kidhik/.env
   ```

5. Запустите валидацию:
   ```bash
   cd /root/kidhik/scr/kidhik
   source /root/kidhik/venv/bin/activate
   python3 -c "import telethon, aiohttp, spotipy; print('OK')"
   ```

### Проблема: Ошибки импорта модулей

```bash
# Используйте оптимизированный скрипт:
cd /root/kidhik/scr/kidhik
./install.sh

# Или вручную:
source /root/kidhik/venv/bin/activate
pip install --upgrade -r requirements.txt
pip install "aiohttp>=3.9.0" --no-build-isolation
```

### Проблема: Сессия не сохраняется

```bash
# Проверьте права на директорию sessions
chmod 755 /root/kidhik/scr/kidhik/sessions
chmod 644 /root/kidhik/scr/kidhik/sessions/*.session 2>/dev/null || true
```

### Проблема: Бот падает с ошибкой

1. Проверьте логи:
   ```bash
   tail -f /root/kidhik/scr/kidhik/kidhik.log
   ```

2. Проверьте статус сервиса:
   ```bash
   systemctl status kidhik
   ```

3. Перезапустите сервис:
   ```bash
   systemctl restart kidhik
   ```

4. Проверьте использование ресурсов:
   ```bash
   systemctl status kidhik | grep -A 5 "Memory\|CPU"
   ```

### Проблема: Медленная работа

1. Проверьте ограничения ресурсов в systemd:
   ```bash
   cat /etc/systemd/system/kidhik.service | grep -E "Memory\|CPU"
   ```

2. Увеличьте лимиты при необходимости (отредактируйте сервис)

## 📝 Обновление бота

```bash
# Останавливаем бота
systemctl stop kidhik

# Делаем бэкап (рекомендуется)
cp -r /root/kidhik /root/kidhik_backup_$(date +%Y%m%d)

# Обновляем код (если используете git)
cd /root/kidhik/scr/kidhik
git pull

# Обновляем зависимости
source /root/kidhik/venv/bin/activate
pip install --upgrade -r requirements.txt

# Запускаем бота
systemctl start kidhik
```

## 🔐 Безопасность

1. **Защитите файл .env:**
   ```bash
   chmod 600 /root/kidhik/scr/kidhik/.env
   ```

2. **Не публикуйте .env файл в репозиторий**

3. **Регулярно обновляйте зависимости:**
   ```bash
   pip install --upgrade -r requirements.txt
   ```

## 📞 Дополнительная информация

- Логи сохраняются в: `/root/kidhik/scr/kidhik/kidhik.log`
- Сессии пользователей: `/root/kidhik/scr/kidhik/sessions/`
- Удаленные сообщения: `/root/kidhik/scr/kidhik/deleted_messages/`
- Сохраненное медиа: `/root/kidhik/scr/kidhik/saved_media/`

---

**Готово!** Бот должен работать в фоновом режиме и автоматически запускаться при перезагрузке сервера.

