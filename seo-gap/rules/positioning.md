# Xác định tập đối thủ, vị thế, và gap SERP

Dùng ở pha 1, 3, 4.

---

## 1. Xác định tập đối thủ

Nguồn theo thứ tự ưu tiên:

| Nguồn | Cách lấy | Ghi chú |
|---|---|---|
| File check top có SERP đầy đủ | Lấy toàn bộ domain trong top 10 của từng từ khóa mục tiêu | Chính xác nhất, có lịch sử nhiều mốc |
| Chrome MCP tra trực tiếp | Mở SERP thật cho từng từ khóa | **Đã kiểm chứng: không dùng được.** Google chặn, trang không tải xong sau 45 giây. Chrome MCP chỉ dùng để lấy HTML sau render của trang đối thủ |
| Ahrefs MCP | Lấy trang đang xếp hạng cho từ khóa | Dự phòng |

**Gộp thành tập duy nhất**: hợp tất cả domain xuất hiện, đếm số từ khóa mục tiêu mà mỗi domain
có mặt trong top 10.

**Cắt tập**: tập trên 12 trang thì giữ 8 trang theo thứ tự ưu tiên:
1. Trang có mặt trong top 3 của nhiều từ khóa mục tiêu nhất.
2. Trang có mặt trong top 10 của mọi từ khóa mục tiêu.
3. Trang cùng loại domain với mình.

Ghi rõ trong báo cáo là đã cắt, và cắt theo tiêu chí nào.

**Trang cần loại khỏi tập so sánh** (vẫn ghi nhận sự có mặt nhưng không đưa vào bảng đo):
diễn đàn, mạng xã hội, sàn thương mại điện tử, video. Chúng khác loại nội dung nên so số từ
và số ảnh không có nghĩa. Tỷ lệ loại này trong top 10 cao thì đó là phát hiện riêng —
Google đang hiểu truy vấn theo hướng khác, nêu ở phần gap.

**Ghi nhận loại domain** của từng trang trong tập (chỉ số 15 ở `metrics.md`). Nếu top 3 toàn
một loại domain và mình khác loại, đây là thông tin quan trọng cho phần đánh giá khả năng lên top.

---

## 2. Chấm điểm vị thế

Không chọn đầu ra theo cảm tính. Chấm theo bảng, rồi mới chọn.

### Bước 1 — Xếp hạng mình trong tập ở từng chỉ số nội dung

Sáu chỉ số nội dung dùng để chấm:

| # | Chỉ số | Trọng số |
|---|---|---|
| 1 | Số từ body | 1 |
| 2 | Số ảnh nội dung | 1 |
| 3 | Mật độ cụm chính | 2 |
| 4 | Số H2 và H3 | 1 |
| 5 | Số mục mẫu hoặc biến thể phủ | 2 |
| 6 | Độ phủ các cụm phụ trong ma trận mật độ | 1 |

Mỗi chỉ số: xếp hạng mình trong tập. Hạng 1-2 tính là mạnh, hạng giữa tính là ngang,
nửa dưới tính là yếu.

### Bước 2 — Quy ra vị thế

| Vị thế | Điều kiện | Đầu ra |
|---|---|---|
| **Mạnh** | Mạnh ở ≥4 trong 6 chỉ số, tính theo trọng số | B |
| **Ngang** | Không mạnh cũng không yếu ở đa số chỉ số | B, kèm bổ sung có chọn lọc |
| **Yếu** | Yếu ở ≥4 trong 6 chỉ số | A |
| **Hỗn hợp** | Mạnh rõ ở một nhóm chỉ số, yếu rõ ở nhóm khác | B cho phần mạnh, mục riêng cho phần yếu |

### Bước 3 — Kiểm tra chéo bắt buộc

Vị thế Mạnh hoặc Ngang mà trang vẫn không lên top thì **bắt buộc chạy `cluster.md`** trước khi
kết luận. Nguyên nhân gần như luôn nằm ở một trong ba chỗ:

| Khả năng | Dấu hiệu | Xử lý |
|---|---|---|
| Nhiều trang nội bộ tranh nhau | Có trang khác cùng domain nhồi cụm chính gần bằng hoặc hơn trang đích | Đầu ra B, phân vai lại |
| Một từ khóa mục tiêu bị bỏ trống | Ô của biến thể đó trong ma trận mật độ thấp bất thường | Bổ sung có mục tiêu, không viết lại cả trang |
| Rào cản kỹ thuật | URL không chứa từ khóa, ảnh không tối ưu, schema khai khống, nội dung chỉ render bằng JS | Mục riêng về kỹ thuật |

**Không được kết luận "cần viết thêm nội dung" khi vị thế là Mạnh.** Đó là đề xuất sai và tốn kém.

### Bước 4 — Đánh giá khả năng lên top

Trước khi đề xuất bất cứ việc gì, xét cấu trúc top 3 hiện tại:

| Cấu trúc top 3 | Kết luận |
|---|---|
| Cùng loại domain với mình, quy mô tương đương | Khả thi. Đề xuất bình thường |
| Có domain nhỏ hơn mình đang top | Khả thi cao. Phân tích kỹ trang đó — họ thắng bằng gì |
| Toàn sàn lớn, báo lớn, trang chính phủ | Không khả thi trực tiếp. Chuyển hướng sang truy vấn dài hơn, nói rõ lý do |
| Toàn diễn đàn, hỏi đáp, video | Google hiểu truy vấn theo hướng khác. Phải đổi loại nội dung trước khi bàn tới độ dày |

Trường hợp đáng chú ý nhất: **một trang nhỏ, ít nội dung mà vẫn top 3**. Ví dụ trang chỉ
2.208 từ và 9 ảnh nhưng vẫn top 3 trong khi mình 6.853 từ và 130 ảnh. Đây là bằng chứng mạnh
rằng độ dày không phải yếu tố quyết định ở truy vấn này — phải tìm xem họ có gì mà mình không có.
Thường là: đúng loại domain, đúng chiều sâu chuyên môn, hoặc một mục nội dung mà chỉ họ có.

---

## 2b. Cổng chặn trước khi chấm điểm — bắt buộc

**Không chấm vị thế khi đo được dưới 3 đối thủ.** Đây là cổng chặn quan trọng nhất của skill này.

Lý do: nhiều site hiện đại render nội dung bằng JavaScript, HTML thuần gần như rỗng.
Đo thật trên cụm "nhà cấp 4 mái Thái": 3 trong 4 đối thủ trả về 1, 15 và 17 từ trên HTML
nặng 287-338KB. Nếu vẫn chấm điểm, trang mình 5.408 từ sẽ thắng mọi chỉ số và hệ thống
kết luận "vị thế Mạnh, nội dung đã đủ, chỉ cần tối ưu" — sai hoàn toàn, vì thực ra
không đo được đối thủ nào.

`measure_pages.py` tự phát hiện: dưới 300 từ nội dung mà HTML trên 80KB thì đánh dấu
`js_suspected`, loại khỏi ma trận mật độ và khỏi tập chấm điểm, rồi trả `scoring_ready: false`.

**Ba cách xử lý khi cổng chặn bật:**

| Cách | Làm gì |
|---|---|
| Lấy HTML sau render | Dùng Chrome MCP mở từng URL trong `js_rendered_urls`, lấy nội dung sau khi chạy JS, đo lại |
| Đổi tập đối thủ | Chọn đối thủ khác trong top 10 mà crawl được |
| Dừng và báo | Không đủ đối thủ đo được thì nói thẳng: chưa đánh giá được vị thế, nêu rõ vì sao |

Không được chấm điểm rồi ghi chú nhỏ "một số đối thủ không đo được". Kết luận vị thế sai
dẫn tới chọn sai loại đầu ra, và đó là lỗi nghiêm trọng nhất của skill này.

**Trang đích của mình render bằng JS** thì script dừng hẳn — mọi chỉ số nội dung đều sai,
không có cách nào cứu ngoài việc lấy HTML sau render.

---

## 3. Phát hiện gap SERP

Gap SERP là mục nội dung mà **không đối thủ nào trong top 3 có**. Đây là cơ hội chiếm
đoạn trích nổi bật và tạo khác biệt.

**Cách tìm:**
1. Trích toàn bộ H2 và H3 của mọi trang trong tập.
2. Gom các mục cùng ý về một nhóm, đặt tên chuẩn hóa.
3. Lập bảng: nhóm mục × domain, đánh dấu có hoặc không.
4. Nhóm mục mà top 3 đều không có, nhưng hợp lý với ý định tìm kiếm → đây là gap.

**Ba loại gap theo giá trị:**

| Loại | Đặc điểm | Ví dụ |
|---|---|---|
| Gap thật | Không ai có, và người dùng thực sự cần | Bảng so sánh nhà chữ L với nhà ống và chữ U |
| Gap giả | Không ai có vì nó không liên quan tới ý định tìm kiếm | Lịch sử kiến trúc, quy định pháp lý chi tiết |
| Gap thương hiệu | Chỗ chèn được giải pháp của mình một cách tự nhiên | Mục nhược điểm và cách khắc phục, trong đó giải pháp là sản phẩm của mình |

Chỉ đề xuất gap thật và gap thương hiệu. Gap giả thì bỏ qua, không liệt kê cho đủ số.

**Kiểm tra ngược**: mục mà mọi đối thủ đều có mà mình không có thì không phải gap —
đó là thiếu sót, xếp vào danh sách vấn đề.

---

## 4. Mổ xẻ từng đối thủ

Với mỗi trang trong tập, viết một khối ngắn trả lời ba câu:

| Câu hỏi | Nội dung |
|---|---|
| Họ mạnh nhất ở đâu | Chỉ số nào họ đứng đầu, và họ nhắm nhánh truy vấn nào (đọc từ ma trận mật độ) |
| Họ yếu ở đâu | Chỗ mình vượt được, hoặc chỗ họ bỏ trống |
| Chỗ chen vào | Cụ thể mình làm gì để vượt trang này |

Không viết chung chung. Mỗi câu phải có số.

Đặc biệt phân tích kỹ: trang đứng đầu, và trang có vị thế yếu nhất mà vẫn nằm trong top 3.
Trang thứ hai cho biết yếu tố nào thực sự quyết định ở truy vấn này.
