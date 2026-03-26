import os
from datetime import datetime, timedelta

from parser import parse_transaction
from database import (
    save_transaction,
    get_summary,
    get_transactions_by_period,
    get_category_summary,
    get_yearly_summary,
    delete_transaction,
    update_transaction,
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

def get_month_name(m):
    return [
        "Januari","Februari","Maret","April","Mei","Juni",
        "Juli","Agustus","September","Oktober","November","Desember"
    ][m-1]

# ======================
# START / HELP
# ======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 BOT KEUANGAN\n\n"
        "Contoh input:\n"
        "- beli makan 20k\n"
        "- gaji 3jt\n\n"
        "Command:\n"
        "/list [today|month|year]\n"
        "/summary\n"
        "/delete <id>\n"
        "/delete 1-5\n"
    )

# ======================
# HANDLE MESSAGE
# ======================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text.lower()

    # ===== CONFIRM SAVE =====
    if uid in user_state and user_state[uid]["action"] == "confirm_save":
        if text in ["ya", "y"]:
            data = user_state[uid]["data"]

            tid, _ = save_transaction(
                data["amount"],
                data["type"],
                data["category"],
                data["description"]
            )

            await update.message.reply_text(
                f"✅ Disimpan (ID: {tid})"
            )
        else:
            await update.message.reply_text("❌ Dibatalkan")

        del user_state[uid]
        return

    # ===== CONFIRM DELETE =====
    if uid in user_state:
        state = user_state[uid]

        if state["action"] == "confirm_delete":
            if text == "ya":
                delete_transaction(state["id"])
                await update.message.reply_text("🗑️ Dihapus")
            del user_state[uid]
            return

        if state["action"] == "confirm_delete_range":
            if text == "ya":
                for tid in state["ids"]:
                    delete_transaction(tid)
                await update.message.reply_text("🗑️ Range dihapus")
            del user_state[uid]
            return

    # ===== PARSE =====
    data = parse_transaction(text)

    if not data["amount"]:
        await update.message.reply_text("Jumlah tidak terbaca")
        return

    if data["type"] == "unknown":
        await update.message.reply_text("Tipe tidak jelas")
        return

    user_state[uid] = {"action": "confirm_save", "data": data}

    await update.message.reply_text(
        f"Konfirmasi:\n{data}\n\nketik 'ya' atau 'batal'"
    )

# ======================
# LIST
# ======================
async def list_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    period = context.args[0] if context.args else "today"

    # ===== YEAR =====
    if period == "year":
        data = get_yearly_summary()

        if not data:
            await update.message.reply_text("Tidak ada data.")
            return

        text = "📊 DATA TAHUN INI\n\n"
        bulan_map = {}

        for month, tipe, amount in data:
            m = month.month
            if m not in bulan_map:
                bulan_map[m] = {"income":0,"expense":0}

            bulan_map[m][tipe] = amount

        for m in sorted(bulan_map):
            inc = bulan_map[m]["income"]
            exp = bulan_map[m]["expense"]

            text += (
                f"{get_month_name(m)}\n"
                f"Pemasukan: Rp {format_rupiah(inc)}\n"
                f"Pengeluaran: Rp {format_rupiah(exp)}\n"
                f"Saldo: Rp {format_rupiah(inc-exp)}\n\n"
            )

        await update.message.reply_text(text)
        return

    data = get_transactions_by_period(period)

    if not data:
        await update.message.reply_text("Tidak ada data.")
        return

    user_last_list[uid] = data

    # ===== HEADER =====
    now = datetime.now()
    header = f"{now.day} {get_month_name(now.month)} {now.year}"

    text = f"📋 Data ({period})\n{header}\n\n"

    # ===== MONTH (AGGREGATE) =====
    if period == "month":
        kategori = {}

        for row in data:
            _, amount, _, cat, _, _ = row
            kategori[cat] = kategori.get(cat, 0) + amount

        for i, (k, v) in enumerate(kategori.items(), start=1):
            text += f"{i}. {k.upper()} - Rp {format_rupiah(v)}\n"

        await update.message.reply_text(text)
        return

    # ===== TODAY =====
    for i, row in enumerate(data, start=1):
        id_, amount, tipe, cat, desc, created = row
        created = adjust_timezone(created)

        text += (
            f"{i}. [{id_}] {cat.upper()}\n"
            f"   Rp {format_rupiah(amount)}\n"
            f"   {desc}\n"
            f"   🕒 {created.strftime('%H:%M')}\n\n"
        )

    await update.message.reply_text(text)

# ======================
# DELETE
# ======================
async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    if not context.args:
        await update.message.reply_text("Gunakan /delete <id> atau range")
        return

    arg = context.args[0]

    # RANGE
    if "-" in arg:
        if uid not in user_last_list:
            await update.message.reply_text("Gunakan /list dulu")
            return

        start, end = map(int, arg.split("-"))
        data = user_last_list[uid]

        if start < 1 or end > len(data):
            await update.message.reply_text("Range tidak valid")
            return

        ids = [row[0] for row in data[start-1:end]]

        user_state[uid] = {
            "action": "confirm_delete_range",
            "ids": ids
        }

        await update.message.reply_text("Yakin hapus range? ya/batal")
        return

    # SINGLE
    tid = int(arg)

    user_state[uid] = {
        "action": "confirm_delete",
        "id": tid
    }

    await update.message.reply_text("Yakin hapus? ya/batal")

# ======================
# MAIN
# ======================
def main():
    init_db()

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("list", list_data))
    app.add_handler(CommandHandler("delete", delete))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()