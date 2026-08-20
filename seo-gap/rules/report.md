# Cấu trúc báo cáo

Dùng ở pha 6.

Một file HTML cho mỗi cụm từ khóa, lưu tại
`~/html/seo-gap-<domain>-<slug-cụm>-<YYYYMMDD>.html`.

Nhiều cụm thì thêm một trang tổng hợp:
`~/html/seo-gap-<domain>-tong-hop-<YYYYMMDD>.html`.

Style: template `templates/report.html` tự chứa toàn bộ CSS, không phụ thuộc thư viện ngoài.
Không emoji. Không dùng dòng nhãn nhỏ viết hoa phía trên tiêu đề.

Chuẩn trích dẫn số và chuẩn trình bày: theo
`~/.claude/skills/seo-doctor/rules/evidence.md`.

---

## 1. Khối đầu trang — bắt buộc cho cả hai loại đầu ra

| Thành phần | Nội dung |
|---|---|
| Tiêu đề | Tên cụm từ khóa |
| Câu mô tả phạm vi | URL trang mình, số URL đối thủ đã so, ngày crawl. Bắt buộc ghi "số liệu lấy từ crawl HTML thô ngày [X]" |
| Danh sách từ khóa mục tiêu | Liệt kê đầy đủ, kể cả biến thể đảo trật tự |
| Bốn ô chỉ số nổi bật | Xem bên dưới |
| Mục lục | Các mục có trong tài liệu |

**Bốn ô chỉ số nổi bật** khác nhau theo loại đầu ra:

| | Đầu ra A (viết lại) | Đầu ra B (tối ưu) |
|---|---|---|
| Ô 1 | Độ dài mục tiêu, kèm số hiện tại | Vị thế hiện tại, một câu |
| Ô 2 | Số ảnh mục tiêu, kèm số hiện tại | Rào cản số 1, một câu có số |
| Ô 3 | Cấu trúc mục tiêu | Rào cản số 2, một câu có số |
| Ô 4 | Số mục mới hoàn toàn | Từ khóa yếu nhất, kèm số |

Bốn ô này phải đọc được trong 10 giây và nói đúng bản chất vấn đề.

## 2. Mục 1 — Hiện trạng trang

Hai phần, đúng thứ tự này, không đảo:

**Điểm mạnh đang có** — 4-6 mục. Mỗi mục: tên ngắn, rồi số của mình so với số của đối thủ cụ thể.

Ví dụ đúng: "130 ảnh nội dung, hạng 2 SERP. Chỉ sau Neohouse (148), hơn Duraflex (80),
3B Design (56), TOSTEM (34). Poshaco chỉ có 9 ảnh mà vẫn top 3."

Câu cuối trong ví dụ trên là kiểu quan sát có giá trị nhất — nó vừa ghi nhận thế mạnh
vừa cảnh báo rằng thế mạnh đó không phải yếu tố quyết định.

**N vấn đề, xếp theo mức tác động** — bốn mức: NGHIÊM TRỌNG, TÁC ĐỘNG CAO, TÁC ĐỘNG TRUNG BÌNH,
TÁC ĐỘNG THẤP.

Mỗi vấn đề gồm:
- Tiêu đề một dòng, nêu đúng bản chất.
- Số của mình.
- Số của đối thủ để so.
- Một câu giải thích vì sao điều này cản việc lên top.
- Khối bằng chứng dạng chữ đều khi cần — dòng lệnh, dãy số so sánh, danh sách URL.

Vấn đề nào là lỗi cấp template thì ghi rõ ngay tại đó, kèm câu "nên xử lý một lần cho toàn site".

## 3. Mục 2 — Vấn đề trọng tâm

Chỉ có khi phát hiện nhiều trang nội bộ tranh nhau. Nội dung theo `cluster.md`:
bảng đo, ba dấu hiệu xác nhận, giải thích vì sao đây là vấn đề chứ không phải cluster tốt,
và bảng phân vai lại.

Kết thúc mục này bằng một câu chốt rõ ràng về việc có cần gộp hay xóa trang nào không.

## 4. Mục 3 — So sánh toàn bộ trang trong SERP

Hai bảng.

**Bảng chỉ số**: dòng đầu là trang của mình, các dòng sau là đối thủ.
Cột theo 15 chỉ số ở `metrics.md`, chọn 8-10 cột quan trọng nhất với cụm này.

**Bảng mật độ cụm từ**: cụm × domain, theo `metrics.md` mục 2.

Dưới mỗi bảng có 2-3 câu đọc bảng, chỉ ra điều quan trọng nhất. Không để bảng đứng trần.

## 5. Mục 4 — Mổ xẻ từng đối thủ

Mỗi đối thủ một khối, theo `positioning.md` mục 4: họ mạnh nhất ở đâu, yếu ở đâu, chỗ mình chen vào.

Trang ngắn mà vẫn top 3 thì phân tích kỹ hơn các trang khác.

## 6. Mục 5 trở đi — Phần đề xuất

Khác nhau theo loại đầu ra.

**Đầu ra A** — theo `outline.md`:
lớp meta, outline chi tiết H2/H3 có nhãn, bộ FAQ, kế hoạch ảnh và alt text,
internal link và anchor, structured data cần sửa, checklist theo đợt, đối chiếu trước và sau.

**Đầu ra B** — theo `cluster.md` mục 6:
lớp meta và định vị lại cluster, bổ sung nội dung có mục tiêu, bộ FAQ,
ảnh và tối ưu tải, structured data cần sửa, checklist theo đợt.

Cả hai đều kết thúc bằng checklist triển khai theo đợt.

## 7. Trang tổng hợp khi chạy nhiều cụm

Bảng so sánh giữa các cụm, mỗi cụm một dòng:

| Cột | Nội dung |
|---|---|
| Cụm | Tên và link tới báo cáo riêng |
| Trang đích | URL |
| Vị thế | Mạnh / Ngang / Yếu / Hỗn hợp |
| Loại đầu ra | A hoặc B |
| Rào cản chính | Một câu có số |
| Khả năng lên top | Khả thi cao / bình thường / không khả thi, theo `positioning.md` mục 2 bước 4 |
| Công sức | Ước lượng |
| Thứ tự đề nghị | Số thứ tự |

Thứ tự đề nghị xếp theo: khả năng lên top trước, rồi tới công sức thấp trước.
Cụm không khả thi xếp cuối, kèm ghi chú nên chuyển hướng sang truy vấn nào.

Dưới bảng: một đoạn ngắn nêu các lỗi cấp template xuất hiện ở nhiều cụm — đây là việc
nên làm một lần cho toàn site thay vì làm riêng từng cụm.

## 8. Ghi ngược vào case file của seo-doctor

Dự án đã có `~/.claude/skills/seo-doctor/cases/<domain>/` thì ghi thêm vào
`findings/<YYYY-MM-DD>-gap-<slug-cụm>.md`, gồm: vị thế, rào cản chính, việc đã đề xuất,
và mốc kiểm chứng.

Mốc kiểm chứng lấy độ trễ từ `~/.claude/skills/seo-doctor/rules/baseline.md` mục 4 —
tối ưu nội dung trang cũ cần 4-8 tuần mới ổn định để đánh giá.

Chưa có case file thì không tự tạo. Chỉ ghi khi seo-doctor đã dựng sẵn.

## 9. Bàn giao

Câu cuối phiên liệt kê: đường dẫn từng báo cáo, trang tổng hợp nếu có,
và các lỗi cấp template cần xử lý riêng.

Không tự sửa website, không tự đăng nội dung. Chỉ phân tích và bàn giao.
