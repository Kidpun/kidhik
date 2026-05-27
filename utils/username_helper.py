"""
Утилита для получения username пользователя (включая NFT юзернеймы)
"""
import logging
from telethon.tl.types import User

logger = logging.getLogger(__name__)


async def get_user_username(client, user_entity):
    """
    Получает активный username пользователя (включая NFT юзернеймы)
    
    :param client: Telethon клиент
    :param user_entity: Объект пользователя (User)
    :return: Username или None
    """
    try:
        # Сначала пробуем получить основной username
        username = getattr(user_entity, 'username', None)
        
        # Если есть username, возвращаем его
        if username:
            return username
        
        # Если нет основного username, пробуем получить полную информацию о пользователе
        # для доступа к NFT юзернеймам
        try:
            # Используем get_full_user для получения полной информации (включая NFT юзернеймы)
            try:
                full_user_info = await client.get_full_user(user_entity)
                full_user = full_user_info.user
            except:
                # Если get_full_user не работает, пробуем get_entity
                full_user = await client.get_entity(user_entity)
            
            # Проверяем основной username
            if hasattr(full_user, 'username') and full_user.username:
                return full_user.username
            
            # Проверяем список всех юзернеймов (включая NFT)
            if hasattr(full_user, 'usernames') and full_user.usernames:
                # Ищем активный username
                for uname in full_user.usernames:
                    if hasattr(uname, 'username') and uname.username:
                        # Проверяем, является ли он активным
                        if hasattr(uname, 'active') and uname.active:
                            return uname.username
                        # Если нет флага active, берем первый
                        return uname.username
                
                # Если не нашли активный, берем первый доступный
                if full_user.usernames:
                    first_uname = full_user.usernames[0]
                    if hasattr(first_uname, 'username'):
                        return first_uname.username
        
        except Exception as e:
            logger.debug(f"Error getting full user info for username: {e}")
        
        return None
        
    except Exception as e:
        logger.debug(f"Error in get_user_username: {e}")
        return None

