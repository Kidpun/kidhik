# 🎵 Настройка Spotify API для команды .музыка

## Шаг 1: Создание приложения на Spotify Developer Dashboard

1. Перейдите на [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Войдите в свой аккаунт Spotify (или создайте новый)
3. Нажмите **"Create app"** или **"Create an app"**
4. Заполните форму:
   - **App name**: любое название (например, "KidHik Music Bot")
   - **App description**: описание (опционально)
   - **Redirect URI**: `http://localhost:8888/callback`
   - Примите условия использования
5. Нажмите **"Save"**

## Шаг 2: Получение Client ID и Client Secret

1. После создания приложения вы увидите страницу с информацией о приложении
2. Найдите:
   - **Client ID** - это строка вида `a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6`
   - **Client Secret** - нажмите **"View client secret"** или **"Show client secret"** чтобы увидеть секретный ключ (строка вида `1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p`)

## Шаг 3: Настройка Redirect URI

1. В настройках приложения найдите раздел **"Redirect URIs"**
2. Убедитесь, что добавлен URI: `http://localhost:8888/callback`
3. Если его нет - добавьте и сохраните

## Шаг 4: Предоставление данных

Отправьте мне следующие данные:
- **SPOTIFY_CLIENT_ID**: ваш Client ID
- **SPOTIFY_CLIENT_SECRET**: ваш Client Secret

Я добавлю их в `.env` файл.

## Важно

- Client Secret - это секретный ключ, не делитесь им публично
- Redirect URI должен быть точно `http://localhost:8888/callback`
- После добавления данных в `.env`, перезапустите бота

## Использование

После настройки:
1. Используйте команду `.музыка` в любом чате
2. При первом использовании бот попросит авторизоваться через Spotify
3. После авторизации команда будет показывать текущий трек

