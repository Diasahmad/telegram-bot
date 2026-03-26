import re

def parse_amount(text):
    text = text.lower().replace(",", ".")
    match = re.search(r'(\d+(\.\d+)?)(\s?)(k|rb|jt)?', text)

    if not match:
        return None

    number = float(match.group(1))
    suffix = match.group(4)

    if suffix in ['k', 'rb']:
        number *= 1_000
    elif suffix == 'jt':
        number *= 1_000_000

    return int(number)


def detect_type(text):
    text = text.lower()

    if any(word in text for word in ["beli", "bayar", "jajan", "makan", "minum", "jajan", "admin", "investasi"]):
        return "expense"
    elif any(word in text for word in ["gaji", "masuk", "dapat", "uang saku", "menabung", "uang saku"]):
        return "income"

    return "unknown"

# Keterangan Pengeluaran dan Pemasukkan 
def categorize(text):
    text = text.lower()

    if any(word in text for word in   ["makan"]):
        return "makan"
    elif any(word in text for word in ["minum"]):
        return "minum"
    elif any(word in text for word in ["makan"]):
        return "makan"
    elif any(word in text for word in ["jajan"]):
        return "jajan"
    elif any(word in text for word in ["bensin", "servis"]):
        return "transport"
    elif any(word in text for word in ["listrik", "air", "wifi"]):
        return "tagihan"
    elif any(word in text for word in ["game", "nonton", "hiburan"]):
        return "hiburan"
    elif any(word in text for word in ["infaq", "sedekah"]):
        return "pahala"
    elif any(word in text for word in ["shopee"]):
        return "shopee"
    elif any(word in text for word in ["uang saku", "menabung"]):
        return "tabungan"
    elif any(word in text for word in ["admin"]):
        return "admin"
    elif any(word in text for word in ["investasi"]):
        return "investasi"

    return "lainnya"

def extract_description(text):
    text = re.sub(r'\d+(\.\d+)?\s?(k|rb|jt)?', '', text)
    return text.strip()


def parse_transaction(text):
    return {
        "amount": parse_amount(text),
        "type": detect_type(text),
        "description": extract_description(text),
        "category": categorize(text)
    }

