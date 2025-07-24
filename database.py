import sqlite3
import logging
from config import DB_NAME, SUPPORTED_FIAT, DEFAULT_FIAT

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
            is_recurring INTEGER DEFAULT 0,
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

    # Portfolio table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS portfolio (
            portfolio_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            coin_id TEXT,
            amount REAL,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            UNIQUE(user_id, coin_id)
        )
    ''')

    # Volume alerts table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS volume_alerts (
            alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            coin_id TEXT,
            threshold_multiplier REAL DEFAULT 2.0,
            is_active INTEGER DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')

    # User profiles table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_profiles (
            user_id INTEGER PRIMARY KEY,
            experience_level TEXT DEFAULT 'beginner',
            join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_alerts_created INTEGER DEFAULT 0,
            favorite_coins TEXT DEFAULT '',
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')

    # Feedback table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS feedback (
            feedback_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            message TEXT,
            rating INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')

    # Portfolio transactions table for PnL tracking
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS portfolio_transactions (
            transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            coin_id TEXT,
            transaction_type TEXT, -- 'buy' or 'sell'
            amount REAL,
            price_per_unit REAL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')

    conn.commit()
    conn.close()
    logger.info("Database initialized.")

async def add_user_if_not_exists(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    cursor.execute("INSERT OR IGNORE INTO user_profiles (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

async def get_user_preferred_fiat(user_id: int) -> str:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT preferred_fiat FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result['preferred_fiat'] if result else DEFAULT_FIAT

async def set_user_preferred_fiat(user_id: int, fiat: str) -> bool:
    if fiat.lower() not in SUPPORTED_FIAT:
        return False
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET preferred_fiat = ? WHERE user_id = ?", (fiat.lower(), user_id))
    conn.commit()
    conn.close()
    return True

async def add_price_alert(user_id: int, coin_id: str, target_price: float, condition: str, recurring: bool = False) -> bool:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO price_alerts (user_id, coin_id, target_price, condition, is_recurring)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, coin_id.lower(), target_price, condition, 1 if recurring else 0))
        
        # Update user profile stats
        cursor.execute("UPDATE user_profiles SET total_alerts_created = total_alerts_created + 1 WHERE user_id = ?", (user_id,))
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
    cursor.execute('''
        SELECT pa.alert_id, pa.user_id, pa.coin_id, pa.target_price, pa.condition, pa.is_recurring, u.preferred_fiat 
        FROM price_alerts pa 
        JOIN users u ON pa.user_id = u.user_id 
        WHERE pa.is_active = 1
    ''')
    alerts = cursor.fetchall()
    conn.close()
    return alerts

async def deactivate_alert(alert_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE price_alerts SET is_active = 0 WHERE alert_id = ?", (alert_id,))
    conn.commit()
    conn.close()

async def delete_alert(user_id: int, alert_id: int) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM price_alerts WHERE alert_id = ? AND user_id = ?", (alert_id, user_id))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0

async def add_volume_alert(user_id: int, coin_id: str, threshold_multiplier: float = 2.0) -> bool:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO volume_alerts (user_id, coin_id, threshold_multiplier)
            VALUES (?, ?, ?)
        ''', (user_id, coin_id.lower(), threshold_multiplier))
        conn.commit()
        return True
    except sqlite3.Error as e:
        logger.error(f"Database error adding volume alert: {e}")
        return False
    finally:
        if conn:
            conn.close()

async def get_active_volume_alerts():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT va.alert_id, va.user_id, va.coin_id, va.threshold_multiplier, u.preferred_fiat 
        FROM volume_alerts va 
        JOIN users u ON va.user_id = u.user_id 
        WHERE va.is_active = 1
    ''')
    alerts = cursor.fetchall()
    conn.close()
    return alerts

async def add_to_watchlist(user_id: int, coin_id: str) -> str:
    coin_id_lower = coin_id.lower()
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO watchlist (user_id, coin_id) VALUES (?, ?)", (user_id, coin_id_lower))
        conn.commit()
        return f"{coin_id.upper()} added to your watchlist."
    except sqlite3.IntegrityError:
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

async def add_to_portfolio(user_id: int, coin_id: str, amount: float) -> str:
    coin_id_lower = coin_id.lower()
    if amount <= 0:
        return "Amount must be positive."
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO portfolio (user_id, coin_id, amount) VALUES (?, ?, ?)",
                       (user_id, coin_id_lower, amount))
        conn.commit()
        return f"Added {amount} {coin_id.upper()} to your portfolio."
    except sqlite3.Error as e:
        logger.error(f"Database error adding to portfolio: {e}")
        return "Sorry, an error occurred while adding to your portfolio."
    finally:
        if conn:
            conn.close()

async def remove_from_portfolio(user_id: int, coin_id: str) -> str:
    coin_id_lower = coin_id.lower()
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM portfolio WHERE user_id = ? AND coin_id = ?", (user_id, coin_id_lower))
        conn.commit()
        if cursor.rowcount > 0:
            return f"{coin_id.upper()} removed from your portfolio."
        else:
            return f"{coin_id.upper()} was not found in your portfolio."
    except sqlite3.Error as e:
        logger.error(f"Database error removing from portfolio: {e}")
        return "Sorry, an error occurred while removing from your portfolio."
    finally:
        if conn:
            conn.close()

async def get_portfolio(user_id: int) -> list:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT coin_id, amount FROM portfolio WHERE user_id = ?", (user_id,))
    portfolio = [(row['coin_id'], row['amount']) for row in cursor.fetchall()]
    conn.close()
    return portfolio

async def add_portfolio_transaction(user_id: int, coin_id: str, transaction_type: str, amount: float, price_per_unit: float) -> bool:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO portfolio_transactions (user_id, coin_id, transaction_type, amount, price_per_unit)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, coin_id.lower(), transaction_type, amount, price_per_unit))
        conn.commit()
        return True
    except sqlite3.Error as e:
        logger.error(f"Database error adding portfolio transaction: {e}")
        return False
    finally:
        if conn:
            conn.close()

async def get_portfolio_transactions(user_id: int, coin_id: str = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    if coin_id:
        cursor.execute('''
            SELECT * FROM portfolio_transactions 
            WHERE user_id = ? AND coin_id = ? 
            ORDER BY timestamp DESC
        ''', (user_id, coin_id.lower()))
    else:
        cursor.execute('''
            SELECT * FROM portfolio_transactions 
            WHERE user_id = ? 
            ORDER BY timestamp DESC
        ''', (user_id,))
    transactions = cursor.fetchall()
    conn.close()
    return transactions

async def get_user_profile(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user_profiles WHERE user_id = ?", (user_id,))
    profile = cursor.fetchone()
    conn.close()
    return profile

async def update_user_experience_level(user_id: int, level: str) -> bool:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE user_profiles SET experience_level = ? WHERE user_id = ?", (level, user_id))
        conn.commit()
        return True
    except sqlite3.Error as e:
        logger.error(f"Database error updating experience level: {e}")
        return False
    finally:
        if conn:
            conn.close()

async def add_feedback(user_id: int, message: str, rating: int) -> bool:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO feedback (user_id, message, rating)
            VALUES (?, ?, ?)
        ''', (user_id, message, rating))
        conn.commit()
        return True
    except sqlite3.Error as e:
        logger.error(f"Database error adding feedback: {e}")
        return False
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    init_db()