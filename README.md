<div align="center">

<img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/People/Robot.png" width="100" alt="KidHik"/>

# KidHik Userbot

**Мощный Telegram userbot с 40+ командами**

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Telethon](https://img.shields.io/badge/Telethon-latest-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white)](https://github.com/LonamiWebs/Telethon)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)
[![Deploy: Server](https://img.shields.io/badge/Deploy-Server%20Only-red?style=for-the-badge&logo=linux&logoColor=white)](https://github.com/Kidpun/kidhik)

> ⚠️ **Предназначен для запуска только на сервере (VPS/Linux).** Локальный запуск не рекомендуется.

</div>

---

## 🚀 Возможности

<details>
<summary><b>📋 Все команды (нажми, чтобы раскрыть)</b></summary>

### 🛠 Утилиты
| Команда | Описание |
|---|---|
| `.помощь` | Список всех команд |
| `.пинг` | Пинг до серверов Telegram |
| `.whoami` | Информация о себе |
| `.calc <выражение>` | Калькулятор: `.calc 2^10 + 5*3` |
| `.напомни <время> <текст>` | Напоминание: `.напомни 10м позвонить` |
| `.tr <текст>` | Перевод текста |
| `.тайп <текст>` | Эффект печатания |
| `.стоп` | Остановить активные задачи |

### 👤 OSINT / Профили
| Команда | Описание |
|---|---|
| `.инфо @user` | Информация о пользователе |
| `.id @user` | Получить Telegram ID |
| `.пробив @user` | Пробив через OSINT |
| `.история @user` | История изменений профиля |
| `.юзернейм_история @user` | История юзернеймов |
| `.фото_история @user` | История фото профиля |
| `.связи @user` | Связанные аккаунты |
| `.слежка @user` | Слежка за пользователем |

### 🌐 Сеть
| Команда | Описание |
|---|---|
| `.ip <ip>` | Информация об IP |
| `.домен <домен>` | Данные о домене |
| `.whois <домен>` | WHOIS запрос |
| `.поиск_номер <номер>` | Поиск по номеру телефона |

### 🎵 Медиа
| Команда | Описание |
|---|---|
| `.музыка` | Поиск музыки через Spotify |
| `.шазам` | Распознавание аудио/голосовых |
| `.dl <ссылка>` | Скачивание видео/аудио |
| `.круг` | Конвертировать видео в кружок |

### 🎲 Развлечения
| Команда | Описание |
|---|---|
| `.цитата` | Цитата дня |
| `.факт` | Случайный факт |
| `.монетка` | Подбросить монетку |
| `.статья` | Случайная статья Wikipedia |
| `.бреинрот` | Brainrot генератор |
| `.процент <вопрос>` | Шанс в процентах |

### 🤖 Авто-функции
| Команда | Описание |
|---|---|
| `.откат` | Авто-ответ на "откат" в чатах |
| `.троль` | Режим троллинга |
| `.снос` | Снос спамеров |
| `.реакции` | Авто-реакции |
| `.чек` | Ловец чеков |
| `.игнор @user` | Игнорировать пользователя |
| `.статистика` | Статистика бота |

</details>

---

## 🧰 Стек технологий

| Технология | Назначение |
|---|---|
| ![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white) **Python 3.10+** | Основной язык |
| ![Telegram](https://img.shields.io/badge/Telethon-2CA5E0?style=flat&logo=telegram&logoColor=white) **Telethon** | MTProto Telegram API клиент |
| ![Spotify](https://img.shields.io/badge/Spotify_API-1DB954?style=flat&logo=spotify&logoColor=white) **Spotify API** | Поиск и воспроизведение музыки |
| ![Yandex](https://img.shields.io/badge/Yandex_Music-FF0000?style=flat&logo=yandex&logoColor=white) **Yandex Music** | Альтернативный источник музыки |
| ![Google](https://img.shields.io/badge/Gemini_AI-4285F4?style=flat&logo=google&logoColor=white) **Gemini AI** | AI-ответы и DDG поиск |
| **SQLite** | Локальная база данных |
| **python-dotenv** | Управление конфигурацией |

---

## ⚙️ Установка на сервер (VPS/Linux)

### 1. Клонировать репозиторий

```bash
git clone https://github.com/Kidpun/kidhik.git
cd kidhik
```

### 2. Создать виртуальное окружение

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Установить зависимости

```bash
pip install -r requirements.txt
```

### 4. Настроить конфиг

```bash
cp .env.example .env
nano .env
```

Заполнить обязательные поля:

| Переменная | Где взять |
|---|---|
| `API_ID` / `API_HASH` | [my.telegram.org/apps](https://my.telegram.org/apps) |
| `BOT_TOKEN` | [@BotFather](https://t.me/BotFather) |
| `SPOTIFY_CLIENT_ID/SECRET` | [developer.spotify.com](https://developer.spotify.com/dashboard) |
| `GEMINI_API_KEY` | [aistudio.google.com](https://aistudio.google.com) |

### 5. Запустить

```bash
python main.py
```

При первом запуске введи номер телефона и код подтверждения.

---

## 🖥 Запуск как systemd-сервис (рекомендуется для сервера)

```bash
sudo nano /etc/systemd/system/kidhik.service
```

```ini
[Unit]
Description=KidHik Userbot
After=network.target

[Service]
Type=simple
User=YOUR_USER
WorkingDirectory=/path/to/kidhik
ExecStart=/path/to/kidhik/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable kidhik
sudo systemctl start kidhik
sudo systemctl status kidhik
```

---

## 🌐 Прокси (опционально)

Добавь в `.env`:

```env
# SOCKS5
PROXY_URL=socks5://user:password@host:port

# HTTP
PROXY_URL=http://1.2.3.4:8080
```

---

## 🔒 Безопасность

- 🚫 **`.env` никогда не попадает в git** — он в `.gitignore`
- 🚫 **`*.session` файлы** тоже игнорируются
- ✅ `OWNER_ID` защищает все команды от чужих
- ✅ При подозрительной активности Telegram удалит сессию — бот уведомит тебя

---

## 📁 Структура проекта

```
kidhik/
├── main.py                 # Точка входа
├── config/
│   └── settings.py         # Все настройки из .env
├── commands/               # 40+ команд userbot
│   ├── calc.py             # Калькулятор
│   ├── remind.py           # Напоминания
│   ├── music.py            # Spotify + Yandex
│   ├── probiv.py           # OSINT
│   ├── network.py          # IP/WHOIS/домены
│   └── ...
├── handlers/               # Обработчики событий Telethon
├── utils/
│   ├── proxy.py            # Система прокси
│   ├── instance_manager.py # Менеджер сессий
│   ├── spotify.py          # Spotify OAuth
│   ├── yandex_music.py     # Yandex Music API
│   └── ...
├── data/                   # Runtime данные (gitignored)
├── text/                   # Текстовые базы (факты, brainrot и т.д.)
├── .env.example            # Шаблон конфига
└── requirements.txt
```

---

## 📄 Лицензия

MIT — делай что хочешь, но звёздочку поставь ⭐

---

<div align="center">

Made with ❤️ by [Kidpun](https://github.com/Kidpun)

</div>
