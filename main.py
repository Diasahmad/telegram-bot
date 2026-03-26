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
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = os.getenv("BOT_TOKEN")

user_state = {}
user_last_list = {}

# ======================
# UTIL
# ======================
def format_rupiah(x):
    return f"{x:,}".replace(",", ".")

def adjust_timezone(dt):
    return dt + timedelta(hours=7)

def format_header_date(period):
    now = datetime.now()

    bulan = [
        "Januari","Februari","Maret","April","Mei","Juni",
        "Juli","Agustus","September","Oktober","November","Desember"
    ]

    if period == "today":
        return f"{now.day} {bulan[now.month-1]} {now.year}"

    if period == "month":
        return f"{bulan[now.month-1]} {now.year}"

    return ""

# ======================
# LIST
# ======================
async def list_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    period = context.args[0] if context.args else "today"

    # ===== YEAR =====
    if period == "year":
        data = get_yearly_summary()

        if not data:
            await update.message.reply_text("Tidak ada data tahun ini.")
            return

        text = "📊 DATA TAHUN INI\n\n"

        bulan_map = {}

        for month, tipe, amount in data:
            m = month.month
            if m not in bulan_map:
                bulan_map[m] = {"income":0,"expense":0}

            bulan_map[m][tipe] = amount

        nama_bulan = [
            "Januari","Februari","Maret","April","Mei","Juni",
            "Juli","Agustus","September","Oktober","November","Desember"
        ]

        for m in sorted(bulan_map.keys()):
            inc = bulan_map[m]["income"]
            exp = bulan_map[m]["expense"]

            text += (
                f"{nama_bulan[m-1]}\n"
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

    user_last_list[user_id] = data

    header = format_header_date(period)
    text = f"📋 Data ({period})\n{header}\n\n"

    # ===== MONTH (AGGREGATE) =====
    if period == "month":
        kategori_map = {}

        for row in data:
            _, amount, _, category, _, _ = row
            kategori_map[category] = kategori_map.get(category, 0) + amount

        for i, (cat, total) in enumerate(kategori_map.items(), start=1):
            text += f"{i}. {cat.upper()} - Rp {format_rupiah(total)}\n"

        await update.message.reply_text(text)
        return

    # ===== TODAY =====
    for i, row in enumerate(data, start=1):
        id_, amount, tipe, category, desc, created = row
        created = adjust_timezone(created)

        jam = created.strftime("%H:%M")

        text += (
            f"{i}. [{id_}] {category.upper()}\n"
            f"   Rp {format_rupiah(amount)}\n"
            f"   {desc}\n"
            f"   🕒 {jam}\n\n"
        )

    await update.message.reply_text(text)

# ======================
# DELETE (SUPPORT PERIOD)
# ======================
async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    if not context.args:
        await update.message.reply_text("Gunakan /delete <id> atau range")
        return

    arg = context.args[0]

    if "-" in arg:
        if uid not in user_last_list:
            await update.message.reply_text("Gunakan /list dulu")
            return

        start, end = map(int, arg.split("-"))
        data = user_last_list[uid]

        selected = data[start-1:end]
        ids = [row[0] for row in selected]

        user_state[uid] = {"action":"confirm_delete_range","ids":ids}

        preview = "\n".join([f"ID {x}" for x in ids])

        await update.message.reply_text(
            f"Hapus:\n{preview}\n\nKetik 'ya' atau 'batal'"
        )
        return

    tid = int(arg)
    user_state[uid] = {"action":"confirm_delete","id":tid}

    await update.message.reply_text("Yakin? ketik 'ya' atau 'batal'")

# ======================
# HANDLE MESSAGE
# ======================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text.lower()

    # CONFIRM DELETE
    if uid in user_state:
        state = user_state[uid]

        if state["action"] == "confirm_delete":
            if text == "ya":
                delete_transaction(state["id"])
                await update.message.reply_text("Dihapus")
            del user_state[uid]
            return

        if state["action"] == "confirm_delete_range":
            if text == "ya":
                for i in state["ids"]:
                    delete_transaction(i)
                await update.message.reply_text("Range dihapus")
            del user_state[uid]
            return

    # PARSE
    data = parse_transaction(text)

    if not data["amount"]:
        await update.message.reply_text("Jumlah tidak terbaca")
        return

    user_state[uid] = {"action":"confirm_save","data":data}

    await update.message.reply_text(f"Konfirmasi:\n{data}\nketik ya/batal")

# ======================
# MAIN
# ======================
def main():
    init_db()

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("list", list_data))
    app.add_handler(CommandHandler("delete", delete))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()

if __name__ == "__main__":
    main()