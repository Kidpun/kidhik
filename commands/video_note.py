"""
Команда .круг
Конвертация видео в Video Note (кружок)
"""
import logging
import os
import subprocess
import asyncio
import shutil
from telethon import events

logger = logging.getLogger(__name__)

def check_ffmpeg():
    """Проверяет наличие ffmpeg в системе"""
    return shutil.which('ffmpeg') is not None

async def video_note_command(event: events.NewMessage.Event):
    """
    .круг - Сделать кружок из реплая (видео/гиф)
    """
    # Проверяем наличие ffmpeg
    if not check_ffmpeg():
        await event.edit(
            "❌ <b>FFmpeg не установлен</b>\n\n"
            "💡 <b>Установка:</b>\n"
            "• <b>Ubuntu/Debian:</b> <code>sudo apt install ffmpeg</code>\n"
            "• <b>CentOS/RHEL:</b> <code>sudo yum install ffmpeg</code>\n"
            "• <b>macOS:</b> <code>brew install ffmpeg</code>\n"
            "• <b>Windows:</b> Скачайте с <a href='https://ffmpeg.org/download.html'>ffmpeg.org</a>",
            parse_mode='html'
        )
        return
    
    reply = await event.get_reply_message()
    if not reply or not reply.media:
        await event.edit("❌ Ответьте на видео!")
        return
        
    await event.edit("🔄 Обработка...")
    
    path = await reply.download_media(file="temp_media/")
    out_path = f"temp_media/circle_{event.id}.mp4"
    
    try:
        # Конвертация через ffmpeg
        # 1. Обрезка до квадрата (crop)
        # 2. Ресайз до 384x384 (стандарт кружка)
        # 3. Лимит 60 сек
        
        cmd = [
            "ffmpeg", "-i", path,
            "-t", "59",
            "-vf", "crop=min(iw\\,ih):min(iw\\,ih),scale=384:384",
            "-b:v", "1000k",
            "-c:v", "libx264",
            "-c:a", "aac",
            "-y", out_path
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_msg = stderr.decode('utf-8', errors='ignore') if stderr else "Неизвестная ошибка"
            logger.error(f"FFmpeg error: {error_msg}")
            await event.edit(f"❌ Ошибка конвертации:\n<code>{error_msg[:200]}</code>", parse_mode='html')
            return
        
        if os.path.exists(out_path):
            await event.edit("⬆️ Отправляю...")
            await event.client.send_file(
                event.chat_id, 
                out_path, 
                video_note=True, # Важно!
                reply_to=event.reply_to_msg_id
            )
            await event.delete()
        else:
            await event.edit("❌ Ошибка конвертации (файл не создан).")
            
    except FileNotFoundError:
        await event.edit(
            "❌ <b>FFmpeg не найден</b>\n\n"
            "Установите FFmpeg и убедитесь, что он доступен в PATH.",
            parse_mode='html'
        )
    except Exception as e:
        logger.error(f"Circle error: {e}", exc_info=True)
        error_msg = f"❌ Ошибка: {e}"
        if 'ffmpeg' in str(e).lower():
            error_msg = "❌ <b>Ошибка FFmpeg</b>\n\nУбедитесь, что FFmpeg установлен и доступен."
        await event.edit(error_msg, parse_mode='html')
    finally:
        # Очистка временных файлов
        if path and os.path.exists(path): 
            try:
                os.remove(path)
                logger.debug(f"Removed temp input file: {path}")
            except Exception as e:
                logger.warning(f"Failed to remove temp input file {path}: {e}")
        if os.path.exists(out_path): 
            try:
                os.remove(out_path)
                logger.debug(f"Removed temp output file: {out_path}")
            except Exception as e:
                logger.warning(f"Failed to remove temp output file {out_path}: {e}")


