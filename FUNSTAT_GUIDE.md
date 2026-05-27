# 🕵️ FunStat API - История изменений профилей Telegram

## 📝 Что это?

**FunStat** ([funstat.info](https://funstat.info)) - сервис для получения истории изменений профилей Telegram:
- История username
- История имени/фамилии
- История фото профиля
- История описания (bio)
- История номеров телефона
- Связанные пользователи
- Поиск по номеру

---

## 🔑 Установка токена

### 1. Получите токен

У вас уже есть токен:
```
eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1aWQiOiI3NTkxMzI1NTc5IiwianRpIjoiN2NlYjI0YzgtOGM1NC00ZTc5LTk3YmQtZGVmYTQyZWE4N2VkIiwiZXhwIjoxNzk5NDg1Njg0fQ.UBPdJRwMH71uXaPnjP0zXSko2DKuecMsgq9rBy58Z-raWdAuR6fO6EECwszXMX6WGRRIxPPC9B62WHJtL9jKj5Em7IILIr04FYMfS5_Dt3nan0Zl49HHawi3pFPbo9KSuK8shCvG1UOn0ulXbzyWeMiuMQwIr_DWcdOicIX7VLs
```

### 2. Добавьте в `.env`

Создайте файл `.env` в корне проекта:
```bash
cd /home/allah/kidhik
nano .env
```

Добавьте строку:
```env
FUNSTAT_TOKEN="eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1aWQiOiI3NTkxMzI1NTc5IiwianRpIjoiN2NlYjI0YzgtOGM1NC00ZTc5LTk3YmQtZGVmYTQyZWE4N2VkIiwiZXhwIjoxNzk5NDg1Njg0fQ.UBPdJRwMH71uXaPnjP0zXSko2DKuecMsgq9rBy58Z-raWdAuR6fO6EECwszXMX6WGRRIxPPC9B62WHJtL9jKj5Em7IILIr04FYMfS5_Dt3nan0Zl49HHawi3pFPbo9KSuK8shCvG1UOn0ulXbzyWeMiuMQwIr_DWcdOicIX7VLs"
```

### 3. Перезапустите бота

```bash
# Остановите (Ctrl+C)
# Запустите снова
python3 main.py
```

---

## 📖 Команды

### `.история @user` - Полная история

Показывает все изменения профиля:
```
.история @username
```

**Или реплай:**
```
(ответить на сообщение)
.история
```

**Пример вывода:**
```
📊 История изменений профиля
🆔 ID: 123456789

📱 История Username:
  • @old_username — 15.04.2024 12:30
  • @new_username — 20.05.2024 18:45
  • @current_username — 01.12.2024 09:15

📝 История имени:
  • Иван Петров — 10.03.2024 10:00
  • Ivan Petrov — 15.04.2024 12:30

🖼 История фото:
  Всего изменений: 15
  Последнее: 01.12.2024 09:15

📞 Известные номера:
  • +79991234567 — 15.04.2024 12:30

⭐ Telegram Premium
```

---

### `.юзернейм_история @user` - История username

Только изменения username:
```
.юзернейм_история @username
```

---

### `.фото_история @user` - История фото

История всех фото профиля:
```
.фото_история @username
```

---

### `.поиск_номер +7999...` - Поиск по номеру

Находит пользователя по номеру телефона:
```
.поиск_номер +79991234567
```

**Результат:**
```
📱 Результат поиска

🆔 ID: 123456789
📝 Имя: Иван Петров
📱 Username: @ivan
📞 Номер: +79991234567
⭐ Telegram Premium
```

---

### `.связи @user` - Связанные пользователи

Показывает связанных пользователей:
```
.связи @username
```

**Пример:**
```
🔗 Связанные пользователи
🆔 ID: 123456789

1. Петр Сидоров @petr
   ID: 987654321 | Тип: contact
2. Анна Смирнова @anna
   ID: 111222333 | Тип: group_member

Всего: 15
```

---

## ⚠️ Ограничения

### Rate Limit: **15 запросов в секунду**

Бот автоматически контролирует скорость запросов, но не спамьте командами!

### База данных

FunStat показывает только то, что есть в их базе. Если пользователя нет - данных не будет.

---

## 🔧 API Reference

Swagger документация: https://funstat.info/swagger/index.html

**Доступные эндпоинты:**
- `GET /api/user/{user_id}` - Инфо о пользователе
- `GET /api/user/{user_id}/username-history` - История username
- `GET /api/user/{user_id}/name-history` - История имени
- `GET /api/user/{user_id}/photo-history` - История фото
- `GET /api/user/{user_id}/bio-history` - История bio
- `GET /api/user/{user_id}/phone-history` - История номеров
- `GET /api/user/{user_id}/full-history` - Полная история
- `GET /api/search/username/{username}` - Поиск по username
- `GET /api/search/phone/{phone}` - Поиск по номеру
- `GET /api/user/{user_id}/related` - Связанные
- `GET /api/user/{user_id}/groups` - Группы

---

## 🐛 Troubleshooting

### "❌ FunStat API не настроен"
- Проверьте что токен добавлен в `.env`
- Перезапустите бота

### "❌ Не удалось получить данные"
- Пользователь не найден в базе FunStat
- Проверьте правильность ID/username
- Возможно rate limit превышен

### "Rate limit exceeded"
- Подождите 1-2 секунды между запросами
- Не спамьте командами

---

## ✅ Готово!

Теперь у тебя есть доступ к истории изменений профилей! 🚀

**Используй с умом и не для зла!** 😈
