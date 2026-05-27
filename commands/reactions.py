"""
Команда .реакции
Ставит реакции на каждое новое сообщение (рандомно)
"""
import logging
import random
import re
import unicodedata
from telethon import events
from telethon.errors import ReactionInvalidError, ChatAdminRequiredError, FloodWaitError

logger = logging.getLogger(__name__)

# Вайтлист обычных эмодзи для реакций (без премиум)
# Основные реакции + дополнительные популярные
ALLOWED_REACTION_EMOJIS = {
    # Основные (запрос пользователя)
    '❤️', '👍', '🤯', '😡', '🔥', '👎', '🎉', '😘', '💊', '🤡', '💋', '💔',

    # Дополнительные популярные
    '💪', '⭐', '✨', '💝', '🎁', '👀', '😍', '😎', '🤩', '😇', '🙏',
    '🤝', '👌', '✌️', '🤞', '🤟', '🤘', '👋', '🤚', '🖐️', '✋', '🖖',
    '🙌', '🤲', '💅', '🤳', '🦾', '🦵', '🦶', '👂', '🦻', '👃', '🧠',
    '👅', '👄', '💘', '💖', '💗', '💓', '💞', '💕', '💟', '❣️',
    '🧡', '💛', '💚', '💙', '💜', '🖤', '🤍', '🤎', '💢', '💥',
    '💫', '💦', '💨', '💣', '💬', '💭', '💤', '😀', '😃', '😄', '😆',
    '😅', '🤣', '😂', '🙂', '🙃', '😉', '😊', '😗', '☺️', '😚',
    '😙', '🥲', '😋', '😛', '😜', '🤪', '😝', '🤑', '🤗', '🤭', '🤫',
    '🤐', '🤨', '😐', '😑', '😶', '😏', '😒', '🙄', '😬', '🤥', '😔',
    '😪', '🤤', '😴', '😷', '🤒', '🤕', '🤢', '🤮', '🤧', '🥵', '🥶',
    '😵', '🤠', '🥳', '🥸', '🧐', '😕', '😟', '🙁', '☹️', '😯', '😲',
    '😳', '🥺', '😦', '😧', '😨', '😰', '😥', '😢', '😭', '😱', '😖',
    '😣', '😞', '😓', '😩', '😫', '🥱', '😤', '😠', '🤬', '😈',
    '👿', '💀', '☠️', '💩', '👹', '👺', '👻', '👽', '👾', '🤖',
    '😺', '😸', '😹', '😻', '😼', '😽', '🙀', '😿', '😾'
}

# Хранилище реакций для каждого пользователя и чата
# Структура: {(user_id, chat_id): [emoji1, emoji2, emoji3]}
user_reactions = {}

# Кеш для сообщений об ошибках (чтобы не спамить)
# Структура: {(user_id, chat_id): timestamp}
error_message_cache = {}
ERROR_MESSAGE_COOLDOWN = 300  # 5 минут между сообщениями об ошибках


def is_valid_emoji(emoji: str) -> bool:
    """
    Проверяет, является ли эмодзи обычным (не премиум) и разрешенным
    """
    result = emoji in ALLOWED_REACTION_EMOJIS
    if not result:
        logger.debug(f"Emoji '{emoji}' not in allowed list (ord: {[ord(c) for c in emoji]})")
        logger.debug(f"Allowed emojis containing heart: {[e for e in ALLOWED_REACTION_EMOJIS if '❤' in e]}")
    return result


async def reactions_command(event: events.NewMessage.Event):
    """
    Обработчик команды .реакции [эмодзи1] [эмодзи2] [эмодзи3]
    Устанавливает реакции для постановки на новые сообщения в текущем чате (100% шанс на одну реакцию)
    """
    try:
        user_id = event.sender_id
        chat_id = event.chat_id
        text = event.message.text.strip()
        
        # Ключ для хранения реакций: (user_id, chat_id)
        reaction_key = (user_id, chat_id)
        
        # Парсим команду
        parts = text.split()
        if len(parts) == 1:
            # Если только команда без параметров - показываем текущие реакции или инструкцию
            if reaction_key in user_reactions and user_reactions[reaction_key]:
                reactions_list = ' '.join(user_reactions[reaction_key])
                await event.respond(
                    f"✅ <b>Текущие реакции для этого чата:</b> {reactions_list}\n\n"
                    f"Чтобы изменить, используйте:\n"
                    f"<code>.реакции [эмодзи1] [эмодзи2] [эмодзи3]</code>\n\n"
                    f"Чтобы отключить, используйте:\n"
                    f"<code>.реакции off</code>",
                    parse_mode='html'
                )
            else:
                await event.respond(
                    "📝 <b>Использование:</b>\n\n"
                    "<code>.реакции [эмодзи1] [эмодзи2] [эмодзи3]</code>\n\n"
                    "Примеры:\n"
                    "• <code>.реакции 👍</code>\n"
                    "• <code>.реакции ❤️ 🔥</code>\n"
                    "• <code>.реакции 🤯 😡 💊</code>\n\n"
                    "💡 Можно указать до 3 эмодзи - бот будет случайно выбирать одну из них.\n"
                    "ℹ️ Реакции будут ставиться только в этом чате.\n"
                    "⚠️ Поддерживаются только обычные эмодзи (без премиум).",
                    parse_mode='html'
                )
            return
        
        # Проверяем отключение
        if parts[1].lower() == 'off':
            if reaction_key in user_reactions:
                del user_reactions[reaction_key]
                logger.info(f"Disabled reactions for user {user_id} in chat {chat_id}. Total active reactions: {len(user_reactions)}")
            else:
                logger.info(f"No reactions to disable for user {user_id} in chat {chat_id}")
            await event.respond("✅ Реакции отключены для этого чата")
            return
        
        # Извлекаем эмодзи из команды (максимум 3)
        reactions = []
        invalid_emojis = []

        # Собираем все эмодзи из аргументов команды
        all_emojis_text = ' '.join(parts[1:4])  # Объединяем все аргументы обратно
        logger.debug(f"Processing emoji text: '{all_emojis_text}' (length: {len(all_emojis_text)})")
        for i, char in enumerate(all_emojis_text):
            logger.debug(f"Char {i}: '{char}' (ord: {ord(char)}, category: {unicodedata.category(char)})")

        # Проходим по тексту и собираем эмодзи
        i = 0
        while i < len(all_emojis_text) and len(reactions) < 3:
            # Пропускаем пробелы
            if all_emojis_text[i].isspace():
                i += 1
                continue

            # Проверяем одиночный символ
            if all_emojis_text[i] in ALLOWED_REACTION_EMOJIS:
                reactions.append(all_emojis_text[i])
                i += 1
                continue

            # Проверяем составные эмодзи (2-3 символа)
            found_emoji = None
            for length in range(2, 4):
                if i + length <= len(all_emojis_text):
                    candidate = all_emojis_text[i:i+length]
                    if candidate in ALLOWED_REACTION_EMOJIS:
                        found_emoji = candidate
                        break

            if found_emoji:
                reactions.append(found_emoji)
                i += len(found_emoji)
            else:
                # Не нашли валидный эмодзи
                char = all_emojis_text[i]
                if char not in [' ', '\n', '\t']:
                    invalid_emojis.append(char)
                    logger.debug(f"No valid emoji found at position {i}: '{char}' (ord: {ord(char)})")
                i += 1
        
        if invalid_emojis:
            invalid_list = ' '.join(invalid_emojis)
            await event.respond(
                f"❌ <b>Недопустимые эмодзи:</b> {invalid_list}\n\n"
                f"Используйте только обычные эмодзи (без премиум).\n\n"
                f"Примеры разрешенных: ❤️ 👍 🤯 😡 🔥 👎 🎉 😘 💊 🤡 💋 💔",
                parse_mode='html'
            )
            return
        
        if not reactions:
            await event.respond(
                "❌ Не указаны эмодзи для реакций.\n\n"
                "Использование: <code>.реакции [эмодзи1] [эмодзи2] [эмодзи3]</code>\n\n"
                "Примеры: <code>.реакции ❤️ 👍 🤯</code>",
                parse_mode='html'
            )
            return
        
        if len(reactions) > 3:
            await event.respond("❌ Можно указать максимум 3 эмодзи")
            return
        
        # Сохраняем реакции для пользователя и чата
        user_reactions[reaction_key] = reactions
        logger.info(f"Set reactions for user {user_id} in chat {chat_id}: {reactions}. Total active reactions: {len(user_reactions)}")
        
        reactions_text = ' '.join(reactions)
        await event.respond(
            f"✅ <b>Реакции установлены для этого чата:</b> {reactions_text}\n\n"
            f"Теперь бот будет случайно ставить одну из этих реакций на новые сообщения только в этом чате.",
            parse_mode='html'
        )
        
        logger.info(f"Reactions set for user {user_id} in chat {chat_id}: {reactions_text}")
        
    except Exception as e:
        logger.error(f"Ошибка в команде .реакции: {e}", exc_info=True)
        await event.respond("❌ Ошибка при установке реакций")


async def auto_react_to_message(event: events.NewMessage.Event, client, user_id: int):
    """
    Автоматически ставит реакции на новое сообщение
    Только в чатах, где была вызвана команда .реакции
    """
    import time
    
    try:
        chat_id = event.chat_id
        reaction_key = (user_id, chat_id)
        
        # Проверяем, есть ли реакции для этого пользователя и чата
        if reaction_key not in user_reactions or not user_reactions[reaction_key]:
            logger.debug(f"No reactions configured for user {user_id} in chat {chat_id}")
            return
        
        # Пропускаем свои сообщения - проверяем через sender_id события
        # sender_id - это ID отправителя сообщения
        # user_id - это ID владельца бота (наш ID)
        if event.sender_id == user_id:
            logger.debug(f"Skipping own message: sender_id={event.sender_id}, user_id={user_id}")
            return
        
        # Дополнительная проверка через get_me() для надежности
        try:
            me = await client.get_me()
            if event.sender_id == me.id:
                logger.debug(f"Skipping own message (via get_me): sender_id={event.sender_id}, me.id={me.id}")
                return
        except Exception as e:
            logger.debug(f"Could not get_me for reaction check: {e}")
        
        # Пропускаем команды
        if event.message.text and event.message.text.strip().startswith('.'):
            return
        
        reactions = user_reactions[reaction_key]
        message_id = event.message.id

        # Всегда ставим реакцию (100% шанс)
        logger.debug(f"🎯 Setting reaction in chat {chat_id} for message {message_id}")

        # Выбираем одну случайную реакцию из списка
        selected_emoji = random.choice(reactions)

        logger.info(f"🎯 Attempting to set random reaction '{selected_emoji}' from {reactions} in chat {chat_id} for message {message_id} (sender: {event.sender_id}, me: {user_id})")

        # Пробуем поставить одну реакцию
        unavailable_reactions = []
        successful_reactions = 0

        # Ставим только выбранную реакцию
        try:
            # В Telethon реакции ставятся через SendReactionRequest
            # Используем только обычные эмодзи (ReactionEmoji)
            from telethon.tl.functions.messages import SendReactionRequest
            from telethon.tl.types import ReactionEmoji

            # Создаем объект реакции (только обычные эмодзи)
            reaction_obj = ReactionEmoji(emoticon=selected_emoji)

            # Отправляем реакцию через API
            await client(SendReactionRequest(
                peer=chat_id,
                msg_id=message_id,
                reaction=[reaction_obj],
                big=False
            ))

            successful_reactions += 1
            logger.info(f"✅ Successfully set reaction {selected_emoji} in chat {chat_id} for message {message_id}")
        except ReactionInvalidError as e:
            # Эмодзи недоступно (возможно, премиум или ограничено)
            unavailable_reactions.append(selected_emoji)
            logger.warning(f"❌ ReactionInvalidError for {selected_emoji} in chat {chat_id}: {e}")
        except ChatAdminRequiredError as e:
            # Нет прав на реакции в этом чате
            logger.warning(f"❌ No permission to react in chat {chat_id}: {e}")
            return
        except FloodWaitError as e:
            # Слишком много запросов
            logger.warning(f"⏳ FloodWait for reactions in chat {chat_id}: {e.seconds} seconds")
            return
        except Exception as e:
            logger.error(f"❌ Error setting reaction {selected_emoji} in chat {chat_id}: {e}", exc_info=True)
            unavailable_reactions.append(selected_emoji)
        
        # Логируем результат
        if successful_reactions > 0:
            logger.info(f"Set {successful_reactions}/1 reactions in chat {chat_id}")
        else:
            logger.warning(f"Failed to set reaction '{selected_emoji}' in chat {chat_id}")

        # Если реакция недоступна, проверяем причину (но не спамим)
        if unavailable_reactions:
            # Проверяем кеш для этого чата
            cache_key = (user_id, chat_id)
            current_time = time.time()
            
            # Проверяем, не отправляли ли мы недавно сообщение об ошибке для этого чата
            if cache_key in error_message_cache:
                last_sent = error_message_cache[cache_key]
                if current_time - last_sent < ERROR_MESSAGE_COOLDOWN:
                    logger.debug(f"Skipping error message for chat {chat_id} (cooldown)")
                    return
            
            # Обновляем кеш
            error_message_cache[cache_key] = current_time
            
            # Проверяем, есть ли у пользователя премиум
            try:
                me = await client.get_me()
                has_premium = getattr(me, 'premium', False)
                
                # Получаем информацию о чате для отправки сообщения
                try:
                    chat = await event.get_chat()
                    chat_title = getattr(chat, 'title', None) or getattr(chat, 'first_name', None) or 'Чат'
                except Exception:
                    chat_title = "Чат"
                
                # Реакции недоступны - значит они ограничены в чате
                restricted_emojis = ' '.join(unavailable_reactions)
                logger.warning(f"Reactions restricted in chat {chat_id}: {restricted_emojis}")
                from utils.bot_sender import send_to_user
                await send_to_user(
                    user_id,
                    f"⚠️ <b>Ограничения в чате</b>\n\n"
                    f"💬 <b>Чат:</b> {chat_title}\n\n"
                    f"В этом чате выключены/ограничены такие реакции:\n"
                    f"{restricted_emojis}\n\n"
                    f"<i>Это сообщение будет показано снова через 5 минут, если проблема повторится.</i>",
                )
            except Exception as e:
                logger.error(f"Error checking premium status: {e}", exc_info=True)
        
    except Exception as e:
        logger.error(f"Error in auto_react_to_message: {e}", exc_info=True)

