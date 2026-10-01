import sqlite3
import os


DB_NAME = "database/shop.db"


def get_connection():
    os.makedirs("database", exist_ok=True)
    return sqlite3.connect(DB_NAME)


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            photo_id TEXT NOT NULL,
            sale_type TEXT NOT NULL,
            price TEXT,
            comment TEXT,
            status TEXT DEFAULT 'draft',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    try:
        cursor.execute(
            "ALTER TABLE ads ADD COLUMN seller TEXT"
        )
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute(
            "ALTER TABLE ads ADD COLUMN price_edits_left INTEGER DEFAULT 2"
        )
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute(
            "ALTER TABLE ads ADD COLUMN ad_fee INTEGER DEFAULT 0"
        )
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute(
            "ALTER TABLE ads ADD COLUMN channel_message_id INTEGER"
        )
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()


def create_ad(
    user_id,
    photo_id,
    sale_type,
    price,
    comment,
    seller,
    ad_fee
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO ads (
            user_id,
            photo_id,
            sale_type,
            price,
            comment,
            seller,
            ad_fee
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        photo_id,
        sale_type,
        price,
        comment,
        seller,
        ad_fee
    ))

    ad_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return ad_id


def get_user_ads(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, sale_type, price, comment, seller, status, created_at
        FROM ads
        WHERE user_id = ?
          AND status = 'paid'
        ORDER BY id DESC
    """, (user_id,))

    ads = cursor.fetchall()

    conn.close()

    return ads

def change_ad_price(ad_id, user_id, new_price):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT price_edits_left
        FROM ads
        WHERE id = ? AND user_id = ?
    """, (ad_id, user_id))

    result = cursor.fetchone()

    if not result:
        conn.close()
        return False, "not_found"

    edits_left = result[0]

    if edits_left <= 0:
        conn.close()
        return False, "no_edits"

    cursor.execute("""
        UPDATE ads
        SET price = ?,
            price_edits_left = price_edits_left - 1
        WHERE id = ? AND user_id = ?
    """, (new_price, ad_id, user_id))

    conn.commit()
    conn.close()

    return True, edits_left - 1


def save_channel_message_id(ad_id, channel_message_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE ads
        SET channel_message_id = ?
        WHERE id = ?
    """, (channel_message_id, ad_id))

    conn.commit()
    conn.close()
def delete_ad(ad_id, user_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM ads
        WHERE id = ? AND user_id = ?
    """, (ad_id, user_id))

    deleted = cursor.rowcount > 0

    conn.commit()
    conn.close()

    return deleted