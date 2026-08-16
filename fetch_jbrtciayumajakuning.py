import os
import re
import json
import time
import html
import requests
import xml.etree.ElementTree as ET


# =========================================================
# JBRTCIAYUMAJAKUNING
# AUTO POST JUAL BELI RUMAH & TANAH
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

CHAT_ID = (
    os.getenv("CHAT_ID")
    or os.getenv("TELEGRAM_CHAT_ID")
    or ""
).strip()


# =========================================================
# SUMBER RSS
# =========================================================

RSS_URLS = [
    "https://rss.app/feeds/Mlc5shYuFREkcpMt.xml",
    "https://rss.app/feeds/NS26IWfOwwr3jnCu.xml",
    "https://rss.app/feeds/UGlfJoXKzJVB3OD8.xml",
]


# =========================================================
# PENGATURAN
# =========================================================

SENT_FILE = "sent.json"

# Maksimal posting baru dari setiap RSS
MAX_POST_PER_RSS = 3

# Jeda antar posting
POST_DELAY = 3

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"


# =========================================================
# VALIDASI SECRET
# =========================================================

def validate_config():

    print("🔍 Memeriksa konfigurasi...")

    if not BOT_TOKEN:
        print("❌ BOT_TOKEN belum ditemukan.")
        print("Tambahkan BOT_TOKEN di GitHub Secrets.")
        raise SystemExit(1)

    if not CHAT_ID:
        print("❌ CHAT_ID belum ditemukan.")
        print("Tambahkan CHAT_ID di GitHub Secrets.")
        raise SystemExit(1)

    print("✅ BOT_TOKEN ditemukan.")
    print("✅ CHAT_ID ditemukan.")


# =========================================================
# CEK BOT TELEGRAM
# =========================================================

def check_bot():

    print("\n🤖 Memeriksa koneksi Telegram...")

    try:

        response = requests.get(
            f"{TELEGRAM_API}/getMe",
            timeout=30
        )

        data = response.json()

    except Exception as error:

        print(f"❌ Tidak dapat terhubung ke Telegram: {error}")
        return False

    if data.get("ok"):

        bot = data.get("result", {})

        print(
            f"✅ Bot aktif: "
            f"@{bot.get('username', 'unknown')}"
        )

        return True

    print("❌ BOT_TOKEN tidak valid.")
    print(response.text)

    return False


# =========================================================
# CEK CHAT / CHANNEL
# =========================================================

def check_chat():

    print("\n📢 Memeriksa CHAT_ID...")

    try:

        response = requests.get(
            f"{TELEGRAM_API}/getChat",
            params={
                "chat_id": CHAT_ID
            },
            timeout=30
        )

        data = response.json()

    except Exception as error:

        print(f"❌ Gagal memeriksa CHAT_ID: {error}")
        return False

    if data.get("ok"):

        chat = data.get("result", {})

        print(
            f"✅ Tujuan Telegram: "
            f"{chat.get('title') or chat.get('username') or chat.get('first_name', 'Unknown')}"
        )

        print(
            f"   Chat ID: {chat.get('id')}"
        )

        return True

    print("❌ CHAT_ID tidak dapat diakses.")
    print(response.text)

    return False


# =========================================================
# LOAD POSTING YANG SUDAH DIKIRIM
# =========================================================

def load_sent():

    if not os.path.exists(SENT_FILE):

        return set()

    try:

        with open(
            SENT_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        if isinstance(data, list):

            return set(data)

    except Exception as error:

        print(
            f"⚠️ Tidak dapat membaca {SENT_FILE}: "
            f"{error}"
        )

    return set()


# =========================================================
# SIMPAN POSTING YANG SUDAH DIKIRIM
# =========================================================

def save_sent(sent):

    try:

        with open(
            SENT_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                list(sent),
                file,
                ensure_ascii=False,
                indent=2
            )

    except Exception as error:

        print(
            f"⚠️ Gagal menyimpan {SENT_FILE}: "
            f"{error}"
        )


# =========================================================
# BERSIHKAN HTML
# =========================================================

def clean_text(text):

    if not text:
        return ""

    # Hapus CDATA
    text = text.replace(
        "<![CDATA[",
        ""
    ).replace(
        "]]>",
        ""
    )

    # Hapus HTML
    text = re.sub(
        r"<[^>]+>",
        " ",
        text
    )

    # Decode HTML entity
    text = html.unescape(text)

    # Rapikan spasi
    text = " ".join(
        text.split()
    )

    return text.strip()


# =========================================================
# EKSTRAK GAMBAR DARI DESCRIPTION
# =========================================================

def extract_image(text):

    if not text:
        return None

    patterns = [
        r'<img[^>]+src=["\']([^"\']+)["\']',
        r'<media:content[^>]+url=["\']([^"\']+)["\']',
        r'<enclosure[^>]+url=["\']([^"\']+)["\']'
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            return match.group(1)

    return None


# =========================================================
# FORMAT POSTING
# =========================================================

def create_message(
    title,
    description,
    link
):

    title = clean_text(title)

    description = clean_text(
        description
    )

    if not title:

        title = "Properti Baru"

    if not description:

        description = (
            "Informasi jual beli "
            "rumah dan tanah."
        )

    # Batasi panjang
    if len(description) > 2800:

        description = (
            description[:2800]
            + "..."
        )

    message = (
        "🏠 <b>JBRTCIAYUMAJAKUNING</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        f"📌 <b>{html.escape(title)}</b>\n\n"

        "📝 <b>Informasi Properti</b>\n"
        f"{html.escape(description)}\n\n"

        "━━━━━━━━━━━━━━━━━━\n"

        "🔗 <b>Lihat Detail:</b>\n"
        f"{html.escape(link)}\n\n"

        "━━━━━━━━━━━━━━━━━━\n"

        "🏡 <b>JUAL BELI RUMAH & TANAH</b>\n"
        "📍 Cirebon • Majalengka • Kuningan\n"
        "📢 JBRTCIAYUMAJAKUNING"
    )

    return message


# =========================================================
# KIRIM TEXT KE TELEGRAM
# =========================================================

def send_message(message):

    try:

        response = requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json={
                "chat_id": CHAT_ID,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": False
            },
            timeout=30
        )

        data = response.json()

    except Exception as error:

        print(
            f"❌ Error Telegram: {error}"
        )

        return False

    if data.get("ok"):

        print(
            "✅ Berhasil posting ke Telegram."
        )

        return True

    print(
        "❌ Telegram gagal menerima pesan."
    )

    print(
        response.text
    )

    return False


# =========================================================
# KIRIM FOTO KE TELEGRAM
# =========================================================

def send_photo(
    image_url,
    caption
):

    if not image_url:

        return False

    try:

        response = requests.post(
            f"{TELEGRAM_API}/sendPhoto",
            json={
                "chat_id": CHAT_ID,
                "photo": image_url,
                "caption": caption,
                "parse_mode": "HTML"
            },
            timeout=30
        )

        data = response.json()

    except Exception as error:

        print(
            f"⚠️ Gagal mengirim foto: {error}"
        )

        return False

    if data.get("ok"):

        print(
            "✅ Foto berhasil dikirim."
        )

        return True

    print(
        "⚠️ Foto gagal dikirim."
    )

    print(
        response.text
    )

    return False


# =========================================================
# AMBIL RSS
# =========================================================

def get_rss(url):

    print("\n📡 Mengambil RSS:")
    print(url)

    try:

        response = requests.get(
            url,
            timeout=30,
            headers={
                "User-Agent":
                "Mozilla/5.0 "
                "JBRTCIAYUMAJAKUNING"
            }
        )

    except requests.RequestException as error:

        print(
            f"❌ Gagal mengambil RSS: "
            f"{error}"
        )

        return None

    print(
        f"HTTP Status: "
        f"{response.status_code}"
    )

    if response.status_code != 200:

        print(
            "❌ RSS tidak dapat diakses."
        )

        print(
            response.text[:500]
        )

        return None

    try:

        root = ET.fromstring(
            response.content
        )

        return root

    except ET.ParseError as error:

        print(
            f"❌ RSS bukan XML valid: "
            f"{error}"
        )

        return None


# =========================================================
# AMBIL DATA ITEM RSS
# =========================================================

def get_items(root):

    # RSS standar
    items = root.findall(
        ".//item"
    )

    if items:

        return items

    # Atom fallback
    items = root.findall(
        ".//{http://www.w3.org/2005/Atom}entry"
    )

    return items


# =========================================================
# AMBIL NILAI XML
# =========================================================

def get_item_value(
    item,
    tag
):

    # RSS biasa
    element = item.find(tag)

    if element is not None:

        return (
            element.text or ""
        ).strip()

    # Atom
    element = item.find(
        f"{{http://www.w3.org/2005/Atom}}{tag}"
    )

    if element is not None:

        return (
            element.text or ""
        ).strip()

    return ""


# =========================================================
# AMBIL LINK
# =========================================================

def get_item_link(item):

    # RSS
    link = get_item_value(
        item,
        "link"
    )

    if link:

        return link

    # Atom
    atom_link = item.find(
        "{http://www.w3.org/2005/Atom}link"
    )

    if atom_link is not None:

        return atom_link.attrib.get(
            "href",
            ""
        ).strip()

    return ""


# =========================================================
# PROSES SEMUA RSS
# =========================================================

def process_feeds():

    sent = load_sent()

    total_items = 0

    total_posted = 0

    for rss_number, rss_url in enumerate(
        RSS_URLS,
        start=1
    ):

        print("\n")
        print("=" * 65)

        print(
            f"📡 RSS {rss_number}/{len(RSS_URLS)}"
        )

        print(rss_url)

        print("=" * 65)

        root = get_rss(
            rss_url
        )

        if root is None:

            print(
                "⏭️ RSS dilewati."
            )

            continue

        items = get_items(
            root
        )

        print(
            f"📦 Ditemukan "
            f"{len(items)} item."
        )

        total_items += len(items)

        # Ambil beberapa terbaru
        for item in items[
            :MAX_POST_PER_RSS
        ]:

            title = get_item_value(
                item,
                "title"
            )

            description = get_item_value(
                item,
                "description"
            )

            if not description:

                description = get_item_value(
                    item,
                    "summary"
                )

            link = get_item_link(
                item
            )

            # Bersihkan
            title = clean_text(
                title
            )

            description = clean_text(
                description
            )

            # =====================================
            # VALIDASI
            # =====================================

            if not link:

                print(
                    "⏭️ Item dilewati "
                    "(tidak ada link)."
                )

                continue

            # =====================================
            # ANTI DUPLIKAT
            # =====================================

            if link in sent:

                print(
                    f"⏭️ SUDAH DIPOSTING:"
                )

                print(
                    f"   {title[:100]}"
                )

                continue

            # =====================================
            # TAMPILKAN INFO
            # =====================================

            print("\n")
            print(
                "🆕 LISTING BARU"
            )

            print(
                f"Judul: {title[:100]}"
            )

            print(
                f"Link: {link}"
            )

            # =====================================
            # BUAT PESAN
            # =====================================

            message = create_message(
                title,
                description,
                link
            )

            # =====================================
            # GAMBAR
            # =====================================

            raw_description = (
                get_item_value(
                    item,
                    "description"
                )
            )

            image_url = extract_image(
                raw_description
            )

            # =====================================
            # POSTING
            # =====================================

            success = False

            if image_url:

                success = send_photo(
                    image_url,
                    message
                )

            # Jika foto gagal / tidak ada
            if not success:

                success = send_message(
                    message
                )

            # =====================================
            # SIMPAN ANTI DUPLIKAT
            # =====================================

            if success:

                sent.add(
                    link
                )

                save_sent(
                    sent
                )

                total_posted += 1

                print(
                    "✅ Listing tersimpan "
                    "sebagai sudah diposting."
                )

                time.sleep(
                    POST_DELAY
                )

            else:

                print(
                    "❌ Listing tidak ditandai "
                    "sebagai terkirim."
                )

    # =============================================
    # HASIL AKHIR
    # =============================================

    print("\n")
    print("=" * 65)

    print(
        "🏠 JBRTCIAYUMAJAKUNING"
    )

    print(
        "🏡 AUTO POST JUAL BELI "
        "RUMAH & TANAH"
    )

    print("=" * 65)

    print(
        f"📦 Total item RSS : "
        f"{total_items}"
    )

    print(
        f"📨 Posting baru    : "
        f"{total_posted}"
    )

    print("=" * 65)

    return total_posted


# =========================================================
# MAIN
# =========================================================

def main():

    print("\n")
    print("=" * 65)

    print(
        "🏠 JBRTCIAYUMAJAKUNING"
    )

    print(
        "AUTO POST RUMAH & TANAH"
    )

    print("=" * 65)

    # Cek konfigurasi
    validate_config()

    # Cek bot
    if not check_bot():

        raise SystemExit(1)

    # Cek tujuan
    if not check_chat():

        raise SystemExit(1)

    # Proses RSS
    process_feeds()

    print("\n")
    print(
        "🎉 Workflow selesai."
    )


# =========================================================
# START
# =========================================================

if __name__ == "__main__":

    main()
