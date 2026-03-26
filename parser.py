import re

# ======================
# ANGKA → NLP (KATA KE ANGKA)
# ======================
def words_to_number(text):
    text = text.lower()

    angka = {
        "nol": 0,
        "satu": 1, "dua": 2, "tiga": 3, "empat": 4,
        "lima": 5, "enam": 6, "tujuh": 7, "delapan": 8, "sembilan": 9,
        "sepuluh": 10, "sebelas": 11
    }

    puluhan = {
        "sepuluh": 10,
        "dua puluh": 20,
        "tiga puluh": 30,
        "empat puluh": 40,
        "lima puluh": 50,
        "enam puluh": 60,
        "tujuh puluh": 70,
        "delapan puluh": 80,
        "sembilan puluh": 90
    }

    total = 0

    # puluhan dulu
    for key, val in puluhan.items():
        if key in text:
            total += val
            text = text.replace(key, "")

    # satuan
    for word, val in angka.items():
        if word in text:
            total += val

    # ribu / juta
    if "ribu" in text:
        total *= 1000
    elif "juta" in text:
        total *= 1_000_000

    return total if total > 0 else None


# ======================
# ANGKA BIASA (NUMERIC)
# ======================
def parse_numeric_amount(text):
    text = text.lower()

    text = text.replace("ribu", "k")
    text = text.replace("rb", "k")
    text = text.replace("juta", "jt")

    # hapus titik (format indo)
    text = text.replace(".", "")

    match = re.search(r'(\d+)\s*(k|jt)?', text)

    if not match:
        return None

    amount = int(match.group(1))
    suffix = match.group(2)

    if suffix == "k":
        amount *= 1000
    elif suffix == "jt":
        amount *= 1_000_000

    return amount


# ======================
# FINAL AMOUNT PARSER
# ======================
def parse_amount(text):
    # coba numeric dulu
    amount = parse_numeric_amount(text)

    if amount:
        return amount

    # fallback ke NLP
    return words_to_number(text)


# ======================
# DETECT TYPE
# ======================
def detect_type(text):
    text = text.lower()

    if any(word in text for word in [
        "beli", "bayar", "jajan", "makan", "minum", "admin", "investasi", "shopee"
    ]):
        return "expense"

    elif any(word in text for word in [
        "gaji", "masuk", "dapat", "uang saku", "menabung"
    ]):
        return "income"

    return "unknown"


# ======================
# CATEGORY
# ======================
def categorize(text):
    text = text.lower()

    if "makan" in text:
        return "makan"
    elif "minum" in text:
        return "minum"
    elif "jajan" in text:
        return "jajan"
    elif any(word in text for word in ["bensin", "servis"]):
        return "transport"
    elif any(word in text for word in ["listrik", "air", "wifi"]):
        return "tagihan"
    elif any(word in text for word in ["game", "nonton", "hiburan"]):
        return "hiburan"
    elif any(word in text for word in ["infaq", "sedekah"]):
        return "pahala"
    elif "shopee" in text:
        return "shopee"
    elif any(word in text for word in ["uang saku", "menabung"]):
        return "tabungan"
    elif "admin" in text:
        return "admin"
    elif "investasi" in text:
        return "investasi"

    return "lainnya"


# ======================
# DESCRIPTION CLEANER
# ======================
def extract_description(text):
    text = text.lower()

    text = text.replace("ribu", "k")
    text = text.replace("rb", "k")
    text = text.replace("juta", "jt")
    text = text.replace(".", "")

    text = re.sub(r'\d+\s*(k|jt)?', '', text)

    return text.strip()


# ======================
# MAIN PARSER
# ======================
def parse_transaction(text):
    return {
        "amount": parse_amount(text),
        "type": detect_type(text),
        "description": extract_description(text),
        "category": categorize(text)
    }