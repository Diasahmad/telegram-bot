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
# TIME HELPERS (WAJIB KONSISTEN)
# ======================
def wib(expr="created_at"):
    return f"{expr} AT TIME ZONE 'Asia/Jakarta'"

def now_wib():
    return "CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Jakarta'"

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
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_created_at 
        ON transactions(created_at)
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
        SELECT type, COALESCE(SUM(amount), 0)
        FROM transactions
        GROUP BY type
    """)

    data = cur.fetchall()
    cur.close()
    conn.close()
    return data

def get_total_summary():
    return get_summary()

# ======================
# TODAY
# ======================
def get_today_summary():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(f"""
        SELECT type, COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE DATE({wib()}) = DATE({now_wib()})
        GROUP BY type
    """)

    data = cur.fetchall()
    cur.close()
    conn.close()
    return data

def get_today_transactions():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(f"""
        SELECT id, amount, type, category, description, created_at
        FROM transactions
        WHERE DATE({wib()}) = DATE({now_wib()})
        ORDER BY created_at DESC
    """)

    data = cur.fetchall()
    cur.close()
    conn.close()
    return data

# ======================
# MONTH
# ======================
def get_month_summary():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(f"""
        SELECT type, COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE DATE_TRUNC('month', {wib()}) =
              DATE_TRUNC('month', {now_wib()})
        GROUP BY type
    """)

    data = cur.fetchall()
    cur.close()
    conn.close()
    return data

# ======================
# YEAR
# ======================
def get_year_summary():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(f"""
        SELECT 
            EXTRACT(MONTH FROM {wib()}) AS month,
            type,
            COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE DATE_TRUNC('year', {wib()}) =
              DATE_TRUNC('year', {now_wib()})
        GROUP BY month, type
        ORDER BY month
    """)

    data = cur.fetchall()
    cur.close()
    conn.close()
    return data

# ======================
# BY DATE
# ======================
def get_transactions_by_date(date):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(f"""
        SELECT id, amount, type, category, description, created_at
        FROM transactions
        WHERE DATE({wib()}) = %s
        ORDER BY created_at DESC
    """, (date,))

    data = cur.fetchall()
    cur.close()
    conn.close()
    return data

# ======================
# MONTH BY YEAR
# ======================
def get_month_summary_by_year(month, year):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(f"""
        SELECT type, COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE EXTRACT(MONTH FROM {wib()}) = %s
        AND EXTRACT(YEAR FROM {wib()}) = %s
        GROUP BY type
    """, (int(month), int(year)))

    data = cur.fetchall()
    cur.close()
    conn.close()
    return data

def get_year_monthly_summary(year):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(f"""
        SELECT 
            EXTRACT(MONTH FROM {wib()}),
            type,
            COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE EXTRACT(YEAR FROM {wib()}) = %s
        GROUP BY 1, type
        ORDER BY 1
    """, (year,))

    data = cur.fetchall()
    cur.close()
    conn.close()
    return data

# ======================
# CATEGORY
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

def get_today_category_summary():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(f"""
        SELECT category, COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE type = 'expense'
        AND DATE({wib()}) = DATE({now_wib()})
        GROUP BY category
        ORDER BY SUM(amount) DESC
    """)

    data = cur.fetchall()
    cur.close()
    conn.close()
    return data

def get_month_category_summary(month, year):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(f"""
        SELECT category, COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE type = 'expense'
        AND EXTRACT(MONTH FROM {wib()}) = %s
        AND EXTRACT(YEAR FROM {wib()}) = %s
        GROUP BY category
        ORDER BY SUM(amount) DESC
    """, (int(month), int(year)))

    data = cur.fetchall()
    cur.close()
    conn.close()
    return data

# ======================
# RANK
# ======================
def get_rank_by_date(date):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(f"""
        SELECT category, COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE type = 'expense'
        AND DATE({wib()}) = %s
        GROUP BY category
        ORDER BY SUM(amount) DESC
    """, (date,))

    data = cur.fetchall()
    cur.close()
    conn.close()
    return data

def get_rank_by_month(month, year):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(f"""
        SELECT category, COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE type = 'expense'
        AND EXTRACT(MONTH FROM {wib()}) = %s
        AND EXTRACT(YEAR FROM {wib()}) = %s
        GROUP BY category
        ORDER BY SUM(amount) DESC
    """, (int(month), int(year)))

    data = cur.fetchall()
    cur.close()
    conn.close()
    return data

def get_rank_by_year(year):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(f"""
        SELECT category, COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE type = 'expense'
        AND EXTRACT(YEAR FROM {wib()}) = %s
        GROUP BY category
        ORDER BY SUM(amount) DESC
    """, (year,))

    data = cur.fetchall()
    cur.close()
    conn.close()
    return data

# ======================
# DELETE
# ======================
def delete_range(mode):
    conn = get_connection()
    cur = conn.cursor()

    if mode == "today":
        query = f"""
        DELETE FROM transactions
        WHERE DATE({wib()}) = DATE({now_wib()})
        """

    elif mode == "week":
        query = f"""
        DELETE FROM transactions
        WHERE DATE_TRUNC('week', {wib()}) =
              DATE_TRUNC('week', {now_wib()})
        """

    elif mode == "month":
        query = f"""
        DELETE FROM transactions
        WHERE DATE_TRUNC('month', {wib()}) =
              DATE_TRUNC('month', {now_wib()})
        """

    elif mode == "year":
        query = f"""
        DELETE FROM transactions
        WHERE DATE_TRUNC('year', {wib()}) =
              DATE_TRUNC('year', {now_wib()})
        """

    else:
        return 0

    cur.execute(query)
    deleted = cur.rowcount

    conn.commit()
    cur.close()
    conn.close()

    return deleted

def delete_by_id(transaction_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM transactions WHERE id = %s", (transaction_id,))
    deleted = cur.rowcount

    conn.commit()
    cur.close()
    conn.close()

    return deleted

# ======================
# UPDATE
# ======================
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