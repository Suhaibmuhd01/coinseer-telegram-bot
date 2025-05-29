import sqlite3
import logging
from config import DB_NAME

logger = logging.getLogger(__name__)

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # User preferences table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            preferred_fiat TEXT DEFAULT 'usd',
            notifications_enabled INTEGER DEFAULT 1
        )
    ''')

    # Price alerts table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS price_alerts (
            alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            coin_id TEXT,
            target_price REAL,
            condition TEXT, -- 'above' or 'below'
            is_active INTEGER DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')

    # Watchlist table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS watchlist (
            watchlist_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            coin_id TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            UNIQUE(user_id, coin_id)
        )
    ''')

    conn.commit()
    conn.close()
    logger.info("Database initialized.")

# --- User Functions ---
async def add_user_if_not_exists(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

# --- Alert Functions ---
async def add_price_alert(user_id: int, coin_id: str, target_price: float, condition: str) -> bool:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO price_alerts (user_id, coin_id, target_price, condition)
            VALUES (?, ?, ?, ?)
        ''', (user_id, coin_id.lower(), target_price, condition))
        conn.commit()
        return True
    except sqlite3.Error as e:
        logger.error(f"Database error adding alert: {e}")
        return False
    finally:
        if conn:
            conn.close()

async def get_active_alerts():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT pa.alert_id, pa.user_id, pa.coin_id, pa.target_price, pa.condition, u.preferred_fiat FROM price_alerts pa JOIN users u ON pa.user_id = u.user_id WHERE pa.is_active = 1")
    alerts = cursor.fetchall()
    conn.close()
    return alerts

async def deactivate_alert(alert_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE price_alerts SET is_active = 0 WHERE alert_id = ?", (alert_id,))
    conn.commit()
    conn.close()

# --- Watchlist Functions ---
async def add_to_watchlist(user_id: int, coin_id: str) -> str:
    coin_id_lower = coin_id.lower()
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO watchlist (user_id, coin_id) VALUES (?, ?)", (user_id, coin_id_lower))
        conn.commit()
        return f"{coin_id.upper()} added to your watchlist."
    except sqlite3.IntegrityError: # Handles UNIQUE constraint violation
        return f"{coin_id.upper()} is already in your watchlist."
    except sqlite3.Error as e:
        logger.error(f"Database error adding to watchlist: {e}")
        return "Sorry, an error occurred while adding to your watchlist."
    finally:
        if conn:
            conn.close()

async def remove_from_watchlist(user_id: int, coin_id: str) -> str:
    coin_id_lower = coin_id.lower()
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM watchlist WHERE user_id = ? AND coin_id = ?", (user_id, coin_id_lower))
        conn.commit()
        if cursor.rowcount > 0:
            return f"{coin_id.upper()} removed from your watchlist."
        else:
            return f"{coin_id.upper()} was not found in your watchlist."
    except sqlite3.Error as e:
        logger.error(f"Database error removing from watchlist: {e}")
        return "Sorry, an error occurred while removing from your watchlist."
    finally:
        if conn:
            conn.close()

async def get_watchlist(user_id: int) -> list:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT coin_id FROM watchlist WHERE user_id = ?", (user_id,))
    watchlist = [row['coin_id'] for row in cursor.fetchall()]
    conn.close()
    return watchlist

if __name__ == '__main__':
    # To initialize DB manually if needed
    logging.basicConfig(level=logging.INFO)
    init_db()