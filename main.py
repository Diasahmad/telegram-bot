import os
import re
from datetime import datetime

from parser import parse_transaction
from database import (
    save_transaction,
    get_summary,
    get_today_summary,
    get_rank_by_date,
    get_rank_by_month,
    get_rank_by_year,
    get_month_summary,
    get_category_summary,
    get_total_summary,
    get_today_category_summary,
    get_year_summary,
    init_db,
    delete_range,
    get_today_transactions, 
    update_transaction_amount,
    delete_by_id,
    get_transactions_by_date, 
    get_month_summary_by_year, 
    get_year_monthly_summary,
    get_month_category_summary
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
    raise ValueError("BOT_TOKEN tidak ditemukan")

# ======================
# FORMAT
# ======================
def format_rupiah(angka):
    return f"{angka:,}".replace(",", ".")

def format_tanggal(dt):
    bulan = [
        "Januari", "Februari", "Maret", "April", "Mei", "Juni",
        "Juli", "Agustus", "September", "Oktober", "November", "Desember"
    ]
    return f"{dt.day} {bulan[dt.month - 1]} {dt.year}, {dt.hour:02d}:{dt.minute:02d}"

# ======================
# HELPER
# ======================
def extract_income_expense(data):
    income, expense = 0, 0
    for row in data:
        if row[0] == "income":
            income = row[1] or 0
        elif row[0] == "expense":
            expense = row[1] or 0
    return income, expense

# ======================
# ALERT
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
# START
# ======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot aktif.")

# ======================
# INPUT DATA
# ======================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    try:
        data = parse_transaction(text)
    except:
        await update.message.reply_text("Format tidak dikenali.")
        return

    if not data.get("amount"):
        await update.message.reply_text("Tidak bisa membaca jumlah.")
        return

    if data.get("type") == "unknown":
        await update.message.reply_text("Tidak jelas pemasukan atau pengeluaran.")
        return

    created_at = save_transaction(
        data["amount"],
        data["type"],
        data["category"],
        data["description"]
    )

    tipe = "Pemasukan" if data["type"] == "income" else "Pengeluaran"

    await update.message.reply_text(
        f"Tercatat:\n"
        f"Tanggal: {format_tanggal(created_at)}\n"
        f"Jumlah: {format_rupiah(data['amount'])}\n"
        f"Tipe: {tipe}\n"
        f"Kategori: {data['category']}\n"
        f"Deskripsi: {data['description']}"
    )

    alert = check_alert()
    if alert:
        await update.message.reply_text(alert)

# ======================
# SUMMARY
# ======================
async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = get_summary()
    income, expense = extract_income_expense(data)

    await update.message.reply_text(
        f"Pemasukan: {format_rupiah(income)}\n"
        f"Pengeluaran: {format_rupiah(expense)}\n"
        f"Saldo: {format_rupiah(income - expense)}"
    )

async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = get_today_summary()
    income, expense = extract_income_expense(data)

    await update.message.reply_text(
        f"Hari ini:\n"
        f"+ {format_rupiah(income)}\n"
        f"- {format_rupiah(expense)}\n"
        f"= {format_rupiah(income - expense)}"
    )

async def month(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = get_month_summary()
    income, expense = extract_income_expense(data)

    await update.message.reply_text(
        f"Bulan ini:\n"
        f"+ {format_rupiah(income)}\n"
        f"- {format_rupiah(expense)}\n"
        f"= {format_rupiah(income - expense)}"
    )

# ======================
# HISTORY
# ======================
async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args

    if not args:
        data = get_today_transactions()

        if not data:
            await update.message.reply_text("Tidak ada data hari ini.")
            return

        text = "History Hari Ini:\n\n"

        for i, row in enumerate(data, 1):
            trx_id, amount, tipe, kategori, desc, created_at = row
            simbol = "+" if tipe == "income" else "-"

            text += (
                f"{i}. (ID:{trx_id})\n"
                f"{simbol} {format_rupiah(amount)} | {kategori}\n"
                f"{desc}\n"
                f"{format_tanggal(created_at)}\n\n"
            )

        await update.message.reply_text(text)
        return

    arg = args[0]

    # DD-MM-YYYY
    if re.match(r"\d{2}-\d{2}-\d{4}", arg):
        d, m, y = map(int, arg.split("-"))
        date = f"{y:04d}-{m:02d}-{d:02d}"

        data = get_transactions_by_date(date)

        if not data:
            await update.message.reply_text("Tidak ada data.")
            return

        text = f"History {arg}:\n\n"

        for i, row in enumerate(data, 1):
            trx_id, amount, tipe, kategori, desc, created_at = row
            simbol = "+" if tipe == "income" else "-"

            text += (
                f"{i}. (ID:{trx_id})\n"
                f"{simbol} {format_rupiah(amount)} | {kategori}\n"
                f"{desc}\n"
                f"{format_tanggal(created_at)}\n\n"
            )

        await update.message.reply_text(text)
        return

    await update.message.reply_text("Format salah.")

# ======================
# RANK
# ======================
async def rank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = get_today_category_summary()

    if not data:
        await update.message.reply_text("Tidak ada data.")
        return

    text = "Ranking Hari Ini:\n\n"

    for i, row in enumerate(data, 1):
        text += f"{i}. {row[0]} - {format_rupiah(row[1])}\n"

    await update.message.reply_text(text)

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
    app.add_handler(CommandHandler("history", history))
    app.add_handler(CommandHandler("rank", rank))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()