import os
from datetime import timedelta

from parser import parse_transaction
from database import (
    save_transaction,
    get_summary,
    get_transactions_by_period,
    update_transaction,
    delete_transaction,
    get_category_summary,
    get_previous_month_summary,
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

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("BOT_TOKEN tidak ditemukan")

# ======================
# STATE
# ======================
user_state = {}
user_last_list = {}

# ======================
# UTIL
# ======================
def format_rupiah(x):
    return f"{x:,}".replace(",", ".")

def adjust_timezone(dt):
    return dt + timedelta(hours=7)

# ======================
# START
# ======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 BOT KEUANGAN\n\n"
        "📌 Input langsung:\n"
        "- beli makan 20k\n"
        "- gaji 3jt\n\n"
        "⚙️ Command:\n"
        "/list [today|week|month|year]\n"
        "/summary [period]\n"
        "/insight\n"
        "/edit <id> field=value\n"
        "/delete <id>\n"
        "/delete 1-5 (range)\n"
        "/help"
    )

# ======================
# HELP
# ======================
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 BANTUAN\n\n"
        "INPUT:\n"
        "beli kopi 20k\n\n"
        "COMMAND:\n"
        "/list → lihat data\n"
        "/summary → ringkasan\n"
        "/insight → analisis\n"
        "/edit → edit data\n"
        "/delete → hapus data\n"
        "/delete 1-5 → hapus range\n\n"
        "⚠️ Gunakan /list sebelum delete range"
    )

# ======================
# HANDLE MESSAGE
# ======================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.lower()

    # ===== CONFIRM SAVE =====
    if user_id in user_state and user_state[user_id]["action"] == "confirm_save":
        if text in ["ya", "y"]:
            data = user_state[user_id]["data"]

            tid, _ = save_transaction(
                data["amount"],
                data["type"],
                data["category"],
                data["description"]
            )

            await update.message.reply_text(
                f"✅ Disimpan\nID: {tid}\n"
                f"{data['category']} - Rp {format_rupiah(data['amount'])}"
            )

        else:
            await update.message.reply_text("❌ Dibatalkan")

        del user_state[user_id]
        return

    # ===== CONFIRM DELETE =====
    if user_id in user_state:

        # SINGLE
        if user_state[user_id]["action"] == "confirm_delete":
            if text in ["ya", "y"]:
                tid = user_state[user_id]["id"]
                delete_transaction(tid)
                await update.message.reply_text(f"🗑️ ID {tid} dihapus")
            else:
                await update.message.reply_text("❌ Batal")

            del user_state[user_id]
            return

        # RANGE
        if user_state[user_id]["action"] == "confirm_delete_range":
            if text in ["ya", "y"]:
                ids = user_state[user_id]["ids"]

                for tid in ids:
                    delete_transaction(tid)

                await update.message.reply_text(
                    f"🗑️ {len(ids)} data dihapus"
                )
            else:
                await update.message.reply_text("❌ Batal")

            del user_state[user_id]
            return

    # ===== PARSE =====
    data = parse_transaction(text)

    if not data["amount"]:
        await update.message.reply_text("❌ Jumlah tidak terbaca")
        return

    if data["type"] == "unknown":
        await update.message.reply_text("❌ Tipe tidak jelas")
        return

    user_state[user_id] = {
        "action": "confirm_save",
        "data": data
    }

    await update.message.reply_text(
        f"Konfirmasi:\n\n"
        f"Tipe: {data['type']}\n"
        f"Jumlah: Rp {format_rupiah(data['amount'])}\n"
        f"Kategori: {data['category']}\n"
        f"Deskripsi: {data['description']}\n\n"
        f"Ketik 'ya' atau 'batal'"
    )

# ======================
# LIST
# ======================
async def list_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    period = context.args[0] if context.args else "today"

    data = get_transactions_by_period(period)

    if not data:
        await update.message.reply_text("Tidak ada data.")
        return

    user_last_list[user_id] = data

    text = f"📋 Data ({period})\n\n"

    for i, row in enumerate(data, start=1):
        id_, amount, tipe, category, desc, _ = row

        text += (
            f"{i}. [{id_}] {category.upper()}\n"
            f"   Rp {format_rupiah(amount)}\n"
            f"   {desc}\n\n"
        )

    await update.message.reply_text(text)

# ======================
# SUMMARY
# ======================
async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    period = context.args[0] if context.args else None
    data = get_summary(period)

    income, expense = 0, 0
    for t, v in data:
        if t == "income":
            income = v or 0
        elif t == "expense":
            expense = v or 0

    await update.message.reply_text(
        f"💰 Summary\n\n"
        f"Pemasukan: Rp {format_rupiah(income)}\n"
        f"Pengeluaran: Rp {format_rupiah(expense)}\n"
        f"Saldo: Rp {format_rupiah(income-expense)}"
    )

# ======================
# INSIGHT
# ======================
async def insight(update: Update, context: ContextTypes.DEFAULT_TYPE):

    current = get_summary("month")
    prev = get_previous_month_summary()

    income, expense = 0, 0
    for t, v in current:
        if t == "income": income = v or 0
        if t == "expense": expense = v or 0

    prev_expense = 0
    for t, v in prev:
        if t == "expense": prev_expense = v or 0

    categories = get_category_summary("month")

    text = "📊 INSIGHT\n\n"

    if expense > income:
        text += "❌ Defisit\n"
    else:
        text += "✅ Surplus\n"

    if categories:
        cat, val = categories[0]
        total = sum(x[1] for x in categories if x[1])
        persen = (val / total) * 100 if total else 0

        text += f"\nTop: {cat} ({persen:.1f}%)"

        if persen > 50:
            text += " ⚠️ Dominan"

    if prev_expense:
        change = ((expense - prev_expense) / prev_expense) * 100
        text += f"\nTrend: {change:.1f}%"

    await update.message.reply_text(text)

# ======================
# DELETE
# ======================
async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    if not context.args:
        await update.message.reply_text("Gunakan /delete <id> atau <range>")
        return

    arg = context.args[0]

    # RANGE
    if "-" in arg:
        if uid not in user_last_list:
            await update.message.reply_text("Gunakan /list dulu")
            return

        try:
            start, end = map(int, arg.split("-"))
            data = user_last_list[uid]

            if start < 1 or end > len(data) or start > end:
                await update.message.reply_text("Range tidak valid")
                return

            selected = data[start-1:end]
            ids = [row[0] for row in selected]

            preview = "\n".join([f"{i+start}. ID {row[0]}" for i, row in enumerate(selected)])

            user_state[uid] = {
                "action": "confirm_delete_range",
                "ids": ids
            }

            await update.message.reply_text(
                f"⚠️ Hapus {len(ids)} data:\n\n{preview}\n\n"
                f"Ketik 'ya' atau 'batal'"
            )

        except:
            await update.message.reply_text("Format salah. /delete 1-5")

        return

    # SINGLE
    try:
        tid = int(arg)

        user_state[uid] = {
            "action": "confirm_delete",
            "id": tid
        }

        await update.message.reply_text(
            f"Yakin hapus ID {tid}? ketik 'ya' atau 'batal'"
        )

    except:
        await update.message.reply_text("ID tidak valid")

# ======================
# EDIT
# ======================
async def edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        tid = int(context.args[0])
    except:
        await update.message.reply_text("ID tidak valid")
        return

    updates = {}

    for arg in context.args[1:]:
        if "=" in arg:
            k, v = arg.split("=")
            updates[k] = v

    update_transaction(
        tid,
        amount=int(updates["amount"]) if "amount" in updates else None,
        tipe=updates.get("type"),
        category=updates.get("category"),
        description=updates.get("description"),
    )

    await update.message.reply_text("✅ Updated")

# ======================
# MAIN
# ======================
def main():
    init_db()

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("list", list_data))
    app.add_handler(CommandHandler("summary", summary))
    app.add_handler(CommandHandler("insight", insight))
    app.add_handler(CommandHandler("delete", delete))
    app.add_handler(CommandHandler("edit", edit))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()