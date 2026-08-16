import io
import os
import re
import json
import time
import threading
import contextlib
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import telebot
from telebot import types

import fetch_jbrtcjayumajakuning.py


# =========================
# CONFIG
# =========================

BOT_TOKEN = (
    os.getenv("BOT_TOKEN")
    or os.getenv("TOKEN_BOT")
    or ""
).strip()

TARGET_CHAT_ID = (
    os.getenv("CHAT_ID")
    or os.getenv("TELEGRAM_CHAT_ID")
    or os.getenv("MY_CHAT_ID")
    or ""
).strip()

ADMIN_CHAT_IDS = {
    chat_id.strip()
    for chat_id in (
        os.getenv("ADMIN_CHAT_ID")
        or os.getenv("ADMIN_CHAT_IDS")
        or os.getenv("MY_CHAT_ID")
        or ""
    ).replace(",", " ").split()
    if chat_id.strip()
}

SCHEDULE_FILE = Path("schedule.json")
DEFAULT_SCHEDULE = ["08:00", "12:00", "19:40"]
WIB = ZoneInfo("Asia/Jakarta")

if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN tidak ditemukan. "
        "Masukkan BOT_TOKEN di Railway Variables."
    )


# =========================
# INIT BOT
# =========================

bot = telebot.TeleBot(
    BOT_TOKEN,
    parse_mode="HTML"
)

schedule_lock = threading.RLock()
run_lock = threading.Lock()


# =========================
# HELPERS
# =========================

def normalize_time(raw_time):
    match = re.fullmatch(r"(\d{1,2})[:.](\d{2})", raw_time.strip())
    if not match:
        return None

    hour = int(match.group(1))
    minute = int(match.group(2))

    if hour > 23 or minute > 59:
        return None

    return f"{hour:02d}:{minute:02d}"


def load_schedule():
    if not SCHEDULE_FILE.exists():
        save_schedule(DEFAULT_SCHEDULE)
        return DEFAULT_SCHEDULE[:]

    try:
        data = json.loads(SCHEDULE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        save_schedule(DEFAULT_SCHEDULE)
        return DEFAULT_SCHEDULE[:]

    times = data.get("times") if isinstance(data, dict) else data

    if not isinstance(times, list):
        save_schedule(DEFAULT_SCHEDULE)
        return DEFAULT_SCHEDULE[:]

    clean_times = sorted(
        {
            normalized
            for normalized in (normalize_time(str(item)) for item in times)
            if normalized
        }
    )

    if not clean_times:
        clean_times = DEFAULT_SCHEDULE[:]

    save_schedule(clean_times)
    return clean_times


def save_schedule(times):
    SCHEDULE_FILE.write_text(
        json.dumps({"times": times}, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def schedule_text():
    with schedule_lock:
        times = load_schedule()

    return ", ".join(f"{item} WIB" for item in times)


def is_admin(message):
    if not ADMIN_CHAT_IDS:
        return False

    user_id = str(message.from_user.id) if message.from_user else ""
    chat_id = str(message.chat.id)

    return user_id in ADMIN_CHAT_IDS or chat_id in ADMIN_CHAT_IDS


def require_admin(message):
    if is_admin(message):
        return True

    if not ADMIN_CHAT_IDS:
        bot.reply_to(
            message,
            (
                "Admin belum disetel. Tambahkan <b>ADMIN_CHAT_ID</b> "
                "di Railway Variables, isinya ID Telegram admin."
            ),
            reply_markup=main_menu()
        )
        return False

    bot.reply_to(
        message,
        "Command ini khusus admin.",
        reply_markup=main_menu()
    )
    return False


def run_loker_now(force=False):
    if not TARGET_CHAT_ID:
        return False, "CHAT_ID/TELEGRAM_CHAT_ID belum disetel di Railway Variables."

    if not run_lock.acquire(blocking=False):
        return False, "Proses loker masih jalan. Tunggu sebentar ya."

    old_chat_id = fetch_loker.CHAT_ID

    try:
        fetch_loker.CHAT_ID = TARGET_CHAT_ID
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            total = fetch_loker.main(force=force)

        log = output.getvalue()
        match = re.search(r"(\d+) lowongan baru dikirim", log)
        total_text = match.group(1) if match else str(total)

        if force:
            return True, f"Selesai. {total_text} loker terbaru dikirim ulang."

        return True, f"Selesai. {total_text} lowongan baru dikirim."

    except SystemExit as error:
        return False, f"Gagal menjalankan loker. Exit code: {error.code}"

    except Exception as error:
        return False, f"Gagal menjalankan loker: {error}"

    finally:
        fetch_loker.CHAT_ID = old_chat_id
        run_lock.release()


def main_menu():
    keyboard = types.ReplyKeyboardMarkup(
        resize_keyboard=True,
        row_width=2
    )
    keyboard.add(
        types.KeyboardButton("/start"),
        types.KeyboardButton("/help"),
        types.KeyboardButton("/loker"),
        types.KeyboardButton("/jadwal"),
        types.KeyboardButton("/setjadwal"),
        types.KeyboardButton("/runloker"),
        types.KeyboardButton("/forceloker"),
        types.KeyboardButton("/resetloker"),
        types.KeyboardButton("/id"),
        types.KeyboardButton("/admin")
    )
    return keyboard


# =========================
# HANDLERS
# =========================

@bot.message_handler(commands=["start"])
def handle_start(message):
    bot.reply_to(
        message,
        (
            "Selamat datang di Bot <b>KerjaDimana.id</b>!\n\n"
            "Ketik /help untuk melihat menu."
        ),
        reply_markup=main_menu()
    )


@bot.message_handler(commands=["help"])
def handle_help(message):
    bot.reply_to(
        message,
        (
            "<b>Menu Bantuan:</b>\n"
            "/start - Mulai bot\n"
            "/help - Bantuan\n"
            "/loker - Info lowongan terbaru\n"
            "/jadwal - Lihat jadwal otomatis\n"
            "/setjadwal 08:00 12:00 19:40 - Ubah jadwal otomatis\n"
            "/runloker - Kirim loker sekarang\n"
            "/forceloker - Paksa kirim ulang loker terbaru\n"
            "/resetloker - Reset riwayat anti-duplikat\n"
            "/id - Lihat ID Telegram kamu\n"
            "/admin - Info admin"
        ),
        reply_markup=main_menu()
    )


@bot.message_handler(commands=["loker"])
def handle_loker(message):
    bot.reply_to(
        message,
        (
            "Info lowongan terbaru dikirim otomatis ke channel/grup "
            "KerjaDimana.id.\n\n"
            "Pantau terus update dari bot ini ya."
        ),
        reply_markup=main_menu()
    )


@bot.message_handler(commands=["jadwal"])
def handle_jadwal(message):
    bot.reply_to(
        message,
        f"Jadwal otomatis sekarang:\n<b>{schedule_text()}</b>",
        reply_markup=main_menu()
    )


@bot.message_handler(commands=["setjadwal"])
def handle_setjadwal(message):
    if not require_admin(message):
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(
            message,
            (
                "Format:\n"
                "<code>/setjadwal 08:00 12:00 19:40</code>"
            ),
            reply_markup=main_menu()
        )
        return

    raw_items = re.split(r"[\s,]+", parts[1].strip())
    times = []

    for item in raw_items:
        normalized = normalize_time(item)
        if not normalized:
            bot.reply_to(
                message,
                f"Jam <b>{item}</b> tidak valid. Contoh: 08:00",
                reply_markup=main_menu()
            )
            return
        times.append(normalized)

    with schedule_lock:
        clean_times = sorted(set(times))
        save_schedule(clean_times)

    bot.reply_to(
        message,
        f"Jadwal otomatis diubah ke:\n<b>{schedule_text()}</b>",
        reply_markup=main_menu()
    )


@bot.message_handler(commands=["runloker"])
def handle_runloker(message):
    if not require_admin(message):
        return

    bot.reply_to(message, "Oke, loker sedang dicek dan dikirim sekarang.")
    success, info = run_loker_now()

    bot.reply_to(
        message,
        info if success else f"Gagal: {info}",
        reply_markup=main_menu()
    )


@bot.message_handler(commands=["forceloker"])
def handle_forceloker(message):
    if not require_admin(message):
        return

    bot.reply_to(message, "Oke, loker terbaru sedang kirim ulang.")
    success, info = run_loker_now(force=True)

    bot.reply_to(
        message,
        info if success else f"Gagal: {info}",
        reply_markup=main_menu()
    )


@bot.message_handler(commands=["resetloker"])
def handle_resetloker(message):
    if not require_admin(message):
        return

    fetch_loker.save_sent([])

    bot.reply_to(
        message,
        (
            "Riwayat loker sudah direset.\n\n"
            "Setelah ini /runloker akan mengirim lagi loker terbaru "
            "yang ada di RSS."
        ),
        reply_markup=main_menu()
    )


@bot.message_handler(commands=["admin"])
def handle_admin(message):
    bot.reply_to(
        message,
        "Admin KerjaDimana.id siap membantu. Kirim pesan kebutuhan kamu di sini.",
        reply_markup=main_menu()
    )


@bot.message_handler(commands=["id"])
def handle_id(message):
    user_id = message.from_user.id if message.from_user else "-"
    chat_id = message.chat.id

    bot.reply_to(
        message,
        (
            "ID Telegram kamu:\n"
            f"<code>{user_id}</code>\n\n"
            "ID chat ini:\n"
            f"<code>{chat_id}</code>"
        ),
        reply_markup=main_menu()
    )


@bot.message_handler(func=lambda message: True)
def handle_unknown(message):
    bot.reply_to(
        message,
        "Perintah belum dikenali. Ketik /help untuk melihat menu.",
        reply_markup=main_menu()
    )


# =========================
# SCHEDULER
# =========================

def scheduler_loop():
    last_run_key = None

    while True:
        now = datetime.now(WIB)
        current_time = now.strftime("%H:%M")
        current_key = now.strftime("%Y-%m-%d %H:%M")

        with schedule_lock:
            times = load_schedule()

        if current_time in times and current_key != last_run_key:
            print(f"Menjalankan loker otomatis: {current_time} WIB")
            success, info = run_loker_now()
            print(info if success else f"Gagal: {info}")
            last_run_key = current_key

        time.sleep(20)


def main():
    print("=" * 50)
    print("KerjaDimana.id Bot")
    print("BOT AKTIF")
    print(f"Jadwal otomatis: {schedule_text()}")
    print("=" * 50)

    threading.Thread(
        target=scheduler_loop,
        daemon=True
    ).start()

    bot.infinity_polling(
        timeout=30,
        long_polling_timeout=30,
        skip_pending=True
    )


if __name__ == "__main__":
    main()
