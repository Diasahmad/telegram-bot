import re

# ======================
# AMOUNT (FIX REAL WORLD)
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
# TYPE
# ======================
def detect_type(text):
    text = text.lower()

    if any(x in text for x in ["beli","bayar","jajan","makan","minum","shopee","sedekah"]):
        return "expense"

    if any(x in text for x in ["gaji","bonus","dapat","transfer masuk"]):
        return "income"

    return "unknown"


# ======================
# CATEGORY (REALISTIC)
# ======================
def categorize(text):
    text = text.lower()

    mapping = {
        "makan": ["makan","ayam","nasi","mie"],
        "minum": ["kopi","teh","minum"],
        "transport": ["bensin","gojek","grab"],
        "tagihan": ["listrik","air","wifi"],
        "hiburan": ["game","netflix","nonton"],
        "belanja": ["shopee","tokopedia"],
        "infaq": ["sedekah","infaq"],
    }

    for cat, keys in mapping.items():
        if any(k in text for k in keys):
            return cat

    return "lainnya"


# ======================
# DESCRIPTION (SAFE)
# ======================
def extract_description(text):
    text = text.lower()
    text = re.sub(r'\b\d+\s*(k|jt)?\b', '', text)
    return text.strip()


# ======================
# MAIN
# ======================
def parse_transaction(text):
    return {
        "amount": parse_amount(text),
        "type": detect_type(text),
        "category": categorize(text),
        "description": extract_description(text)
    }