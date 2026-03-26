import os
from datetime import datetime, timedelta

from parser import parse_transaction
from database import (
    save_transaction,
    get_summary,
    get_today_summary,
    get_month_summary,
    get_category_summary,
    get_total_summary,
    get_today_category_summary,
    init_db
)

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# ======================
# ENV
# ======================
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("BOT_TOKEN tidak ditemukan di environment variables")

# ======================
# FORMAT RUPIAH
# ======================
def format_rupiah(angka):
    return f"{angka:,}".replace(",", ".")

# ======================
# FORMAT TANGGAL
# ======================
def format_tanggal(dt):
    bulan = [
        "Januari", "Februari", "Maret", "April", "Mei", "Juni",
        "Juli", "Agustus", "September", "Oktober", "November", "Desember"
    ]
    return f"{dt.day} {bulan[dt.month - 1]} {dt.year}, {dt.hour:02d}:{dt.minute:02d}"

def adjust_timezone(dt):
    return dt + timedelta(hours=7)

# ======================
# ALERT SYSTEM
# ======================
def check_alert():
    data = get_category_summary()

    if not data:
        return None

    total = sum(row[1] for row in data if row[1])

    if total == 0:
        return None

    top_category, top_value = data[0]
    persen = (top_value / total) * 100

    if persen > 60:
        return f"🚨 KRITIS: {top_category} ({persen:.1f}%) sangat dominan"
    elif persen > 50:
        return f"⚠️ Warning: {top_category} sudah dominan ({persen:.1f}%)"
    elif persen > 40:
        return f"⚡ Perhatian: {top_category} mulai besar ({persen:.1f}%)"

    return None

# ======================
# COMMAND START
# ======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text("Bot aktif.")

# ======================
# HANDLE MESSAGE
# ======================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text
    print(f"Pesan masuk: {text}")

    # Parsing
    try:
        data = parse_transaction(text)
    except Exception as e:
        print(f"Parse error: {e}")
        await update.message.reply_text("Format tidak dikenali.")
        return

    if not data.get("amount"):
        await update.message.reply_text("Tidak bisa membaca jumlah.")
        return

    if data.get("type") == "unknown":
        await update.message.reply_text("Tidak jelas pemasukan atau pengeluaran.")
        return

    # Simpan ke DB
    try:
        created_at = save_transaction(
            data["amount"],
            data["type"],
            data["category"],
            data["description"]
        )
    except Exception as e:
        print(f"DB error: {e}")
        await update.message.reply_text("Gagal menyimpan data.")
        return

    # Format output
    type_text = "Pemasukan" if data["type"] == "income" else "Pengeluaran"

    created_at = adjust_timezone(created_at)
    tanggal = format_tanggal(created_at)

    await update.message.reply_text(
        f"Tercatat:\n"
        f"Tanggal: {tanggal}\n"
        f"Jumlah: {format_rupiah(data['amount'])}\n"
        f"Tipe: {type_text}\n"
        f"Kategori: {data['category']}\n"
        f"Deskripsi: {data['description']}"
    )

    # Alert
    alert = check_alert()
    if alert:
        await update.message.reply_text(alert)

# ======================
# SUMMARY TOTAL
# ======================
async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = get_summary()

    income, expense = 0, 0

    for row in data:
        if row[0] == "income":
            income = row[1] or 0
        elif row[0] == "expense":
            expense = row[1] or 0

    balance = income - expense

    if update.message:
        await update.message.reply_text(
            f"Ringkasan Uang:\n"
            f"Pemasukan: {format_rupiah(income)}\n"
            f"Pengeluaran: {format_rupiah(expense)}\n"
            f"Saldo: {format_rupiah(balance)}"
        )

# ======================
# TODAY
# ======================
async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = get_today_summary()

    income, expense = 0, 0

    for row in data:
        if row[0] == "income":
            income = row[1] or 0
        elif row[0] == "expense":
            expense = row[1] or 0

    balance = income - expense

    if update.message:
        await update.message.reply_text(
            f"Hari ini:\n"
            f"Pemasukan: {format_rupiah(income)}\n"
            f"Pengeluaran: {format_rupiah(expense)}\n"
            f"Saldo: {format_rupiah(balance)}"
        )

# ======================
# MONTH
# ======================
async def month(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = get_month_summary()

    income, expense = 0, 0

    for row in data:
        if row[0] == "income":
            income = row[1] or 0
        elif row[0] == "expense":
            expense = row[1] or 0

    balance = income - expense

    if update.message:
        await update.message.reply_text(
            f"Bulan ini:\n"
            f"Pemasukan: {format_rupiah(income)}\n"
            f"Pengeluaran: {format_rupiah(expense)}\n"
            f"Saldo: {format_rupiah(balance)}"
        )

# ======================
# RANK
# ======================
async def rank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = get_today_category_summary()

    text = "Ranking Pengeluaran Hari Ini:\n\n"

    if data:
        total_today = sum(row[1] for row in data if row[1])

        for i, row in enumerate(data, start=1):
            kategori = row[0]
            total = row[1] or 0
            persen = (total / total_today) * 100 if total_today else 0

            text += f"{i}. {kategori} - {format_rupiah(total)} ({persen:.1f}%)\n"

        text += f"\nTotal: {format_rupiah(total_today)}"
    else:
        text += "Belum ada pengeluaran hari ini."

    # Bulan
    month_data = get_month_summary()
    income, expense = 0, 0

    for row in month_data:
        if row[0] == "income":
            income = row[1] or 0
        elif row[0] == "expense":
            expense = row[1] or 0

    text += "\n\n--- Bulan Ini ---\n"
    text += f"Pemasukan: {format_rupiah(income)}\n"
    text += f"Pengeluaran: {format_rupiah(expense)}\n"
    text += f"Saldo: {format_rupiah(income - expense)}"

    # Total
    total_data = get_total_summary()
    total_income, total_expense = 0, 0

    for row in total_data:
        if row[0] == "income":
            total_income = row[1] or 0
        elif row[0] == "expense":
            total_expense = row[1] or 0

    text += "\n\n--- Total ---\n"
    text += f"Saldo: {format_rupiah(total_income - total_expense)}"

    if update.message:
        await update.message.reply_text(text)

# ======================
# ERROR HANDLER
# ======================
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    print(f"Error global: {context.error}")

# ======================
# MAIN
# ======================
def main():
    init_db()

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("summary", summary))
    app.add_handler(CommandHandler("today", today))
    app.add_handler(CommandHandler("month", month))
    app.add_handler(CommandHandler("rank", rank))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.add_error_handler(error_handler)

    print("Bot berjalan di Railway...")
    app.run_polling()

if __name__ == "__main__":
    main()