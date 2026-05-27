import logging
import os
import asyncio
from telethon import events
from shazamio import Shazam
from pathlib import Path
import subprocess

logger = logging.getLogger(__name__)

TEMP_DIR = Path(__file__).parent.parent / "temp_media"
TEMP_DIR.mkdir(exist_ok=True)

async def shazam_command(event: events.NewMessage.Event):
    """
    .шазам - Распознает трек из голосового, видео или аудио (реплай).
    """
    if not event.is_reply:
        await event.edit("❌ Используйте команду в ответ на аудио, видео или голосовое сообщение.")
        return

    reply_msg = await event.get_reply_message()
    if not reply_msg or not reply_msg.media:
        await event.edit("❌ Сообщение не содержит медиа.")
        return

    status_msg = await event.edit("🎧 Слушаю...", parse_mode='html')
    
    # Путь для временного файла
    file_path = TEMP_DIR / f"shazam_{reply_msg.id}"
    converted_file = None
    
    try:
        # Скачиваем файл
        downloaded_file = await reply_msg.download_media(file=file_path)
        if not downloaded_file or not os.path.exists(downloaded_file):
            await status_msg.edit("❌ Не удалось скачать медиа.")
            return

        # Проверяем размер файла
        file_size = os.path.getsize(downloaded_file)
        if file_size < 1024:  # Меньше 1KB - слишком маленький
            await status_msg.edit("❌ Файл слишком маленький для распознавания.")
            if os.path.exists(downloaded_file):
                os.remove(downloaded_file)
            return

        await status_msg.edit("🎧 Конвертирую...", parse_mode='html')

        # Конвертируем в WAV для лучшей совместимости с Shazam
        # Shazam лучше работает с WAV/MP3
        converted_file = str(file_path) + "_converted.wav"
        try:
            # Пытаемся использовать ffmpeg для конвертации (асинхронно!)
            process = await asyncio.create_subprocess_exec(
                'ffmpeg', '-i', downloaded_file, '-ar', '44100', '-ac', '2', '-f', 'wav', '-y', converted_file,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=30)
            except asyncio.TimeoutError:
                process.kill()
                logger.warning("FFmpeg conversion timeout, using original file")
                converted_file = downloaded_file
            else:
                if process.returncode != 0 or not os.path.exists(converted_file):
                    # Если конвертация не удалась, используем оригинальный файл
                    error_msg = stderr.decode('utf-8', errors='ignore') if stderr else "Unknown error"
                    logger.warning(f"FFmpeg conversion failed, using original file: {error_msg}")
                    converted_file = downloaded_file
                else:
                    # Удаляем оригинальный файл после успешной конвертации
                    try:
                        os.remove(downloaded_file)
                    except:
                        pass
        except (FileNotFoundError, Exception) as e:
            # Если ffmpeg не установлен или ошибка - используем оригинальный файл
            logger.debug(f"FFmpeg not available or error: {e}, using original file")
            converted_file = downloaded_file

        await status_msg.edit("🎧 Распознаю...", parse_mode='html')

        # Распознаем через Shazam с таймаутом
        shazam = Shazam()
        try:
            out = await asyncio.wait_for(shazam.recognize(converted_file), timeout=30)
        except asyncio.TimeoutError:
            await status_msg.edit("❌ Таймаут распознавания. Попробуйте более короткий фрагмент.")
            return
        except Exception as e:
            logger.error(f"Shazam recognition error: {e}")
            # Пробуем еще раз с оригинальным файлом, если использовали конвертированный
            if converted_file != downloaded_file and os.path.exists(downloaded_file):
                try:
                    out = await asyncio.wait_for(shazam.recognize(downloaded_file), timeout=30)
                except Exception as e2:
                    await status_msg.edit(f"❌ Ошибка распознавания: {e2}")
                    return
            else:
                await status_msg.edit(f"❌ Ошибка распознавания: {e}")
                return
        
        # Удаляем файлы после распознавания
        for f in [downloaded_file, converted_file]:
            if f and os.path.exists(f):
                try:
                    os.remove(f)
                except:
                    pass

        if not out or 'track' not in out:
            await status_msg.edit("🔇 Не удалось распознать трек.")
            return

        track = out['track']
        title = track.get('title', 'Unknown Title')
        subtitle = track.get('subtitle', 'Unknown Artist')
        share_url = track.get('share', {}).get('href', '')
        image_url = track.get('images', {}).get('coverart', '')
        
        # Ссылки на стриминги (если есть)
        # Shazam иногда отдает их в sections -> metadata
        
        response_text = (
            f"🎵 <b>Найдено:</b>\n\n"
            f"🎤 <b>Исполнитель:</b> {subtitle}\n"
            f"🎼 <b>Трек:</b> {title}\n"
        )
        
        if share_url:
            response_text += f"\n🔗 <a href='{share_url}'>Открыть в Shazam</a>"

        # Отправляем результат
        # Если есть обложка, отправляем с фото, иначе просто текст
        if image_url:
            try:
                await event.client.send_file(
                    event.chat_id,
                    image_url,
                    caption=response_text,
                    reply_to=reply_msg.id,
                    parse_mode='html'
                )
                await status_msg.delete()
            except Exception as e:
                # Если не удалось отправить фото, просто редактируем статус
                await status_msg.edit(response_text, parse_mode='html', link_preview=True)
        else:
            await status_msg.edit(response_text, parse_mode='html', link_preview=True)

    except Exception as e:
        logger.error(f"Ошибка в команде .шазам: {e}", exc_info=True)
        error_msg = f"❌ Ошибка: {e}"
        
        # Более понятные сообщения об ошибках
        error_str = str(e).lower()
        if 'end of stream' in error_str or 'eof' in error_str:
            error_msg = "❌ <b>Ошибка: конец потока</b>\n\n"
            error_msg += "Файл поврежден или не полностью скачан.\n"
            error_msg += "💡 <b>Попробуйте:</b>\n"
            error_msg += "• Отправить файл заново\n"
            error_msg += "• Использовать более короткий фрагмент (10-30 секунд)\n"
            error_msg += "• Проверить качество аудио"
        elif 'timeout' in error_str:
            error_msg = "❌ Таймаут распознавания. Попробуйте более короткий фрагмент."
        elif 'format' in error_str or 'codec' in error_str:
            error_msg = "❌ Неподдерживаемый формат файла. Попробуйте MP3 или WAV."
        
        await status_msg.edit(error_msg, parse_mode='html')
    finally:
        # Очистка временных файлов - ВСЕГДА выполняется
        try:
            # Удаляем конкретные файлы
            for f in [downloaded_file, converted_file]:
                if f and os.path.exists(f):
                    try:
                        os.remove(f)
                        logger.debug(f"Cleaned up Shazam temp file: {f}")
                    except Exception as e:
                        logger.warning(f"Failed to remove {f}: {e}")
            
            # Уборка мусора - ищем все файлы, начинающиеся с shazam_reply_msg.id
            # (download_media может добавлять расширение)
            if TEMP_DIR.exists():
                for f in os.listdir(TEMP_DIR):
                    if f.startswith(f"shazam_{reply_msg.id}"):
                        try:
                            file_path = TEMP_DIR / f
                            os.remove(file_path)
                            logger.debug(f"Cleaned up remaining Shazam file: {file_path}")
                        except Exception as e:
                            logger.debug(f"Failed to remove {file_path}: {e}")
        except Exception as cleanup_err:
            logger.error(f"Error in Shazam cleanup: {cleanup_err}")


