import sqlite3
import os
import random
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DB_PATH = BASE_DIR / "data" / "users.db"

def init_db():
    """Инициализация базы данных"""
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    cursor = conn.cursor()

    # Включаем режим WAL и устанавливаем таймауты для предотвращения "database is locked"
    cursor.execute("PRAGMA busy_timeout=30000")
    cursor.execute("PRAGMA journal_mode=WAL")
    
    # Таблица пользователей (добавили колонки для устройства)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        phone TEXT,
        session_name TEXT,
        api_id INTEGER,
        api_hash TEXT,
        device_model TEXT,
        system_version TEXT,
        app_version TEXT,
        is_active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Таблица пула API ключей
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS api_pool (
        api_id INTEGER PRIMARY KEY,
        api_hash TEXT NOT NULL,
        added_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Таблица глобальных настроек (для админа)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    ''')
    
    # По умолчанию бот включен
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('global_enabled', '1')")
    
    # Проверка на наличие новых колонок (миграция)
    cursor.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'device_model' not in columns:
        cursor.execute('ALTER TABLE users ADD COLUMN device_model TEXT')
        cursor.execute('ALTER TABLE users ADD COLUMN system_version TEXT')
        cursor.execute('ALTER TABLE users ADD COLUMN app_version TEXT')
    if 'is_business' not in columns:
        cursor.execute('ALTER TABLE users ADD COLUMN is_business INTEGER DEFAULT 0')
    if 'business_connection_id' not in columns:
        cursor.execute('ALTER TABLE users ADD COLUMN business_connection_id TEXT')
    
    conn.commit()
    conn.close()

def add_api_to_pool(api_id, api_hash, added_by=None):
    """Добавляет API ключи в общий пул"""
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    cursor = conn.cursor()
    cursor.execute("PRAGMA busy_timeout=30000")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute('''
    INSERT OR IGNORE INTO api_pool (api_id, api_hash, added_by)
    VALUES (?, ?, ?)
    ''', (api_id, api_hash, added_by))
    conn.commit()
    conn.close()

def get_random_api(default_id, default_hash):
    """Возвращает случайный API из пула или дефолтный из .env"""
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    cursor = conn.cursor()
    cursor.execute("PRAGMA busy_timeout=30000")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute('SELECT api_id, api_hash FROM api_pool')
    pool = cursor.fetchall()
    conn.close()

    # Добавляем дефолтный в список для выбора
    pool_list = list(pool)
    pool_list.append((default_id, default_hash))

    # Убираем дубликаты и выбираем случайный
    unique_pool = list(set(pool_list))
    return random.choice(unique_pool)

def add_user(user_id, phone, session_name, api_id, api_hash, device_model=None, system_version=None, app_version=None, is_business=False, business_connection_id=None):
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    cursor = conn.cursor()
    cursor.execute("PRAGMA busy_timeout=30000")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute('''
    INSERT OR REPLACE INTO users (user_id, phone, session_name, api_id, api_hash, device_model, system_version, app_version, is_active, is_business, business_connection_id)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
    ''', (user_id, phone, session_name, api_id, api_hash, device_model, system_version, app_version, is_business, business_connection_id))
    conn.commit()
    conn.close()

def get_business_connections():
    """Возвращает список активных бизнес-подключений {user_id: connection_id}"""
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    cursor = conn.cursor()
    cursor.execute("PRAGMA busy_timeout=30000")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute('SELECT user_id, business_connection_id FROM users WHERE is_active = 1 AND is_business = 1 AND business_connection_id IS NOT NULL')
    rows = cursor.fetchall()
    conn.close()
    return {row[0]: row[1] for row in rows}

def get_active_users():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    cursor = conn.cursor()
    cursor.execute("PRAGMA busy_timeout=30000")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute('SELECT user_id, session_name, api_id, api_hash, device_model, system_version, app_version FROM users WHERE is_active = 1')
    users = cursor.fetchall()
    conn.close()
    return users

def remove_user(user_id):
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    cursor = conn.cursor()
    cursor.execute("PRAGMA busy_timeout=30000")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def set_global_enabled(enabled: bool):
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    cursor = conn.cursor()
    cursor.execute("PRAGMA busy_timeout=30000")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('global_enabled', ?)", ('1' if enabled else '0',))
    conn.commit()
    conn.close()

def is_global_enabled() -> bool:
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    cursor = conn.cursor()
    cursor.execute("PRAGMA busy_timeout=30000")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("SELECT value FROM settings WHERE key = 'global_enabled'")
    res = cursor.fetchone()
    conn.close()
    return res[0] == '1' if res else True

def get_all_user_ids():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    cursor = conn.cursor()
    cursor.execute("PRAGMA busy_timeout=30000")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute('SELECT user_id FROM users')
    ids = [row[0] for row in cursor.fetchall()]
    conn.close()
    return ids
