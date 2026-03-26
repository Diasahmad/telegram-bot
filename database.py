import os
import psycopg

# ======================
# ENV
# ======================
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL tidak ditemukan")

# ======================
# CONNECTION
# ======================
def get_connection():
    return psycopg.connect(DATABASE_URL)

# ======================
# INIT DB
# ======================
def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id SERIAL PRIMARY KEY,
            amount INTEGER,
            type TEXT,
            category TEXT,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    cur.close()
    conn.close()

# ======================
# SAVE DATA
# ======================
def save_transaction(amount, tipe, category, description):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO transactions (amount, type, category, description)
        VALUES (%s, %s, %s, %s)
        RETURNING created_at
    """, (amount, tipe, category, description))

    created_at = cur.fetchone()[0]

    conn.commit()
    cur.close()
    conn.close()

    return created_at

# ======================
# SUMMARY
# ======================
def get_summary():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT type, SUM(amount)
        FROM transactions
        GROUP BY type
    """)

    data = cur.fetchall()

    cur.close()
    conn.close()

    return data

# ======================
# TODAY SUMMARY
# ======================
def get_today_summary():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT type, SUM(amount)
        FROM transactions
        WHERE DATE(created_at) = CURRENT_DATE
        GROUP BY type
    """)

    data = cur.fetchall()

    cur.close()
    conn.close()

    return data

# ======================
# MONTH SUMMARY
# ======================
def get_month_summary():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT type, SUM(amount)
        FROM transactions
        WHERE DATE_TRUNC('month', created_at) = DATE_TRUNC('month', CURRENT_DATE)
        GROUP BY type
    """)

    data = cur.fetchall()

    cur.close()
    conn.close()

    return data

# ======================
# CATEGORY SUMMARY
# ======================
def get_category_summary():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT category, SUM(amount)
        FROM transactions
        WHERE type = 'expense'
        GROUP BY category
        ORDER BY SUM(amount) DESC
    """)

    data = cur.fetchall()

    cur.close()
    conn.close()

    return data

# ======================
# TODAY CATEGORY
# ======================
def get_today_category_summary():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT category, SUM(amount)
        FROM transactions
        WHERE type = 'expense'
        AND DATE(created_at) = CURRENT_DATE
        GROUP BY category
        ORDER BY SUM(amount) DESC
    """)

    data = cur.fetchall()

    cur.close()
    conn.close()

    return data

# ======================
# TOTAL SUMMARY
# ======================
def get_total_summary():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT type, SUM(amount)
        FROM transactions
        GROUP BY type
    """)

    data = cur.fetchall()

    cur.close()
    conn.close()

    return data

# ======================
# DELETE FUNCTIONS
# ======================
def delete_today():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        DELETE FROM transactions
        WHERE DATE(created_at) = CURRENT_DATE
    """)

    deleted = cur.rowcount

    conn.commit()
    cur.close()
    conn.close()

    return deleted


def delete_week():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        DELETE FROM transactions
        WHERE DATE_TRUNC('week', created_at) = DATE_TRUNC('week', CURRENT_DATE)
    """)

    deleted = cur.rowcount

    conn.commit()
    cur.close()
    conn.close()

    return deleted


def delete_month():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        DELETE FROM transactions
        WHERE DATE_TRUNC('month', created_at) = DATE_TRUNC('month', CURRENT_DATE)
    """)

    deleted = cur.rowcount

    conn.commit()
    cur.close()
    conn.close()

    return deleted


def delete_year():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        DELETE FROM transactions
        WHERE DATE_TRUNC('year', created_at) = DATE_TRUNC('year', CURRENT_DATE)
    """)

    deleted = cur.rowcount

    conn.commit()
    cur.close()
    conn.close()

    return deleted