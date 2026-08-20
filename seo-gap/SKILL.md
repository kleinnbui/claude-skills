---
name: seo-gap
description: Phân tích khoảng cách cạnh tranh ở cấp cụm từ khóa để trả lời vì sao trang chưa lên top và cần làm gì để lên. Crawl trang mình cùng toàn bộ top SERP, đo 15 chỉ số so sánh được, dựng ma trận mật độ cụm từ, phát hiện nhiều trang nội bộ tranh nhau, rồi xuất một trong hai đầu ra: outline viết lại có nhãn GIỮ/SỬA/MỚI, hoặc phân vai lại cluster kèm việc tối ưu. Chạy nhiều cụm song song.
---

# SEO Gap — phân tích khoảng cách để lên top

Skill này trả lời câu hỏi **"vì sao trang chưa lên top và cần làm gì để lên"**.

Khác với `/seo-doctor` (chẩn đoán sự cố — vì sao tụt). Ở đây không có triệu chứng để kiểm chứng,
không có giả thuyết để loại trừ. Đây là **đo, so sánh, rồi đề xuất**.

Mọi con số phải đo trực tiếp từ HTML thô của trang mình và của toàn bộ đối thủ đang top.
Không ước lượng, không dùng số từ công cụ bên thứ ba trừ khi nói rõ nguồn.

---

## Nguyên tắc bất di bất dịch

1. **Đo trực tiếp, không ước lượng.** Mỗi con số phải truy được về một lần crawl cụ thể,
   ghi rõ ngày crawl.
2. **Luôn ghi nhận điểm mạnh trước khi nêu vấn đề.** Không xác định được thế mạnh thì không
   kết luận được nên viết lại hay chỉ cần tối ưu. Đây là lỗi hay gặp nhất.
3. **Mỗi vấn đề phải kèm số của đối thủ để so.** "Ảnh chưa tối ưu" là câu vô giá trị.
   "130 ảnh mà chỉ 23 lazy, 0 srcset, trong khi Neohouse 148 ảnh có 128 lazy và 128 srcset"
   mới là bằng chứng.
4. **Không đề xuất viết lại khi nội dung đã mạnh.** Trang đã nằm nhóm mạnh nhất SERP mà vẫn
   không lên được thì nguyên nhân nằm chỗ khác — thường là nhiều trang nội bộ tranh nhau.
5. **Phân biệt lỗi cấp trang với lỗi cấp template.** Cùng một lỗi xuất hiện ở nhiều trang
   thì phải nói rõ đây là lỗi hệ thống, xử lý một lần cho toàn site.
6. **Không emoji** trong mọi output.
7. **Không tự sửa website.** Chỉ phân tích và bàn giao.

---

## Luồng 7 pha

| Pha | Tên | Rules cần đọc | Chạy song song |
|---|---|---|---|
| 0 | Nhận đầu vào và kiểm dữ liệu | — | Không, chạy một lần |
| 1 | Xác định tập đối thủ | `positioning.md` mục 1 | Không |
| 2 | Crawl và đo | `metrics.md` | Có, mỗi cụm một subagent |
| 3 | Xác định vị thế và chọn đầu ra | `positioning.md` | Có |
| 4 | Phân tích: mạnh, yếu, gap | `positioning.md`, `cluster.md` | Có |
| 5 | Dựng đầu ra A hoặc B | `outline.md` hoặc `cluster.md` | Có |
| 6 | Xuất báo cáo | `report.md` | Không, gom kết quả |

Nhiều cụm thì pha 2-5 chạy song song, mỗi cụm một subagent độc lập. Pha 0, 1, 6 chạy một lần.

### Pha 0 — Nhận đầu vào và kiểm dữ liệu

Cần đủ ba thứ cho mỗi cụm:

| Bắt buộc | Ghi chú |
|---|---|
| Trang đích của mình | URL đầy đủ. Chưa có trang thì đây là trường hợp "cần tạo mới", báo ngay |
| Danh sách từ khóa mục tiêu | 2-5 từ khóa, gồm cả biến thể đảo trật tự. Biến thể đảo hay bị bỏ sót và là nguyên nhân trực tiếp khiến từ khóa đó không lên |
| Tập đối thủ đang top | File check top có SERP đầy đủ, hoặc để skill tự tra qua Chrome MCP |

Nên có: vùng địa lý đo, và ghi chú về ưu tiên kinh doanh của cụm này.

**Nhận nhiều cụm**: người dùng đưa danh sách. Xác nhận lại toàn bộ danh sách trước khi chạy,
kèm ước lượng số trang sẽ crawl (mỗi cụm khoảng 8-10 trang).

**Kiểm tra thừa kế từ `/seo-doctor`**: nếu `~/.claude/skills/seo-doctor/cases/<domain>/` tồn tại,
đọc `profile.md` để lấy bối cảnh dự án và đối thủ đã biết. Không hỏi lại thứ đã có.

### Pha 1 — Xác định tập đối thủ

Lấy toàn bộ domain đang chiếm top 10 cho từng từ khóa mục tiêu, gộp lại thành tập duy nhất.
Chi tiết ở `positioning.md` mục 1.

Tập này thường 6-8 trang. Trên 12 trang thì cắt còn top 8 theo tần suất xuất hiện,
và ghi rõ đã cắt.

### Pha 2 — Crawl và đo

Crawl HTML thô của: trang mình, toàn bộ đối thủ, và **toàn bộ trang cùng chủ đề trên domain mình**
(để bắt cannibalization ở pha 4).

Đo 15 chỉ số theo `metrics.md`. Mọi chỉ số phải đo được, không có chỉ số định tính.

Ghi ngày crawl. Báo cáo phải nêu ngày này.

### Pha 3 — Xác định vị thế

Đây là pha quyết định toàn bộ phần còn lại. Ba vị thế, ba loại đầu ra khác nhau:

| Vị thế | Điều kiện | Đầu ra |
|---|---|---|
| Yếu hơn | Thua nhóm top ở đa số chỉ số nội dung | **A** — outline viết lại có nhãn |
| Ngang hoặc mạnh hơn | Nằm nhóm mạnh nhất ở các chỉ số nội dung chính | **B** — phân vai cluster và tối ưu, không viết lại |
| Hỗn hợp | Mạnh ở nội dung, yếu ở kỹ thuật hoặc ngược lại | **B** cho phần mạnh, bổ sung mục riêng cho phần yếu |

Cách chấm điểm cụ thể ở `positioning.md` mục 2. Không được chọn đầu ra theo cảm tính.

### Pha 4 — Phân tích

Ba việc, theo đúng thứ tự:

1. **Điểm mạnh đang có** — 4-6 mục, mỗi mục kèm số của mình và số của đối thủ để so.
   Làm trước, không làm sau. Danh sách này quyết định cái gì được giữ nguyên.
2. **Vấn đề, xếp theo mức tác động** — NGHIÊM TRỌNG / TÁC ĐỘNG CAO / TRUNG BÌNH / THẤP.
   Mỗi vấn đề: số của mình, số của đối thủ, và vì sao nó cản việc lên top.
3. **Gap SERP** — mục mà không đối thủ nào trong top 3 có. Đây là cơ hội chiếm đoạn trích nổi bật.

Chạy `cluster.md` để bắt nhiều trang nội bộ tranh nhau. Phát hiện ra thì đây thường là
vấn đề mức NGHIÊM TRỌNG, đứng đầu danh sách.

### Pha 5 — Dựng đầu ra

**Đầu ra A** (`outline.md`): outline H2/H3 đầy đủ, mỗi mục gắn nhãn GIỮ / SỬA / MỚI / GAP SERP /
BRAND, kèm độ dài mục tiêu, số ảnh, và lý do dựa trên số của đối thủ.

**Đầu ra B** (`cluster.md`): bảng phân vai lại các trang trong cluster, kèm việc cụ thể cho
từng trang và hướng nối link.

Cả hai đầu ra đều kèm: lớp meta (title, description, URL, H1), bộ FAQ hiển thị thật,
kế hoạch ảnh, structured data cần sửa, và checklist triển khai.

### Pha 6 — Xuất báo cáo

Theo `report.md`. Một file HTML cho mỗi cụm, lưu tại
`~/html/seo-gap-<domain>-<slug-cụm>-<YYYYMMDD>.html`.

Nhiều cụm thì thêm một trang tổng hợp so sánh mức ưu tiên giữa các cụm.

---

## Nối với /seo-doctor

Skill này nhận bàn giao từ `/seo-doctor` khi bên đó kết luận:

| Giả thuyết bên seo-doctor | Nghĩa là |
|---|---|
| H25 — đã index nhưng không lên top | Đúng phạm vi skill này |
| H14 — nội dung mỏng hoặc lỗi thời | Đúng phạm vi, chạy để biết mỏng ở đâu và cần thêm gì |
| H16 — thiếu trang đích | Chạy để dựng outline cho trang mới |
| H11 — nhiều trang tranh nhau | Chạy để phân vai lại bằng số liệu mật độ |

Khi nhận bàn giao: đọc `~/.claude/skills/seo-doctor/cases/<domain>/` để lấy bối cảnh,
không hỏi lại. Kết quả phân tích ghi ngược vào `findings/` của case đó.

Dùng chung hai file rules của seo-doctor:
- `~/.claude/skills/seo-doctor/rules/evidence.md` — chuẩn trích dẫn số và chuẩn trình bày.
- `~/.claude/skills/seo-doctor/rules/data-quality.md` mục 3 — độ tin cậy.

---

## Ranh giới

| Tình huống | Chuyển sang |
|---|---|
| Trang đang tụt hạng, cần biết vì sao | `/seo-doctor` |
| Cần báo cáo traffic định kỳ | `/seo-analyst` |
| Traffic tốt nhưng không ra đơn | `/cro-analyst` |

Skill này không xử lý sự cố. Trang vừa tụt mạnh thì chạy `/seo-doctor` trước —
phân tích khoảng cách trên một trang đang có sự cố kỹ thuật là lãng phí.
