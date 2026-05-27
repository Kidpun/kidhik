"""
KidHik Userbot — конфигурация
Все значения берутся из .env
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Пути ──────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent
TEXT_DIR = BASE_DIR / "text"
TROLL_FILE = TEXT_DIR / "troll.txt"

# ── Telegram API ───────────────────────────────────────────────────────────────
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
SESSION_FILE = os.getenv("SESSION_FILE", "sessions_local/kidhik.session")

# ── Данные устройства (рандомизируются при входе) ─────────────────────────────
DEFAULT_DEVICE_MODEL = "PC 64bit"
DEFAULT_SYSTEM_VERSION = "Windows 10"
DEFAULT_APP_VERSION = "4.16.2 x64"
LANG_CODE = os.getenv("LANG_CODE", "ru")
SYSTEM_LANG_CODE = os.getenv("SYSTEM_LANG_CODE", "en-US")

# ── Владелец (ваш Telegram ID — обязательно задать в .env) ───────────────────
# Получить свой ID: напишите @userinfobot в Telegram
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

# ── Прокси ───────────────────────────────────────────────────────────────────
# Форматы: socks5://user:pass@host:port  |  http://host:port
PROXY_URL = os.getenv("PROXY_URL", "")

# ── Spotify ───────────────────────────────────────────────────────────────────
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", "")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "")
SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI", "http://localhost:8888/callback")

# ── AI / Search ───────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
GOOGLE_SEARCH_CX = os.getenv("GOOGLE_SEARCH_CX", "")

# ── Внешние API ───────────────────────────────────────────────────────────────
WHOIS_API_KEY = os.getenv("WHOIS_API_KEY", "")
FUNSTAT_TOKEN = os.getenv("FUNSTAT_TOKEN", "")
YANDEX_TOKEN = os.getenv("YANDEX_TOKEN", "")

# ── Фразы для команды .откат ──────────────────────────────────────────────────
_otkat_base = [
    "откат", "оТкАт", "ОТКАТ", "0тkат", "0tkat", "0ТКАТ",
    "отк@т", "0тк@т", "оТк@Т", "ОТК@Т",
    "откат изи", "отк@т изи", "0тkат изи", "оТкАт изи",
    "ez откат", "ez отк@т", "ez 0тkат", "ez оТкАт",
    "давай бомж откат", "давай бомж отк@т", "давай бомж 0тkат",
]
_additional_words = [
    "шлюха", "бомж", "нищий", "хуила", "терпила",
    "шлюх@", "б0мж", "нищ@й", "хуил@", "терпил@",
    "шлюха откат", "бомж откат", "нищий откат", "хуила откат", "терпила откат",
    "откат шлюха", "откат бомж", "откат нищий", "откат хуила", "откат терпила",
    "шлюх@ отк@т", "б0мж 0тkат", "нищ@й оТкАт", "хуил@ отк@т", "терпил@ 0тkат",
]
OTKAT_PHRASES = _otkat_base + _additional_words

# Вероятность ответить реплаем в .откат (20 %)
OTKAT_REPLY_CHANCE = 0.2
