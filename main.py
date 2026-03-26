import os
from datetime import datetime, timedelta

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
    get_month_category_summary,
    get_transactions_by_year
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
# HELPER (INI YANG NGURANGIN DUPLIKASI)
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
# COMMAND /HELP
# ======================
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📌 MENU BOT KEUANGAN\n\n"

        "📥 INPUT DATA\n"
        "Ketik langsung:\n"
        "- beli makan 10k\n"
        "- gaji 2jt\n\n"

        "📊 RINGKASAN\n"
        "/summary → total keseluruhan\n"
        "/today → hari ini\n"
        "/month → bulan ini\n"
        "/year → ringkasan per bulan (1 tahun)\n\n"

        "🧾 HISTORY (BERDASARKAN WAKTU)\n"
        "/history → hari ini (detail transaksi)\n"
        "/history DD-MM-YYYY → detail per tanggal\n"
        "/history MM-YYYY → ringkasan bulanan + kategori\n"
        "/history YYYY → ringkasan per bulan (1 tahun)\n\n"

        "📈 ANALISIS (RANKING PENGELUARAN)\n"
        "/rank → hari ini\n"
        "/rank DD-MM-YYYY → ranking per tanggal\n"
        "/rank MM-YYYY → ranking per bulan\n"
        "/rank YYYY → ranking per tahun\n\n"

        "✏️ EDIT DATA\n"
        "/edit <id> <nominal>\n"
        "contoh: /edit 5 50000\n\n"

        "🗑️ HAPUS DATA\n"
        "/delete today | week | month | year\n"
        "/deleteid <id>\n\n"

        "⚠️ KONFIRMASI (WAJIB)\n"
        "/confirm → jalankan edit/delete\n"
        "/cancel → batalkan aksi\n\n"

        "💡 ALUR PENGGUNAAN (PENTING)\n"
        "1. /history → lihat data & ID\n"
        "2. /edit atau /deleteid\n"
        "3. /confirm\n\n"

        "📌 CATATAN\n"
        "- ID hanya bisa dilihat dari /history\n"
        "- Semua edit & delete harus dikonfirmasi\n"
    )

    await update.message.reply_text(text)

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
    income, expense = extract_income_expense(data)

    if update.message:
        await update.message.reply_text(
            f"Ringkasan Uang:\n"
            f"Pemasukan: {format_rupiah(income)}\n"
            f"Pengeluaran: {format_rupiah(expense)}\n"
            f"Saldo: {format_rupiah(income - expense)}"
        )

# ======================
# TODAY
# ======================
async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = get_today_summary()
    income, expense = extract_income_expense(data)

    if update.message:
        await update.message.reply_text(
            f"Hari ini:\n"
            f"Pemasukan: {format_rupiah(income)}\n"
            f"Pengeluaran: {format_rupiah(expense)}\n"
            f"Saldo: {format_rupiah(income - expense)}"
        )

# ======================
# MONTH
# ======================
async def month(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = get_month_summary()
    income, expense = extract_income_expense(data)

    if update.message:
        await update.message.reply_text(
            f"Bulan ini:\n"
            f"Pemasukan: {format_rupiah(income)}\n"
            f"Pengeluaran: {format_rupiah(expense)}\n"
            f"Saldo: {format_rupiah(income - expense)}"
        )

# ======================
# YEAR (FITUR BARU)
# ======================
async def year(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = get_year_summary()

    if not data:
        await update.message.reply_text("Belum ada data tahun ini.")
        return

    result = {}

    for month, tipe, amount in data:
        month = int(month)

        if month not in result:
            result[month] = {"income": 0, "expense": 0}

        result[month][tipe] = amount or 0

    nama_bulan = [
        "Jan", "Feb", "Mar", "Apr", "Mei", "Jun",
        "Jul", "Agu", "Sep", "Okt", "Nov", "Des"
    ]

    text = "Ringkasan Tahun Ini:\n\n"

    total_income = 0
    total_expense = 0

    for m in range(1, 13):
        income = result.get(m, {}).get("income", 0)
        expense = result.get(m, {}).get("expense", 0)

        if income == 0 and expense == 0:
            continue

        total_income += income
        total_expense += expense

        text += (
            f"{nama_bulan[m-1]}:\n"
            f"  + {format_rupiah(income)}\n"
            f"  - {format_rupiah(expense)}\n\n"
        )

    text += "--- TOTAL ---\n"
    text += f"+ {format_rupiah(total_income)}\n"
    text += f"- {format_rupiah(total_expense)}\n"
    text += f"= {format_rupiah(total_income - total_expense)}"

    await update.message.reply_text(text)

# ======================
# RANK
# ======================
async def rank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args

    # ======================
    # DEFAULT → HARI INI
    # ======================
    if not args:
        data = get_today_category_summary()
        title = "Ranking Hari Ini"

    else:
        arg = args[0]

        # ======================
        # DD-MM-YYYY
        # ======================
        if len(arg.split("-")) == 3:
            try:
                day, month, year = map(int, arg.split("-"))
                date = f"{year:04d}-{month:02d}-{day:02d}"

                data = get_rank_by_date(date)
                title = f"Ranking {arg}"
            except:
                await update.message.reply_text("Format tanggal salah.")
                return

        # ======================
        # MM-YYYY
        # ======================
        elif len(arg.split("-")) == 2:
            try:
                month, year = map(int, arg.split("-"))

                data = get_rank_by_month(month, year)
                title = f"Ranking {arg}"
            except:
                await update.message.reply_text("Format bulan salah.")
                return

        # ======================
        # YYYY
        # ======================
        elif len(arg) == 4 and arg.isdigit():
            try:
                year = int(arg)

                data = get_rank_by_year(year)
                title = f"Ranking Tahun {year}"
            except:
                await update.message.reply_text("Format tahun salah.")
                return

        else:
            await update.message.reply_text("Format tidak dikenali.")
            return

    # ======================
    # OUTPUT
    # ======================
    if not data:
        await update.message.reply_text("Tidak ada data.")
        return

    total = sum(row[1] for row in data if row[1])

    text = f"{title}\n\n"

    for i, row in enumerate(data, start=1):
        kategori = row[0]
        amount = row[1] or 0
        persen = (amount / total) * 100 if total else 0

        text += f"{i}. {kategori}\n"
        text += f"   {format_rupiah(amount)} ({persen:.1f}%)\n"

    text += f"\nTotal Pengeluaran: {format_rupiah(total)}"

    await update.message.reply_text(text)

    # Bulan
    month_data = get_month_summary()
    income, expense = extract_income_expense(month_data)

    text += "\n\n--- Bulan Ini ---\n"
    text += f"Pemasukan: {format_rupiah(income)}\n"
    text += f"Pengeluaran: {format_rupiah(expense)}\n"
    text += f"Saldo: {format_rupiah(income - expense)}"

    # Total
    total_data = get_total_summary()
    total_income, total_expense = extract_income_expense(total_data)

    text += "\n\n--- Total ---\n"
    text += f"Saldo: {format_rupiah(total_income - total_expense)}"

    if update.message:
        await update.message.reply_text(text)

# ======================
# HANDLE /HISTORY
# ======================
async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args

    # ======================
    # HARI INI
    # ======================
    if not args:
        data = get_today_transactions()
        title = "History Hari Ini"

    else:
        arg = args[0]
        parts = arg.split("-")

        # ======================
        # DD-MM-YYYY
        # ======================
        if len(parts) == 3:
            try:
                day, month, year = map(int, parts)
                date = f"{year:04d}-{month:02d}-{day:02d}"

                data = get_transactions_by_date(date)
                title = f"History {arg}"

            except:
                await update.message.reply_text("Format tanggal salah (DD-MM-YYYY)")
                return

        # ======================
        # MM-YYYY
        # ======================
        elif len(parts) == 2:
            try:
                month, year = map(int, parts)

                data = get_month_summary_by_year(month, year)

                if not data:
                    await update.message.reply_text("Tidak ada data.")
                    return

                income, expense = 0, 0

                for row in data:
                    if row[0] == "income":
                        income = row[1] or 0
                    elif row[0] == "expense":
                        expense = row[1] or 0

                nama_bulan = [
                    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
                    "Juli", "Agustus", "September", "Oktober", "November", "Desember"
                ]

                text = f"History {nama_bulan[month-1]} {year}\n\n"
                text += f"Pemasukan: {format_rupiah(income)}\n"
                text += f"Pengeluaran: {format_rupiah(expense)}\n"
                text += f"Saldo: {format_rupiah(income - expense)}\n"

                await update.message.reply_text(text)

            except:
                await update.message.reply_text("Format bulan salah. Gunakan MM-YYYY")
                return

        # ======================
        # FORMAT TIDAK DIKENALI
        # ======================
        else:
            await update.message.reply_text("Format tidak dikenali.")
            return

# ======================
# OPTIONAL: KATEGORI
# ======================
        cat_data = get_month_category_summary(month, year)

        if cat_data:
            text += "\nTop Pengeluaran:\n"

            total_exp = sum(row[1] for row in cat_data if row[1])

            for i, row in enumerate(cat_data[:5], start=1):
                kategori = row[0]
                total = row[1] or 0
                persen = (total / total_exp) * 100 if total_exp else 0

                text += f"{i}. {kategori} - {format_rupiah(total)} ({persen:.1f}%)\n"

        await update.message.reply_text(text)

    except:
        await update.message.reply_text("Format bulan salah. Gunakan MM-YYYY")
        return

        # ======================
        # YYYY
        # ======================
        elif len(arg) == 4 and arg.isdigit():
    try:
        year = int(arg)

        data = get_transactions_by_year(year)

        if not data:
            await update.message.reply_text("Tidak ada data.")
            return

        # struktur hasil
        result = {}

        for month, tipe, amount in data:
            month = int(month)

            if month not in result:
                result[month] = {"income": 0, "expense": 0}

            result[month][tipe] = amount or 0

        nama_bulan = [
            "Jan", "Feb", "Mar", "Apr", "Mei", "Jun",
            "Jul", "Agu", "Sep", "Okt", "Nov", "Des"
        ]

        text = f"History Tahun {year}\n\n"

        total_income = 0
        total_expense = 0

        for m in range(1, 13):
            income = result.get(m, {}).get("income", 0)
            expense = result.get(m, {}).get("expense", 0)

            if income == 0 and expense == 0:
                continue

            total_income += income
            total_expense += expense

            text += (
                f"{nama_bulan[m-1]}:\n"
                f"  + {format_rupiah(income)}\n"
                f"  - {format_rupiah(expense)}\n"
                f"  = {format_rupiah(income - expense)}\n\n"
            )

        text += "--- TOTAL ---\n"
        text += f"+ {format_rupiah(total_income)}\n"
        text += f"- {format_rupiah(total_expense)}\n"
        text += f"= {format_rupiah(total_income - total_expense)}"

        await update.message.reply_text(text)

    except:
        await update.message.reply_text("Format tahun salah. Gunakan YYYY")
        return

    # ======================
    # OUTPUT
    # ======================
    if not data:
        await update.message.reply_text("Tidak ada data.")
        return

    text = f"{title}:\n\n"

    for i, row in enumerate(data, start=1):
        trx_id, amount, tipe, kategori, desc, created_at = row

        created_at = adjust_timezone(created_at)
        tipe_text = "+" if tipe == "income" else "-"

        text += (
            f"{i}. (ID: {trx_id})\n"
            f"{tipe_text} {format_rupiah(amount)} | {kategori}\n"
            f"{desc}\n"
            f"{format_tanggal(created_at)}\n\n"
        )

    await update.message.reply_text(text)

# ======================
# HANDLE /EDIT
# ======================
async def edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text(
            "Gunakan:\n/edit <id> <nominal_baru>"
        )
        return

    try:
        trx_id = int(context.args[0])
        new_amount = int(context.args[1])
    except:
        await update.message.reply_text("Format salah.")
        return

    set_pending_action(context, "edit", {
        "id": trx_id,
        "amount": new_amount
    })

    await update.message.reply_text(
        f"⚠️ Yakin ubah transaksi {trx_id} jadi {format_rupiah(new_amount)}?\n"
        f"Ketik: /confirm edit {trx_id} {new_amount}\n"
        f"Atau: /cancel"
    )


# ======================
# HANDLE /DELETE
# ======================
async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Gunakan:\n/delete today | week | month | year"
        )
        return

    mode = context.args[0].lower()

    if mode not in ["today", "week", "month", "year"]:
        await update.message.reply_text("Mode tidak valid.")
        return

    set_pending_action(context, "delete", {"mode": mode})

    await update.message.reply_text(
        f"⚠️ Yakin hapus data {mode}?\n"
        f"Ketik: /confirm delete {mode}\n"
        f"Atau: /cancel"
    )

# HANDLE /DELETE ID
# ======================
async def delete_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Gunakan:\n/deleteid <id>\nContoh: /deleteid 5"
        )
        return

    try:
        trx_id = int(context.args[0])
    except:
        await update.message.reply_text("ID harus angka.")
        return

    # simpan ke pending action
    set_pending_action(context, "delete_id", {"id": trx_id})

    await update.message.reply_text(
        f"⚠️ Yakin hapus transaksi ID {trx_id}?\n"
        f"Ketik /confirm untuk lanjut atau /cancel"
    )

# ======================
# KONFIRMASI YA/TIDAK
# ======================
def set_pending_action(context, action, data):
    context.user_data["pending"] = {
        "action": action,
        "data": data
    }

def clear_pending_action(context):
    context.user_data.pop("pending", None)

# ======================
# HANDLE /KONFIRMASI
# ======================
async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pending = context.user_data.get("pending")

    if not pending:
        await update.message.reply_text("Tidak ada aksi yang perlu dikonfirmasi.")
        return

    action = pending["action"]
    data = pending["data"]

    if action == "delete":
        mode = data["mode"]
        deleted = delete_range(mode)

        await update.message.reply_text(
            f"{deleted} data berhasil dihapus ({mode})."
        )

    elif action == "edit":
        trx_id = data["id"]
        new_amount = data["amount"]

        updated = update_transaction_amount(trx_id, new_amount)

        if updated == 0:
            await update.message.reply_text("ID tidak ditemukan.")
        else:
            await update.message.reply_text(
                f"Transaksi {trx_id} berhasil diupdate menjadi {format_rupiah(new_amount)}"
            )

    elif action == "delete_id":   # ← HARUS sejajar dengan elif di atas
        trx_id = data["id"]

        deleted = delete_by_id(trx_id)

        if deleted == 0:
            await update.message.reply_text("ID tidak ditemukan.")
        else:
            await update.message.reply_text(
                f"Transaksi {trx_id} berhasil dihapus."
            )

    clear_pending_action(context)

# ======================
# HANDLE /CANCEL
# ======================
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "pending" not in context.user_data:
        await update.message.reply_text("Tidak ada aksi untuk dibatalkan.")
        return

    clear_pending_action(context)

    await update.message.reply_text("Aksi dibatalkan.")

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
    app.add_handler(CommandHandler("year", year))
    app.add_handler(CommandHandler("rank", rank))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CommandHandler("delete", delete))
    app.add_handler(CommandHandler("history", history))
    app.add_handler(CommandHandler("edit", edit))
    app.add_handler(CommandHandler("confirm", confirm))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("menu", help_command))
    app.add_handler(CommandHandler("deleteid", delete_id))

    app.add_error_handler(error_handler)

    print("Bot berjalan di Railway...")
    app.run_polling()

if __name__ == "__main__":
    main()