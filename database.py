import re

# ======================
# AMOUNT PARSER (STABIL)
# ======================
def parse_amount(text):
    text = text.lower()

    text = text.replace(".", "")
    text = text.replace("ribu", "k").replace("rb", "k")
    text = text.replace("juta", "jt")

    matches = re.findall(r'(\d+)\s*(k|jt)?', text)

    if not matches:
        return None

    values = []

    for num, suffix in matches:
        val = int(num)

        if suffix == "k":
            val *= 1000
        elif suffix == "jt":
            val *= 1_000_000

        values.append(val)

    return max(values)


# ======================
# TYPE DETECTION
# ======================
def detect_type(text):
    text = text.lower()

    expense_keywords = [
        "beli", "bayar", "jajan", "makan", "minum",
        "shopee", "sedekah", "infaq", "bensin"
    ]

    income_keywords = [
        "gaji", "bonus", "dapat", "transfer masuk"
    ]

    if any(word in text for word in expense_keywords):
        return "expense"

    if any(word in text for word in income_keywords):
        return "income"

    return "unknown"


# ======================
# CATEGORY (LEBIH REAL)
# ======================
def categorize(text):
    text = text.lower()

    mapping = {
        "makan": ["makan", "ayam", "nasi", "mie"],
        "minum": ["kopi", "teh", "minum"],
        "transport": ["bensin", "gojek", "grab"],
        "tagihan": ["listrik", "air", "wifi"],
        "hiburan": ["game", "netflix", "nonton"],
        "belanja": ["shopee", "tokopedia"],
        "infaq": ["sedekah", "infaq"],
        "gaji": ["gaji", "bonus"]
    }

    for cat, keys in mapping.items():
        if any(k in text for k in keys):
            return cat

    return "lainnya"


# ======================
# DESCRIPTION (BERSIH)
# ======================
def extract_description(text):
    text = text.lower()

    text = re.sub(r'\b\d+\s*(k|jt)?\b', '', text)
    text = text.replace(".", "").strip()

    return text


# ======================
# MAIN PARSER
# ======================
def parse_transaction(text):
    return {
        "amount": parse_amount(text),
        "type": detect_type(text),
        "category": categorize(text),
        "description": extract_description(text)
    }