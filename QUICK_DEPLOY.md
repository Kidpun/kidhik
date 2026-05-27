# ⚡ Быстрая установка KidHik Bot на Debian 12

## 🚀 Автоматическая установка (рекомендуется)

```bash
# 1. Скопируйте все файлы проекта на сервер в /root/kidhik/scr/kidhik
# 2. Запустите скрипт установки:
chmod +x deploy.sh
./deploy.sh

# 3. Отредактируйте .env файл:
nano /root/kidhik/scr/kidhik/.env

# 4. Запустите бота вручную для первой авторизации:
cd /root/kidhik/scr/kidhik
source /root/kidhik/venv/bin/activate
python3 main.py

# 5. После авторизации (Ctrl+C) включите автозапуск:
systemctl enable kidhik
systemctl start kidhik
```

## 📋 Ручная установка

```bash
# 1. Обновление системы
apt update && apt upgrade -y
apt install -y python3 python3-pip python3-venv git

# 2. Создание окружения
mkdir -p /root/kidhik/scr/kidhik
cd /root/kidhik/scr/kidhik
python3 -m venv /root/kidhik/venv
source /root/kidhik/venv/bin/activate

# 3. Установка зависимостей
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

# 4. Создание директорий
mkdir -p sessions session data deleted_messages saved_media temp_media text

# 5. Создание .env файла
nano .env  # Заполните переменные окружения

# 6. Первый запуск
python3 main.py  # Авторизуйтесь, затем Ctrl+C

# 7. Создание systemd сервиса
nano /etc/systemd/system/kidhik.service
# Скопируйте содержимое из DEPLOY.md

# 8. Активация сервиса
systemctl daemon-reload
systemctl enable kidhik
systemctl start kidhik
```

## 🎮 Управление ботом

```bash
# Запуск
systemctl start kidhik

# Остановка
systemctl stop kidhik

# Перезапуск
systemctl restart kidhik

# Статус
systemctl status kidhik

# Логи (systemd)
journalctl -u kidhik -f

# Логи (файл)
tail -f /root/kidhik/scr/kidhik/kidhik.log
```

## ⚙️ Переменные окружения (.env)

```env
API_ID=ваш_api_id
API_HASH=ваш_api_hash
BOT_TOKEN=ваш_bot_token
OWNER_ID=7591325579
SPOTIFY_CLIENT_ID=...
SPOTIFY_CLIENT_SECRET=...
SPOTIFY_REDIRECT_URI=https://kidwork.live/spotify/callback.html
```

## 🔧 Решение проблем

```bash
# Переустановка зависимостей
source /root/kidhik/venv/bin/activate
pip install --upgrade -r requirements.txt

# Проверка прав доступа
chmod 600 /root/kidhik/scr/kidhik/.env
chmod 755 /root/kidhik/scr/kidhik/sessions

# Просмотр ошибок
journalctl -u kidhik -n 100 --no-pager
```

## 📁 Важные пути

- Проект: `/root/kidhik/scr/kidhik`
- Логи: `/root/kidhik/scr/kidhik/kidhik.log`
- Сессии: `/root/kidhik/scr/kidhik/sessions/`
- Конфиг: `/root/kidhik/scr/kidhik/.env`
- Сервис: `/etc/systemd/system/kidhik.service`

---

📖 **Подробная инструкция:** См. `DEPLOY.md`




















