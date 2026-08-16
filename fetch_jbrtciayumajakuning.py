import os
import re
import json
import time
import html
import requests
import xml.etree.ElementTree as ET


# =========================================================
# JBRTCIAYUMAJAKUNING
# AUTO POST RUMAH & TANAH
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

CHAT_ID = (
    os.getenv("CHAT_ID")
    or os.getenv("TELEGRAM_CHAT_ID")
    or ""
).strip()

# RSS APP
RSS_URL = "https://rss.app/r/feed/Mlc5shYuFREkcpMt"

SENT_FILE = "sent.json"

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"


# =========================================================
# VALIDASI
# =========================================================

def validate_config():

    if not BOT_TOKEN:
        print("❌ BOT_TOKEN tidak ditemukan.")
        print("Tambahkan BOT_TOKEN di GitHub Secrets.")
        raise SystemExit(1)

    if not CHAT_ID:
        print("❌ CHAT_ID tidak ditemukan.")
        print("Tambahkan CHAT_ID di GitHub Secrets.")
        raise SystemExit(1)


# =========================================================
# DATABASE ANTI DUPLIKAT
# =========================================================

def load_sent():

    if not os.path.exists(SENT_FILE):
        return []

    try:
        with open(SENT_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        if isinstance(data, list):
            return data

    except Exception as error:
        print(f"⚠️ Gagal membaca sent.json: {error}")

    return []


def save_sent(sent):

    with open(SENT_FILE, "w", encoding="utf-8") as file:
        json.dump(
            sent,
            file,
            ensure_ascii=False,
            indent=2
        )


# =========================================================
# BERSIHKAN TEKS
# =========================================================

def clean_text(text):

    if not text:
        return ""

    text = re.sub(r"<[^>]+>", " ", text)

    text = html.unescape(text)

    text = " ".join(text.split())

    return text.strip()


# =========================================================
# FORMAT POSTING
# =========================================================

def create_message(title, description, link):

    title = clean_text(title)
    description = clean_text(description)

    if not title:
        title = "Properti Baru"

    if not description:
        description = "Informasi jual beli rumah dan tanah."

    if len(description) > 2800:
        description = description[:2800] + "..."

    message = (
        "🏠 <b>JBRTCIAYUMAJAKUNING</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        f"📌 <b>{html.escape(title)}</b>\n\n"

        "📝 <b>Informasi Properti</b>\n"
        f"{html.escape(description)}\n\n"

        "━━━━━━━━━━━━━━━━━━\n"
        "🔗 <b>Detail / Sumber:</b>\n"
        f"{html.escape(link)}\n\n"

        "🏡 <b>Jual Beli Rumah & Tanah</b>\n"
        "📍 Cirebon • Majalengka • Kuningan\n"
        "📢 JBRTCIAYUMAJAKUNING"
    )

    return message


# =========================================================
# KIRIM TELEGRAM
# =========================================================

def send_telegram(message):

    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }

    try:

        response = requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json=payload,
            timeout=30
        )

        data = response.json()

    except Exception as error:

        print(f"❌ Gagal mengirim Telegram: {error}")

        return False

    if response.status_code == 200 and data.get("ok"):

        print("✅ Posting berhasil.")

        return True

    print("❌ Telegram menolak posting.")

    print(response.text)

    return False


# =========================================================
# AMBIL RSS
# =========================================================

def get_rss():

    print("📡 Mengambil RSS...")
    print(RSS_URL)

    try:

        response = requests.get(
            RSS_URL,
            timeout=30,
            headers={
                "User-Agent":
                "Mozilla/5.0 JBRTCIAYUMAJAKUNING/1.0"
            }
        )

    except requests.RequestException as error:

        print(f"❌ Gagal mengambil RSS: {error}")

        return None

    print(f"HTTP Status: {response.status_code}")

    if response.status_code != 200:

        print("❌ RSS tidak dapat diakses.")

        print(response.text[:500])

        return None

    try:

        root = ET.fromstring(response.content)

        return root

    except ET.ParseError as error:

        print(f"❌ RSS bukan XML yang valid: {error}")

        return None


# =========================================================
# PROSES RSS
# =========================================================

def process_feed():

    root = get_rss()

    if root is None:
        return 0

    sent = load_sent()

    items = root.findall(".//item")

    print(f"📦 Ditemukan {len(items)} posting dari RSS.")

    if not items:

        print("⚠️ Tidak ada posting.")

        return 0

    berhasil = 0

    # Maksimal 3 posting setiap workflow
    for item in items[:3]:

        title = item.findtext("title", "").strip()

        link = item.findtext("link", "").strip()

        description = item.findtext(
            "description",
            ""
        ).strip()

        if not link:

            print("⏭️ Posting dilewati karena tidak mempunyai link.")

            continue

        # Anti duplikat
        if link in sent:

            print(
                f"⏭️ Sudah pernah diposting: {title[:70]}"
            )

            continue

        message = create_message(
            title,
            description,
            link
        )

        print(
            f"📨 Mengirim: {title[:70]}"
        )

        if send_telegram(message):

            sent.append(link)

            save_sent(sent)

            berhasil += 1

            time.sleep(3)

    return berhasil


# =========================================================
# MAIN
# =========================================================

def main():

    print("=" * 60)

    print("🏠 JBRTCIAYUMAJAKUNING")

    print("🏡 Auto Post Jual Beli Rumah & Tanah")

    print("=" * 60)

    validate_config()

    total = process_feed()

    print("=" * 60)

    print(
        f"✅ SELESAI — {total} posting baru dikirim."
    )

    print("=" * 60)


if __name__ == "__main__":
    main()
