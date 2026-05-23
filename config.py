"""
Cấu hình từ biến môi trường (env vars).
"""
import os
import sys

# ===== Telegram =====
# Token CHỈ đọc từ env var — KHÔNG hardcode trong code (bảo mật).
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
if not BOT_TOKEN:
    print("[config] WARNING: BOT_TOKEN env var is EMPTY!", file=sys.stderr)

ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID", "558789316")

# ===== Sepay =====
# Nếu không có key → mode manual (admin tự /confirm).
# Có key → tự động gửi link khi Sepay báo giao dịch.
SEPAY_API_KEY = os.environ.get("SEPAY_API_KEY", "") or ""

# ===== Ngân hàng =====
# MB Bank — Sepay có API trực tiếp (không cần SMS forward).
BANK_ACCOUNT = os.environ.get("BANK_ACCOUNT", "3100181888868")
BANK_NAME = os.environ.get("BANK_NAME", "MB Bank")
BANK_OWNER = os.environ.get("BANK_OWNER", "TA QUANG THUAN")

# ===== Hosting =====
BASE_URL = os.environ.get("BASE_URL", "https://your-app.railway.app")

# ===== Sản phẩm =====
# Link Drive được lưu trong DB (cập nhật qua /set_link), giá cố định ở đây
PRODUCTS = {
    "mua_combo": {
        "name": "Combo Full Pack (Claude + OpenCode, 8 cấp)",
        "price": 199000,
        "drive_link": "https://drive.google.com/file/d/1KC9PrlJ4hw0K0OwSPfLHXOuw96UcJ8eK/view?usp=sharing",
    },
    "mua_claude": {
        "name": "Claude AI Thực Chiến (4 cấp)",
        "price": 99000,
        "drive_link": "https://drive.google.com/file/d/1Bs71fSnXNP2eXv8y0qh4I3jSiCcAkHsa/view?usp=sharing",
    },
    "mua_opencode": {
        "name": "OpenCode Thực Chiến (4 cấp)",
        "price": 149000,
        "drive_link": "https://drive.google.com/file/d/1ioWrucdyGXpA7zvB1pUFKVYmsGaUU-5o/view?usp=sharing",
    },
}

# Startup check — log trạng thái ngay khi import (gunicorn cũng chạy)
print(f"[config] BOT_TOKEN: {'✓' if BOT_TOKEN else '✗ MISSING'} ({BOT_TOKEN[:10]}...{BOT_TOKEN[-5:] if len(BOT_TOKEN) > 15 else ''})")
print(f"[config] SEPAY_API_KEY: {'✓' if SEPAY_API_KEY else '✗ MISSING (manual mode)'}")
print(f"[config] ADMIN_CHAT_ID: {'✓' if ADMIN_CHAT_ID else '✗ MISSING'}")
print(f"[config] BANK: {BANK_NAME} - {BANK_ACCOUNT} - {BANK_OWNER}")
print(f"[config] BASE_URL: {BASE_URL}")
