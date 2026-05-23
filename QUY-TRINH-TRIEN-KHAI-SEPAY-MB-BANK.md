# Quy trình triển khai bán hàng tự động với Sepay MB Bank

> Mình viết lại cái này như một bản chia sẻ kinh nghiệm — kể lại từng bước mình đã làm để dựng một con bot Telegram tự bán sản phẩm số: khách chuyển khoản xong là bot tự giao hàng, không cần ai ngồi canh. Bạn đọc xong là làm theo được, kể cả khi chưa rành kỹ thuật.
>
> *Lưu ý: tài liệu này cố tình KHÔNG ghi số tài khoản, tên thật hay ID Telegram của ai — chỗ nào cần thông tin riêng mình để dạng `<...>` để bạn tự điền.*

---

## Câu chuyện ngắn: mình muốn gì?

Hồi đầu bán hàng, cứ mỗi đơn là phải tự kiểm tra app ngân hàng xem khách chuyển chưa, đúng số tiền không, rồi mới gửi link sản phẩm. Bán vài đơn thì ổn, nhưng đông khách là loạn, lại còn dễ sót.

Nên mình dựng một hệ thống tự lo hết: **khách chuyển khoản → trong khoảng 30 giây bot tự gửi link tải cho khách**. Mình chỉ việc ngồi xem doanh số.

Sơ đồ cho dễ hình dung:

```
[1] Khách bấm /mua_combo trong bot Telegram
      ↓
[2] Bot tạo mã đơn (vd TXNxxxxx), gửi mã QR + số tài khoản + nội dung chuyển khoản
      ↓
[3] Khách chuyển vào tài khoản MB, ghi đúng nội dung "MUA TXNxxxxx"
      ↓
[4] MB Bank → Sepay (đang theo dõi tài khoản) → bắn về bot
      ↓
[5] Bot kiểm: đúng mã đơn? đủ tiền chưa?
      ↓
[6] Đủ rồi → bot tự gửi link Google Drive cho khách + báo cho mình
```

Có **bốn điều mình rút ra, sai một cái là tịt cả hệ thống**, nói trước để bạn khỏi vấp:

1. **Dùng MB Bank, đừng dùng Vietcombank.** Sepay nối thẳng API với MB nên biến động về sau 1–3 giây. VCB không có API, phải hứng qua SMS/email — rườm rà và hay lỗi.
2. **Tên ngân hàng và số tài khoản phải khớp nhau, và phải đúng tài khoản mà Sepay đang theo dõi.** Mình từng để lệch cái này, mã QR khách quét báo lỗi luôn (sẽ kể kỹ ở dưới).
3. **Cái "chìa khóa" API key phải giống hệt nhau ở hai đầu** — một bên là webhook trên Sepay, một bên là biến môi trường của bot. Lệch một ký tự là bot từ chối.
4. **Đừng bao giờ ghi cứng token/mật khẩu vào code.** Chỉ để ở biến môi trường thôi.

---

## Trước khi bắt đầu, chuẩn bị mấy thứ này

Làm một lần, để dành dùng mãi:

| Cần gì | Làm sao | Ghi chú |
|--------|---------|---------|
| Tài khoản MB Bank + Sepay | Mở MB Bank, đăng ký Sepay (sepay.vn), vào Sepay liên kết tài khoản MB | Liên kết xong, thử chuyển 1 ít tiền xem Sepay có thấy biến động không |
| Bot Telegram | Nhắn **@BotFather** → `/newbot` | Lấy được **token bot** (dạng `<số>:<chuỗi>`) — giữ kín |
| ID Telegram của bạn | Nhắn **@userinfobot** | Nó trả về một con số — đây là `<ADMIN_CHAT_ID>` để nhận thông báo |
| Link Google Drive sản phẩm | Mỗi sản phẩm một thư mục/ file, đặt "Ai có link đều xem được" | Lưu lại các URL |
| Repo GitHub (để **riêng tư**) + Railway | Tạo repo private cho code bot, đăng ký Railway đăng nhập bằng GitHub | Repo phải private vì có liên quan thanh toán |

---

## Bộ não của hệ thống: con bot trông như thế nào

Bot mình viết bằng Python (Flask). Mấy file chính:

| File | Lo việc gì |
|------|-----------|
| `app.py` | Nhận tín hiệu từ Telegram và từ Sepay; có sẵn các "cửa" (route) như `/sepay-webhook`, `/telegram-webhook`, `/` (kiểm tra sống) |
| `config.py` | Đọc toàn bộ cấu hình từ biến môi trường + danh sách sản phẩm (giá, link) |
| `db.py` | Lưu đơn đang chờ, ghi lại các giao dịch không khớp |

Cái "cửa" quan trọng nhất là nơi nhận tiền — **`/sepay-webhook`**. Mình để nó hoạt động thế này:

- Phải có "chìa khóa" đúng (Sepay gửi kèm header `Authorization: Apikey <chìa-khóa>`); sai hoặc thiếu là từ chối ngay.
- Nếu chưa khai báo chìa khóa → bot chạy **chế độ thủ công** (bỏ qua mọi giao dịch, mình tự xác nhận tay). Khai báo chìa khóa vào → bot chuyển sang **tự động**.
- Chỉ xử lý giao dịch **tiền vào**.
- Bot đọc nội dung chuyển khoản, dò mã đơn `MUA TXNxxxxx`, đối chiếu số tiền (cho lệch nhẹ ±100đ cho an toàn), rồi mới giao hàng.

---

## Đưa bot lên mây với Railway

Mình chọn Railway vì nó tự kéo code từ GitHub về chạy, có sẵn HTTPS, chi phí khởi điểm gần như bằng 0.

Các bước:

1. Railway → **New Project → Deploy from GitHub repo** → chọn repo bot (Railway tự nhận ra là Python).
2. Nếu bot dùng cơ sở dữ liệu, thêm **Postgres** vào cùng project.
3. Vào **Settings → Networking → Generate Domain** để lấy địa chỉ web của bot (dạng `https://<tên-app>.up.railway.app`) — gọi là `<BASE_URL>`.
4. Vào tab **Variables**, khai báo đầy đủ cấu hình (bảng dưới).
5. Mỗi lần đổi cấu hình hoặc đẩy code mới lên GitHub, Railway tự build lại.

Bảng cấu hình mình dùng (bạn thay phần `<...>` bằng thông tin của bạn):

| Biến | Điền gì | Ghi chú |
|------|---------|---------|
| `BOT_TOKEN` | `<token bot từ BotFather>` | Chỉ để ở đây, **không ghi vào code** |
| `ADMIN_CHAT_ID` | `<ID Telegram của bạn>` | Để bot báo cho bạn mỗi khi có đơn |
| `SEPAY_API_KEY` | `<chìa-khóa-tự-đặt>` | **Phải giống hệt** chìa khóa khai trong webhook Sepay |
| `BANK_ACCOUNT` | `<số tài khoản MB của bạn>` | Đúng tài khoản mà Sepay đang theo dõi |
| `BANK_NAME` | `MB Bank` | Viết đúng tên để hệ thống tạo QR đúng ngân hàng |
| `BANK_OWNER` | `<TÊN CHỦ TK, in hoa không dấu>` | Hiện trên QR cho khách |
| `BASE_URL` | `https://<tên-app>.up.railway.app` | Địa chỉ Railway vừa tạo |

> Mẹo kiểm tra: mở `<BASE_URL>/` trên trình duyệt, thấy báo `{"status":"ok",...}` là bot đã sống.

---

## Nối Sepay vào bot

Vào my.sepay.vn → **Tích hợp WebHooks → Tạo webhook**, điền qua 4 bước:

| Bước | Điền |
|------|------|
| 1. Cơ bản | Địa chỉ = `<BASE_URL>/sepay-webhook` · Loại = **Tiền vào** · Định dạng = **JSON** · bật "tự gửi lại khi lỗi" |
| 2. Tài khoản | Chọn "Tất cả tài khoản" (nếu bạn chỉ có một); để **tắt** mục "dùng để xác thực thanh toán" vì bot tự đối chiếu |
| 3. Bảo mật | Chọn **API Key**, dán đúng cái `<chìa-khóa>` đã đặt ở `SEPAY_API_KEY` |
| 4. Cảnh báo | Tùy chọn |

Nhớ nhé: **chìa khóa ở đây và `SEPAY_API_KEY` trên Railway phải y hệt nhau.**

---

## Nối Telegram vào bot

Mở trình duyệt, vào địa chỉ này (thay phần trong ngoặc):

```
https://api.telegram.org/bot<TOKEN>/setWebhook?url=<BASE_URL>/telegram-webhook
```

Thấy trả về `{"ok":true,...}` là xong. Muốn kiểm lại thì vào `.../getWebhookInfo`, mục `last_error_message` phải là `null`.

---

## Link sản phẩm cho khách

Hai cách (bot ưu tiên đọc trong cơ sở dữ liệu, không có thì lấy mặc định trong code):

- Ghi sẵn trong `config.py` — bền, không mất khi cơ sở dữ liệu reset. Mình thích cách này.
- Hoặc nhắn cho bot (với tư cách admin): `/set_link <mã sản phẩm> <link>`.

---

## Kiểm thử trước khi mở bán

Đừng vội mở bán. Mình luôn chạy đủ mấy bước này trước:

| Thử gì | Làm sao | Đúng thì thấy |
|--------|---------|---------------|
| Bot còn sống | Nhắn `/start` | Bot trả menu |
| Tạo đơn | `/mua_combo` | Ra mã `TXNxxxxx` + QR đúng ngân hàng |
| QR có quét được | Quét bằng app ngân hàng | App điền sẵn đúng tài khoản, số tiền, nội dung |
| **Thiếu tiền** | Chuyển ít hơn giá, ghi đúng mã | Bot nhắc khách "còn thiếu..." |
| **Đủ tiền** | Chuyển đúng, ghi đúng mã | Bot **tự gửi link** + báo cho bạn |

Mẹo test rẻ: chuyển đúng 1.000đ với mã đơn đúng → bot báo thiếu tiền. Vậy là biết đường dây MB → Sepay → bot đã thông mà không tốn tiền thật.

---

## Những cú vấp mình đã gặp (và cách tránh)

Phần này mới là quý nhất — toàn là chỗ mình từng mất thời gian:

| Hiện tượng | Lý do thật sự | Cách sửa |
|-----------|----------------|----------|
| Quét QR báo **"truy vấn mã QR không thành công"** | Số tài khoản và tên ngân hàng không cùng một nhà băng (vd số của ngân hàng A nhưng khai tên ngân hàng B) | Đảm bảo `BANK_ACCOUNT` đúng là tài khoản của `BANK_NAME` |
| Khách chuyển rồi mà bot **không giao** | Tiền vào một tài khoản, nhưng Sepay lại đang theo dõi tài khoản khác | Tài khoản trên QR phải đúng cái Sepay đang theo dõi |
| Webhook báo **401 (từ chối)** | Chìa khóa ở Sepay khác chìa khóa trên Railway | Đặt hai nơi giống hệt |
| Webhook gửi nhưng bot **làm ngơ** | Chưa khai `SEPAY_API_KEY` nên bot ở chế độ thủ công | Khai chìa khóa vào Railway rồi build lại |
| Giao dịch rơi vào danh sách "không khớp" | Khách ghi sai nội dung `MUA TXNxxxxx` | Dặn khách ghi đúng; hoặc admin xác nhận tay `/confirm TXNxxx` |
| Lỡ để token lộ trong code | Ghi cứng token trong file cấu hình | Chỉ đọc từ biến môi trường; nếu đã lỡ lộ thì thu hồi token ngay |

> Khi đổi ngân hàng (ví dụ từ VCB sang MB), nhớ sửa **đồng bộ** tên ngân hàng + số tài khoản ở mọi nơi (cả biến môi trường lẫn mặc định trong code), bỏ các cấu hình cũ không dùng, và chỉnh webhook Sepay trỏ đúng tài khoản mới. Mình từng quên một chỗ là khách quét QR ra sai ngân hàng.

---

## Giữ an toàn (đừng bỏ qua phần này)

- Repo để **riêng tư**. Không bao giờ đẩy file cấu hình chứa token lên Git, không ghi cứng token/mật khẩu trong code.
- Lỡ lộ token hay chìa khóa → **thu hồi ngay**: token bot thì `/revoke` trong BotFather; chìa khóa Sepay thì tạo lại; rồi cập nhật biến môi trường và build lại.
- Địa chỉ web luôn dùng **https**.
- Cơ sở dữ liệu có lưu thông tin khách (ID chat) — coi như dữ liệu cá nhân, sao lưu định kỳ và giữ kín.
- Hạn chế đưa số tài khoản, tên thật, ID Telegram vào tài liệu chia sẻ công khai — dễ bị lợi dụng.

---

## Vận hành hằng ngày — mấy lệnh admin hay dùng

| Lệnh | Tác dụng |
|------|----------|
| `/confirm TXNxxx` | Xác nhận đơn bằng tay (khi Sepay trễ) → giao link ngay |
| `/unmatched` | Xem các giao dịch không khớp (sai tiền/sai mã) |
| `/set_link <mã sp> <link>` | Cập nhật link sản phẩm |
| `/sale_stats` | Xem doanh số |
| `/admin` | Mở bảng quản trị (có nút bấm) |

---

## Khi có trục trặc, mình kiểm theo thứ tự này

- **Bot im lặng:** xem log Railway có lỗi không; kiểm `getWebhookInfo` của Telegram; khởi động lại service.
- **Webhook không nổ:** vào Sepay xem mục lịch sử gửi có đẩy không; kiểm tra tài khoản còn liên kết không.
- **Khớp rồi mà không giao link:** tìm mã đơn trong log; kiểm tra link sản phẩm đã cài chưa.

---

## Lời cuối

Cái hay nhất của hệ thống này không phải công nghệ, mà là nó **chạy thay mình lúc mình ngủ**. Lúc đầu thấy lằng nhằng, nhưng dựng xong một lần là dùng mãi, và nhân bản cho sản phẩm/kênh khác rất nhanh. Chúc bạn dựng mượt — vướng chỗ nào cứ lần theo bảng "những cú vấp" ở trên, mình gom hết kinh nghiệm đau thương vào đó rồi.

*— Chia sẻ từ EcoSynTech Global*
