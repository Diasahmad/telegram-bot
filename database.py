import os
import psycopg

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL tidak ditemukan")

# ======================
# CONNECTION
# ======================
def get_connection():
    try:
        return psycopg.connect(DATABASE_URL)
    except Exception as e:
        print("DB CONNECTION ERROR:", e)
        raise


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

    cur.execute("""
        INSERT INTO transactions (amount, type, category, description)
        VALUES (%s, %s, %s, %s)
        RETURNING id, created_at
    """, (amount, tipe, category, description))

    result = cur.fetchone()

    conn.commit()
    cur.close()
    conn.close()

    return result  # (id, created_at)


# ======================
# GET BY PERIOD (UNTUK LIST)
# ======================
def get_transactions_by_period(period="today"):
    conn = get_connection()
    cur = conn.cursor()

    if period == "today":
        query = "DATE(created_at) = CURRENT_DATE"
    elif period == "week":
        query = "DATE_TRUNC('week', created_at) = DATE_TRUNC('week', CURRENT_DATE)"
    elif period == "month":
        query = "DATE_TRUNC('month', created_at) = DATE_TRUNC('month', CURRENT_DATE)"
    elif period == "year":
        query = "DATE_TRUNC('year', created_at) = DATE_TRUNC('year', CURRENT_DATE)"
    else:
        query = "TRUE"

    cur.execute(f"""
        SELECT id, amount, type, category, description, created_at
        FROM transactions
        WHERE {query}
        ORDER BY created_at DESC
    """)

    result = cur.fetchall()

    cur.close()
    conn.close()
    return result


# ======================
# UPDATE
# ======================
def update_transaction(transaction_id, amount=None, tipe=None, category=None, description=None):
    conn = get_connection()
    cur = conn.cursor()

    fields = []
    values = []

    if amount is not None:
        fields.append("amount = %s")
        values.append(amount)

    if tipe is not None:
        fields.append("type = %s")
        values.append(tipe)

    if category is not None:
        fields.append("category = %s")
        values.append(category)

    if description is not None:
        fields.append("description = %s")
        values.append(description)

    if not fields:
        return False

    values.append(transaction_id)

    query = f"""
        UPDATE transactions
        SET {", ".join(fields)}
        WHERE id = %s
    """

    cur.execute(query, values)

    conn.commit()
    cur.close()
    conn.close()

    return True


# ======================
# DELETE
# ======================
def delete_transaction(transaction_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        DELETE FROM transactions
        WHERE id = %s
    """, (transaction_id,))

    conn.commit()
    cur.close()
    conn.close()

    return True


# ======================
# SUMMARY (FLEXIBLE)
# ======================
def get_summary(period=None):
    conn = get_connection()
    cur = conn.cursor()

    filter_query = "TRUE"

    if period == "today":
        filter_query = "DATE(created_at) = CURRENT_DATE"
    elif period == "week":
        filter_query = "DATE_TRUNC('week', created_at) = DATE_TRUNC('week', CURRENT_DATE)"
    elif period == "month":
        filter_query = "DATE_TRUNC('month', created_at) = DATE_TRUNC('month', CURRENT_DATE)"
    elif period == "year":
        filter_query = "DATE_TRUNC('year', created_at) = DATE_TRUNC('year', CURRENT_DATE)"

    cur.execute(f"""
        SELECT type, SUM(amount)
        FROM transactions
        WHERE {filter_query}
        GROUP BY type
    """)

    result = cur.fetchall()

    cur.close()
    conn.close()
    return result


# ======================
# CATEGORY SUMMARY
# ======================
def get_category_summary(period=None):
    conn = get_connection()
    cur = conn.cursor()

    filter_query = "TRUE"

    if period == "today":
        filter_query = "DATE(created_at) = CURRENT_DATE"
    elif period == "week":
        filter_query = "DATE_TRUNC('week', created_at) = DATE_TRUNC('week', CURRENT_DATE)"
    elif period == "month":
        filter_query = "DATE_TRUNC('month', created_at) = DATE_TRUNC('month', CURRENT_DATE)"
    elif period == "year":
        filter_query = "DATE_TRUNC('year', created_at) = DATE_TRUNC('year', CURRENT_DATE)"

    cur.execute(f"""
        SELECT category, SUM(amount)
        FROM transactions
        WHERE type = 'expense'
        AND {filter_query}
        GROUP BY category
        ORDER BY SUM(amount) DESC
    """)

    result = cur.fetchall()

    cur.close()
    conn.close()
    return result

# ======================
# YEARLY SUMMARY (BARU)
# ======================
def get_yearly_summary():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            DATE_TRUNC('month', created_at) AS month,
            type,
            SUM(amount)
        FROM transactions
        WHERE DATE_TRUNC('year', created_at) = DATE_TRUNC('year', CURRENT_DATE)
        GROUP BY month, type
        ORDER BY month
    """)

    result = cur.fetchall()

    cur.close()
    conn.close()
    return result

# ======================
# PREVIOUS MONTH (INSIGHT)
# ======================
def get_previous_month_summary():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT type, SUM(amount)
        FROM transactions
        WHERE DATE_TRUNC('month', created_at) =
              DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')
        GROUP BY type
    """)

    result = cur.fetchall()

    cur.close()
    conn.close()
    return result