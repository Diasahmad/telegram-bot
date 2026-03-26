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
            amount INTEGER NOT NULL,
            type TEXT NOT NULL CHECK (type IN ('income', 'expense')),
            category TEXT,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # INDEX untuk performa (ini krusial, bukan opsional)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_created_at 
        ON transactions(created_at)
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
# SUMMARY (ALL TIME)
# ======================
def get_summary():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT type, COALESCE(SUM(amount), 0)
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
        SELECT type, COALESCE(SUM(amount), 0)
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
        SELECT type, COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE DATE_TRUNC('month', created_at) = DATE_TRUNC('month', CURRENT_DATE)
        GROUP BY type
    """)

    data = cur.fetchall()

    cur.close()
    conn.close()

    return data

# ======================
# YEAR SUMMARY (INI YANG KAMU BUTUHKAN)
# ======================
def get_year_summary():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            EXTRACT(MONTH FROM created_at) AS month,
            type,
            COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE DATE_TRUNC('year', created_at) = DATE_TRUNC('year', CURRENT_DATE)
        GROUP BY month, type
        ORDER BY month
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
        SELECT category, COALESCE(SUM(amount), 0)
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
# TODAY CATEGORY RANK
# ======================
def get_today_category_summary():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT category, COALESCE(SUM(amount), 0)
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

# RANK HARI
# ======================
def get_rank_by_date(date):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT category, SUM(amount)
        FROM transactions
        WHERE type = 'expense'
        AND DATE(created_at) = %s
        GROUP BY category
        ORDER BY SUM(amount) DESC
    """, (date,))

    data = cur.fetchall()

    cur.close()
    conn.close()

    return data

# RANK BULAN
# ======================
def get_rank_by_month(month, year):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT category, SUM(amount)
        FROM transactions
        WHERE type = 'expense'
        AND EXTRACT(MONTH FROM created_at) = %s
        AND EXTRACT(YEAR FROM created_at) = %s
        GROUP BY category
        ORDER BY SUM(amount) DESC
    """, (month, year))

    data = cur.fetchall()

    cur.close()
    conn.close()

    return data

# RANK TAHUN
# ======================
def get_rank_by_year(year):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT category, SUM(amount)
        FROM transactions
        WHERE type = 'expense'
        AND EXTRACT(YEAR FROM created_at) = %s
        GROUP BY category
        ORDER BY SUM(amount) DESC
    """, (year,))

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
        SELECT type, COALESCE(SUM(amount), 0)
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

def delete_range(mode):
    if mode == "today":
        return delete_today()
    elif mode == "week":
        return delete_week()
    elif mode == "month":
        return delete_month()
    elif mode == "year":
        return delete_year()
    else:
        return None

def delete_by_id(transaction_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        DELETE FROM transactions
        WHERE id = %s
    """, (transaction_id,))

    deleted = cur.rowcount

    conn.commit()
    cur.close()
    conn.close()

    return deleted

def get_today_transactions():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, amount, type, category, description, created_at
        FROM transactions
        WHERE DATE(created_at) = CURRENT_DATE
        ORDER BY created_at DESC
    """)

    data = cur.fetchall()

    cur.close()
    conn.close()

    return data

def update_transaction_amount(transaction_id, new_amount):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE transactions
        SET amount = %s
        WHERE id = %s
    """, (new_amount, transaction_id))

    updated = cur.rowcount

    conn.commit()
    cur.close()
    conn.close()

    return updated

def get_transactions_by_date(date):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, amount, type, category, description, created_at
        FROM transactions
        WHERE DATE(created_at) = %s
        ORDER BY created_at DESC
    """, (date,))

    data = cur.fetchall()

    cur.close()
    conn.close()

    return data

def get_month_summary_by_year(month, year):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT type, SUM(amount)
        FROM transactions
        WHERE EXTRACT(MONTH FROM created_at) = %s
        AND EXTRACT(YEAR FROM created_at) = %s
        GROUP BY type
    """, (month, year))

    data = cur.fetchall()

    cur.close()
    conn.close()

    return data

def get_year_monthly_summary(year):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            EXTRACT(MONTH FROM created_at) AS month,
            type,
            SUM(amount)
        FROM transactions
        WHERE EXTRACT(YEAR FROM created_at) = %s
        GROUP BY month, type
        ORDER BY month
    """, (year,))

    data = cur.fetchall()

    cur.close()
    conn.close()

    return data

