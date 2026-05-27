"""
Команда .игнор
Добавляет/убирает чат из списка игнорируемых
"""
import logging
from telethon import events
from telethon.errors import ChannelPrivateError, UsernameNotOccupiedError

from utils.ignore_list import ignore_manager

logger = logging.getLogger(__name__)


async def ignore_command(event: events.NewMessage.Event):
    """
    Обработчик команды .игнор <chat_id или username>
    """
    user_id = event.sender_id
    text = event.message.text.strip()
    
    # Извлекаем аргумент
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        await event.respond(
            "❌ Использование: <code>.игнор &lt;ID_чата или @username&gt;</code>\n\n"
            "Примеры:\n"
            "• <code>.игнор -1001234567890</code> (ID группы/канала)\n"
            "• <code>.игнор 123456789</code> (ID пользователя для ЛС)\n"
            "• <code>.игнор @username</code> (username канала/группы/пользователя)\n\n"
            "Повторная команда с тем же ID уберёт чат из игнора.",
            parse_mode='html'
        )
        return
    
    chat_input = parts[1].strip()
    
    try:
        # Пробуем распарсить как число (ID)
        try:
            chat_id = int(chat_input)
        except ValueError:
            # Если не число, пробуем как username
            if chat_input.startswith('@'):
                chat_input = chat_input[1:]
            
            # Пробуем получить чат по username
            try:
                entity = await event.client.get_entity(chat_input)
                chat_id = entity.id
                chat_title = getattr(entity, 'title', getattr(entity, 'first_name', 'Unknown'))
            except (ValueError, UsernameNotOccupiedError):
                await event.respond(
                    f"❌ Не удалось найти чат/пользователя: <code>{chat_input}</code>\n\n"
                    "Убедитесь, что:\n"
                    "• ID указан правильно\n"
                    "• Username существует и вы имеете к нему доступ",
                    parse_mode='html'
                )
                return
        
        # Для чатов/каналов используем always_telegram_id
        def norm_chat_id(cid, entity=None):
            # Telethon: Channel (id > 0) → -100{id} (as in official clients)
            if entity and hasattr(entity, 'id'):
                if hasattr(entity, 'megagroup') or hasattr(entity, 'broadcast'):
                    return int(f'-100{int(entity.id)}')
            if abs(cid) > 1e11 or str(cid).startswith('-100'):
                return int(cid)
            # Если случайно обычный int > 2e9 — передадим без изменений
            return int(cid)
        #
        normed_chat_id = chat_id
        try:
            # Попробуем получить нормализованный id (для Channel)
            chat_entity = await event.client.get_entity(chat_id)
            normed_chat_id = norm_chat_id(chat_id, chat_entity)
        except Exception:
            normed_chat_id = norm_chat_id(chat_id)
        #
        is_now_ignored = ignore_manager.toggle_ignore(user_id, normed_chat_id)
        
        # Получаем название чата для красивого ответа
        try:
            chat = await event.client.get_entity(chat_id)
            chat_title = getattr(chat, 'title', getattr(chat, 'first_name', f'Chat {chat_id}'))
        except:
            chat_title = f'Chat {chat_id}'
        
        if is_now_ignored:
            await event.respond(
                f"✅ Чат <b>{chat_title}</b> добавлен в игнор.\n\n"
                "Теперь удаленные/измененные сообщения и медиа из этого чата "
                "не будут сохраняться и отправляться в личку.\n\n"
                "Чтобы убрать из игнора, повторите команду: "
                f"<code>.игнор {chat_id}</code>",
                parse_mode='html'
            )
            logger.info(f"User {user_id} ignored chat {chat_id} ({chat_title})")
        else:
            await event.respond(
                f"✅ Чат <b>{chat_title}</b> убран из игнора.\n\n"
                "Теперь удаленные/измененные сообщения и медиа из этого чата "
                "будут снова сохраняться.",
                parse_mode='html'
            )
            logger.info(f"User {user_id} unignored chat {chat_id} ({chat_title})")
            
    except Exception as e:
        logger.error(f"Error in ignore command for user {user_id}: {e}")
        await event.respond(
            f"❌ Ошибка: {e}\n\n"
            "Попробуйте указать числовой ID чата.",
            parse_mode='html'
        )



















