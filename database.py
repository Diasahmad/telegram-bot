import os
import psycopg2

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL tidak ditemukan")

# ======================
# CONNECTION
# ======================
def get_connection():
    return psycopg2.connect(DATABASE_URL)

# ======================
# INIT TABLE
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
# SAVE
# ======================
def save_transaction(amount, tipe, category, description):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO transactions (amount, type, category, description) VALUES (%s, %s, %s, %s)",
        (amount, tipe, category, description)
    )

    conn.commit()
    cur.close()
    conn.close()

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

    result = cur.fetchall()

    cur.close()
    conn.close()
    return result

# ======================
# TODAY
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

    result = cur.fetchall()

    cur.close()
    conn.close()
    return result

# ======================
# MONTH
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

    result = cur.fetchall()

    cur.close()
    conn.close()
    return result

# ======================
# CATEGORY
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

    result = cur.fetchall()

    cur.close()
    conn.close()
    return result

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

    result = cur.fetchall()

    cur.close()
    conn.close()
    return result

# ======================
# TOTAL
# ======================
def get_total_summary():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT type, SUM(amount)
        FROM transactions
        GROUP BY type
    """)

    result = cur.fetchall()

    cur.close()
    conn.close()
    return result