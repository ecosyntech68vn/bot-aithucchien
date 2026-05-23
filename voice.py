"""Cách 2 — đọc giọng thông tin thanh toán rồi gửi audio vào Telegram (loa đọc đơn).

An toàn tuyệt đối: TẤT CẢ lỗi đều bị nuốt, không bao giờ làm hỏng luồng giao hàng.
gTTS được import lười (trong hàm) nên kể cả chưa cài lib, gọi vẫn không vỡ.
"""


def announce(bot_token, chat_id, text):
    try:
        import io
        import requests
        from gtts import gTTS

        if not (bot_token and chat_id and text):
            return
        buf = io.BytesIO()
        gTTS(text=text, lang="vi").write_to_fp(buf)
        buf.seek(0)
        requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendAudio",
            data={"chat_id": str(chat_id), "title": "Thông báo thanh toán"},
            files={"audio": ("thanhtoan.mp3", buf, "audio/mpeg")},
            timeout=20,
        )
    except Exception:
        pass
