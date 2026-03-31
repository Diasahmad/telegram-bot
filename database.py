import os
import psycopg

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL tidak ditemukan")

def get_connection():
    return psycopg.connect(DATABASE_URL)

# ======================
# TIME (SATU SUMBER KEBENARAN)
# ======================
def wib(expr="created_at"):
    return f"{expr} AT TIME ZONE 'Asia/Jakarta'"

def now_wib():
    return "CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Jakarta'"

def today_range():
    return f"""
    {wib()} >= DATE_TRUNC('day', {now_wib()})
    AND {wib()} < DATE_TRUNC('day', {now_wib()}) + INTERVAL '1 day'
    """

# ======================
# INIT
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
        RETURNING created_at AT TIME ZONE 'Asia/Jakarta'
    """, (amount, tipe, category, description))

    created_at = cur.fetchone()[0]

    conn.commit()
    cur.close()
    conn.close()

    return created_at

# ======================
# TODAY
# ======================
def get_today_transactions():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(f"""
        SELECT id, amount, type, category, description,
               {wib()} AS created_at
        FROM transactions
        WHERE {today_range()}
        ORDER BY created_at DESC
    """)

    data = cur.fetchall()
    cur.close()
    conn.close()
    return data

def get_today_summary():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(f"""
        SELECT type, COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE {today_range()}
        GROUP BY type
    """)

    data = cur.fetchall()
    cur.close()
    conn.close()
    return data

# ======================
# BY DATE (FIX RANGE)
# ======================
def get_transactions_by_date(date):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(f"""
        SELECT id, amount, type, category, description,
               {wib()} AS created_at
        FROM transactions
        WHERE {wib()} >= %s
        AND {wib()} < (%s::date + INTERVAL '1 day')
        ORDER BY created_at DESC
    """, (date, date))

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
        AND {today_range()}
        GROUP BY category
        ORDER BY SUM(amount) DESC
    """)

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
        AND {wib()} >= %s
        AND {wib()} < (%s::date + INTERVAL '1 day')
        GROUP BY category
        ORDER BY SUM(amount) DESC
    """, (date, date))

    data = cur.fetchall()
    cur.close()
    conn.close()
    return data

# ======================
# DELETE (FIX RANGE)
# ======================
def delete_range(mode):
    conn = get_connection()
    cur = conn.cursor()

    if mode == "today":
        query = f"DELETE FROM transactions WHERE {today_range()}"

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