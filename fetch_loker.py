import os
import re
import sys
import json
import time
import html
import requests
import xml.etree.ElementTree as ET


# =========================================================
# CONFIG
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

CHAT_ID = (
    os.getenv("CHAT_ID")
    or os.getenv("TELEGRAM_CHAT_ID")
    or ""
).strip()

DEFAULT_RSS_FEEDS = [
    "https://rss.app/feeds/MZMZkLtTiHKbr2ck.xml",
    "https://rss.app/feeds/7oEScJlZFeoYE3oo.xml",
]

DEFAULT_FALLBACK_RSS_FEEDS = [
    (
        "https://news.google.com/rss/search?"
        "q=loker%20Cirebon%20OR%20Kuningan%20"
        "site%3Aglints.com%20OR%20site%3Ajobstreet.co.id%20OR%20site%3Akarir.com"
        "&hl=id&gl=ID&ceid=ID:id"
    ),
    (
        "https://news.google.com/rss/search?"
        "q=lowongan%20kerja%20Cirebon%20OR%20Kuningan%20"
        "site%3Aglints.com%20OR%20site%3Ajobstreet.co.id"
        "&hl=id&gl=ID&ceid=ID:id"
    ),
]


def env_list(name, default):
    raw_value = os.getenv(name, "").strip()

    if not raw_value:
        return default[:]

    items = [
        item.strip()
        for item in re.split(r"[\n,]+", raw_value)
        if item.strip()
    ]

    return items or default[:]


RSS_FEEDS = env_list("RSS_FEEDS", DEFAULT_RSS_FEEDS)
FALLBACK_RSS_FEEDS = env_list("FALLBACK_RSS_FEEDS", DEFAULT_FALLBACK_RSS_FEEDS)

IKLAN = "https://crypotential.com/kxseizepn?key=b27dbc018fb141e5773a6cc85f207c78"

SENT_FILE = "sent.json"

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"


# =========================================================
# VALIDASI
# =========================================================

def validate_config():
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN tidak ditemukan.")
        print("Tambahkan BOT_TOKEN di GitHub Secrets.")
        sys.exit(1)

    if not CHAT_ID:
        print("❌ CHAT_ID tidak ditemukan.")
        print("Tambahkan CHAT_ID di GitHub Secrets.")
        sys.exit(1)


# =========================================================
# DATABASE ANTI-DUPLIKAT
# =========================================================

def save_sent(sent):
    with open(SENT_FILE, "w", encoding="utf-8") as file:
        json.dump(
            sent,
            file,
            ensure_ascii=False,
            indent=2
        )


def load_sent():
    # Kalau sent.json belum ada, otomatis buat
    if not os.path.exists(SENT_FILE):
        print("ℹ️ sent.json belum ada. Membuat file baru...")
        save_sent([])
        return []

    try:
        with open(SENT_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        if isinstance(data, list):
            return data

        print("⚠️ Isi sent.json tidak valid. Database direset.")
        save_sent([])
        return []

    except (json.JSONDecodeError, OSError) as error:
        print(f"⚠️ Gagal membaca sent.json: {error}")
        print("⚠️ Database anti-duplikat direset.")
        save_sent([])
        return []


# =========================================================
# BERSIHKAN TEKS
# =========================================================

def strip_html(raw_text):
    if not raw_text:
        return ""

    # Hapus tag HTML dari RSS
    text = re.sub(r"<[^>]+>", " ", raw_text)

    # Decode HTML entity
    text = html.unescape(text)

    # Rapikan spasi
    return " ".join(text.split())


def clean_text(raw_text):
    text = strip_html(raw_text)

    # Escape supaya aman untuk Telegram HTML
    return html.escape(text)


def clean_job_title(raw_title):
    title = strip_html(raw_title)

    for suffix in (
        " - Glints",
        " | Glints TapLoker",
        " - Karir.com",
        " - Jobstreet",
        " - JobStreet",
    ):
        title = title.replace(suffix, "")

    return title.strip(" ,-")


def fallback_description(title, source):
    source_text = f" dari {source}" if source else ""

    return (
        f"Informasi lowongan ini ditemukan{source_text} untuk area "
        "Cirebon/Kuningan dan sekitarnya. "
        f"Posisi yang tersedia: {title}. "
        "Buka tombol Lihat Lowongan untuk membaca detail pekerjaan, "
        "kualifikasi, persyaratan, gaji, dan cara melamar langsung "
        "di halaman resmi lowongan."
    )


# =========================================================
# KIRIM TELEGRAM
# =========================================================

def send_telegram(title, description, link):
    # Sisakan ruang untuk judul/footer agar tidak melebihi limit Telegram
    if len(description) > 3000:
        description = description[:3000] + "..."

    pesan = (
        "📢 <b>INFO KerjaDimana</b>\n\n"
        f"🏢 <b>{title}</b>\n\n"
        "📝 <b>Deskripsi Pekerjaan</b>\n"
        f"{description}\n\n"
        "━━━━━━━━━━━━━━\n\n"
        "📄 <b>BUAT CV GENERATOR KANDIDAT</b>\n"
        "🎯 Buat CV profesional untuk meningkatkan peluang diterima kerja.\n\n"
        "🤖 <b>KerjaDimana.id</b>"
    )

    keyboard = {
        "inline_keyboard": [
            [
                {
                    "text": "📄 Generator Buat CV",
                    "url": "https://crypotential.com/vynh0yqe?key=0f3039ec0183e232743c1c0ce0a299f6"
                }
            ],
            [
                {
                    "text": "📄 Generator Buat Lamaran",
                    "url": "https://aboardpoodlechat.com/u7t8hcvxga?key=9718e827473e98bbec182ac0a8acf4e3"
                }
            ]
        ]
    }

    payload = {
        "chat_id": CHAT_ID,
        "text": pesan,
        "parse_mode": "HTML",
        "reply_markup": keyboard,
        "disable_web_page_preview": True
    }

    try:
        response = requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json=payload,
            timeout=30
        )

    except requests.RequestException as error:
        print(f"❌ Gagal terhubung ke Telegram: {error}")
        return False

    try:
        data = response.json()

    except ValueError:
        print("❌ Response Telegram bukan JSON.")
        print(response.text)
        return False

    if response.status_code == 200 and data.get("ok"):
        print(
            f"✅ BERHASIL: "
            f"{html.unescape(title)[:70]}"
        )
        return True

    print("❌ GAGAL TELEGRAM")
    print(f"HTTP Status: {response.status_code}")
    print(f"Response: {response.text}")

    return False


# =========================================================
# PROSES RSS
# =========================================================

def process_feed(rss_url, sent, force=False):
    print()
    print("=" * 60)
    print(f"📡 Mengambil RSS: {rss_url}")

    try:
        response = requests.get(
            rss_url,
            timeout=30,
            headers={
                "User-Agent": "Mozilla/5.0 KerjaDimanaBot/1.0"
            }
        )

    except requests.RequestException as error:
        print(f"❌ Gagal mengambil RSS: {error}")
        return 0

    if response.status_code != 200:
        print(
            f"⚠️ RSS HTTP {response.status_code}. "
            "Feed dilewati."
        )
        return 0

    try:
        root = ET.fromstring(response.content)

    except ET.ParseError as error:
        print(f"❌ XML RSS tidak valid: {error}")
        return 0

    items = root.findall(".//item")

    print(f"📦 Ditemukan {len(items)} item.")

    jumlah_berhasil = 0

    for item in items[:5]:
        title_raw = item.findtext("title", "")
        link_raw = item.findtext("link", "")
        desc_raw = item.findtext("description", "")
        source_raw = item.findtext("source", "")

        link = (link_raw or "").strip()

        if not link:
            print("⏭️ Item tidak mempunyai link.")
            continue

        if link in sent and not force:
            print(
                f"⏭️ Sudah pernah dikirim: "
                f"{title_raw[:60]}"
            )
            continue

        title_plain = clean_job_title(title_raw)
        description_plain = strip_html(desc_raw)

        if not title_plain:
            title_plain = "KerjaDimana.id"

        if len(description_plain) < 80 or description_plain.lower() in title_plain.lower():
            description_plain = fallback_description(
                title_plain,
                strip_html(source_raw)
            )

        title = html.escape(title_plain)
        description = html.escape(description_plain)

        print(
            f"📨 Mengirim: "
            f"{html.unescape(title)[:70]}"
        )

        berhasil = send_telegram(
            title,
            description,
            link
        )

        if berhasil:
            if link not in sent:
                sent.append(link)

                # Langsung simpan agar tidak hilang jika proses berhenti
                save_sent(sent)

            jumlah_berhasil += 1

            # Jeda antar posting
            time.sleep(2)

    return jumlah_berhasil


# =========================================================
# MAIN
# =========================================================

def main(force=False):
    validate_config()

    sent = load_sent()

    print("=" * 60)
    print("🤖 KerjaDimana.id Auto Loker")
    print(f"📢 CHAT_ID: {CHAT_ID}")
    print(f"📚 Database anti-duplikat: {len(sent)} link")
    print(f"🔁 Force kirim ulang: {'YA' if force else 'TIDAK'}")
    print("=" * 60)

    total = 0

    for rss_url in RSS_FEEDS:
        total += process_feed(
            rss_url,
            sent,
            force=force
        )

    if total == 0 and FALLBACK_RSS_FEEDS:
        print()
        print("=" * 60)
        print("⚠️ Feed utama tidak mengirim loker.")
        print("🔎 Mencoba fallback Google News RSS...")
        print("=" * 60)

        for rss_url in FALLBACK_RSS_FEEDS:
            total += process_feed(
                rss_url,
                sent,
                force=force
            )

    save_sent(sent)

    print()
    print("=" * 60)
    print(
        f"✅ SELESAI — "
        f"{total} lowongan baru dikirim."
    )
    print("=" * 60)

    return total


if __name__ == "__main__":
    main()
