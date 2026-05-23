# QUY TRÌNH TRIỂN KHAI BÁN HÀNG TỰ ĐỘNG VỚI SEPAY MB BANK

> Runbook tái sử dụng — dựng bot Telegram bán sản phẩm số, tự xác thực chuyển khoản MB Bank qua Sepay và tự giao link.
> EcoSynTech Global · Tạ Quang Thuận · cập nhật 2026-05-24

---

## 0. Tổng quan

**Mục tiêu:** khách chuyển khoản → trong ~30 giây bot tự giao sản phẩm, không cần người trực.

**Luồng hoạt động:**

```
[1] Khách bấm /mua_combo trong bot Telegram
      ↓
[2] Bot tạo mã đơn TXNxxxxx, lưu DB, gửi QR (VietQR) + STK + nội dung CK
      ↓
[3] Khách CK vào MB Bank, nội dung "MUA TXNxxxxx"
      ↓
[4] MB Bank → Sepay (giám sát tài khoản) → POST {BASE_URL}/sepay-webhook
      ↓
[5] Bot xác thực: Apikey + transferType=in + khớp mã đơn + đủ tiền (±100đ)
      ↓
[6] Bot tự gửi link Google Drive cho khách + báo admin
```

**Nguyên tắc cốt lõi (phải nhớ):**

1. **MB Bank, KHÔNG dùng Vietcombank.** Sepay có API trực tiếp với MB → biến động về trong 1–3 giây. VCB không có API (phải SMS/email forward, mong manh).
2. **3 giá trị phải khớp nhau tuyệt đối** ở mọi nơi: `BANK_NAME`, `BANK_ACCOUNT`, và tài khoản Sepay đang giám sát. Lệch một cái là đứt luồng.
3. **`SEPAY_API_KEY` phải giống hệt** ở 2 đầu: webhook Sepay (mục Bảo mật) và env Railway.
4. **Không hardcode token/secret trong code.** Chỉ đọc từ env.

---

## 1. Chuẩn bị tài khoản (làm 1 lần)

| # | Việc | Kết quả cần có |
|---|------|----------------|
| 1.1 | Mở **MB Bank**, đăng ký **Sepay** (sepay.vn), liên kết tài khoản MB trong Sepay | STK MB + tên chủ TK + Sepay đã thấy biến động |
| 1.2 | Tạo bot Telegram qua **@BotFather** (`/newbot`) | `BOT_TOKEN` dạng `1234567890:ABC...` |
| 1.3 | Lấy chat ID admin qua **@userinfobot** | `ADMIN_CHAT_ID` (số) |
| 1.4 | Tạo link **Google Drive** cho từng sản phẩm, set "Anyone with link → Viewer" | URL link tải mỗi SKU |
| 1.5 | Repo bot **PRIVATE** trên GitHub + tài khoản **Railway** (login bằng GitHub) | repo + project Railway |

---

## 2. Cấu trúc bot (Flask + Postgres)

| File | Vai trò |
|------|---------|
| `app.py` | Flask: route `/telegram-webhook`, `/sepay-webhook`, `/` (health) |
| `config.py` | Đọc toàn bộ env vars + `PRODUCTS` (giá + link Drive) |
| `db.py` | Lưu pending orders, log GD không khớp |
| `requirements.txt`, `Procfile` | deps + lệnh chạy cho Railway |

**Endpoint nhận tiền (quan trọng nhất) — `/sepay-webhook`:**

- Yêu cầu header `Authorization: Apikey {SEPAY_API_KEY}` → sai/thiếu = `401`.
- Nếu `SEPAY_API_KEY` rỗng → trả "Manual mode", **bỏ qua** mọi giao dịch (admin phải `/confirm` tay).
- Chỉ xử lý `transferType == "in"` (tiền vào).
- Trích mã đơn từ nội dung `MUA TXNxxxxx`, đối chiếu số tiền (cho lệch ±100đ), rồi giao link.

---

## 3. Deploy lên Railway

1. Railway → **New Project → Deploy from GitHub repo** → chọn repo bot (Railway tự nhận Python).
2. Thêm service **Postgres** (nếu bot dùng DB) trong cùng project.
3. Tab **Settings → Networking → Generate Domain** để lấy `BASE_URL` (dạng `https://xxx.up.railway.app`).
4. Tab **Variables** → nạp đủ env (bảng dưới).
5. Mỗi lần đổi env hoặc push code lên nhánh deploy → Railway **tự redeploy**.

### Bảng env vars chuẩn

| Biến | Giá trị mẫu | Ghi chú |
|------|-------------|---------|
| `BOT_TOKEN` | `1234567890:ABC...` | Token Telegram. **Chỉ ở env, không hardcode.** |
| `ADMIN_CHAT_ID` | `558789316` | Chat ID admin nhận thông báo |
| `SEPAY_API_KEY` | `sepay_xxxxx` | **Phải giống hệt key trong webhook Sepay.** Có key = chế độ AUTOMATIC |
| `BANK_ACCOUNT` | `3100181888868` | **Số TK MB** mà Sepay giám sát |
| `BANK_NAME` | `MB Bank` | Phải khớp dict BIN (MB Bank → 970422). Sai tên = QR sai ngân hàng |
| `BANK_OWNER` | `TA QUANG THUAN` | Tên chủ TK (in hoa, không dấu) |
| `BASE_URL` | `https://xxx.up.railway.app` | Domain Railway |
| `TELEGRAM_WEBHOOK_SECRET` | (tuỳ chọn) | Chống giả mạo update Telegram |

> **Kiểm tra nhanh:** mở `BASE_URL/` trên trình duyệt → phải thấy `{"status":"ok","service":"..."}`.

---

## 4. Tạo webhook Sepay (đúng cấu hình)

my.sepay.vn → **Tích hợp WebHooks → Tạo webhook**, điền 4 bước:

| Bước | Cấu hình |
|------|----------|
| 1. Cơ bản | URL = `{BASE_URL}/sepay-webhook` · Loại GD = **Tiền vào** · Định dạng = **JSON** · bật "Tự động gửi lại khi server lỗi" |
| 2. Tài khoản | "Tất cả tài khoản" (nếu chỉ có 1 TK) · để TẮT "Dùng để xác thực thanh toán" (bot tự match) |
| 3. Bảo mật | Phương thức = **API Key** → nhập đúng giá trị `SEPAY_API_KEY` (Sepay sẽ gửi `Authorization: Apikey {key}`) |
| 4. Cảnh báo | Tuỳ chọn (cần cấu hình Kênh cảnh báo trước nếu bật) |

---

## 5. Kết nối Telegram webhook

Mở trên trình duyệt (thay `{TOKEN}`, `{BASE_URL}`):

```
https://api.telegram.org/bot{TOKEN}/setWebhook?url={BASE_URL}/telegram-webhook
```

Trả về `{"ok":true,...}` = xong. Kiểm tra: `.../getWebhookInfo` → `last_error_message` phải `null`.

---

## 6. Link sản phẩm

2 cách (bot ưu tiên DB, fallback về code):

- **Hardcode trong `config.py`** (`PRODUCTS[sku]["drive_link"]`) — bền, không mất khi DB reset. **Khuyến nghị.**
- Hoặc admin chat bot: `/set_link <sku> <url>` (lưu DB).

---

## 7. Kiểm thử (bắt buộc trước khi mở bán)

| Test | Cách | Kết quả đúng |
|------|------|--------------|
| Bot sống | `/start` | Bot trả menu |
| Tạo đơn | `/mua_combo` | Ra mã `TXNxxxxx` + QR đúng MB Bank |
| QR hợp lệ | Quét QR bằng app ngân hàng | App điền đúng STK MB + số tiền + nội dung |
| **Thiếu tiền** | CK 1.000đ, nội dung `MUA TXNxxxxx` | Bot báo **underpaid** (đã verify ✔) |
| **Đủ tiền** | CK đúng số + nội dung | Bot **tự giao link** + admin nhận noti (đã verify ✔) |

---

## 8. Các lỗi đã gặp & cách tránh (kinh nghiệm thực chiến)

| Triệu chứng | Nguyên nhân gốc | Cách xử lý |
|-------------|-----------------|------------|
| Quét QR báo **"Truy vấn mã QR không thành công"** | `BANK_ACCOUNT` là số của ngân hàng KHÁC với `BANK_NAME` (vd số VCB nhưng BIN MB) | Đảm bảo `BANK_ACCOUNT` đúng là TK của `BANK_NAME` |
| Khách CK rồi bot **không giao** | Tiền vào TK không phải TK Sepay giám sát | `BANK_ACCOUNT` (QR) phải = đúng TK Sepay đang theo dõi |
| `/sepay-webhook` trả **401** | `SEPAY_API_KEY` ở Sepay ≠ ở Railway | Đặt 2 nơi giống hệt nhau |
| Webhook gửi nhưng bot **bỏ qua** (Manual mode) | `SEPAY_API_KEY` env rỗng | Nạp `SEPAY_API_KEY` vào Railway → redeploy |
| GD vào **/unmatched** | Nội dung CK sai format `MUA TXNxxxxx` | Khách CK đúng nội dung; hoặc admin `/confirm TXNxxx` |
| Token lộ trong code | Hardcode `BOT_TOKEN` fallback trong `config.py` | Chỉ đọc từ env; revoke token cũ nếu đã lộ |

> **Lưu ý đổi ngân hàng:** khi chuyển từ VCB sang MB phải sửa ĐỒNG BỘ `BANK_NAME`, `BANK_ACCOUNT` (env + default code), xóa env VCB cũ (`VCB_EMAIL_SECRET`), và webhook Sepay trỏ đúng TK MB.

---

## 9. Bảo mật (bắt buộc)

- Repo **PRIVATE**. Không commit `.env`, không hardcode token/secret trong code.
- Token/API key lộ → **revoke ngay**: BotFather `/revoke` cho bot; Sepay regenerate API key; cập nhật env Railway → redeploy.
- `BASE_URL` luôn **https://**.
- DB chứa `chat_id` khách = dữ liệu cá nhân, đối xử cẩn trọng; backup định kỳ.

---

## 10. Vận hành — lệnh admin

| Lệnh | Tác dụng |
|------|----------|
| `/confirm TXNxxx` | Xác nhận đơn thủ công (khi Sepay lỗi/delay) → giao link ngay |
| `/unmatched` | Xem GD không khớp (sai tiền/sai mã) |
| `/set_link <sku> <url>` | Cập nhật link Drive |
| `/sale_stats` | Doanh số theo SKU |
| `/admin` | Bảng quản trị (nút bấm) |

---

## 11. Troubleshooting nhanh

- **Bot không trả lời:** Railway logs có exception? `getWebhookInfo` `last_error_message` null? Restart service.
- **Webhook không trigger:** Sepay → tab "Lịch sử gửi" xem có đẩy không; kiểm tra liên kết MB còn active.
- **Khớp nhưng không giao link:** Railway logs tìm mã đơn; kiểm tra link Drive đã set (`config.py` hoặc `/set_link`).

---

## Phụ lục — hiện trạng triển khai (2026-05-24)

- Bot: repo `ecosyntech68vn/bot-aithucchien` (private), Railway domain `bot-aithucchien-production-ee5f.up.railway.app`.
- Ngân hàng: **MB Bank · 3100181888868 · TA QUANG THUAN**. Đã xóa cấu hình VCB cũ.
- Webhook Sepay "Bot AI Thực Chiến" active, auth API Key, lọc Tiền vào. Bot ở chế độ AUTOMATIC.
- Đã verify: thiếu tiền → cảnh báo; đủ tiền → tự giao link.
