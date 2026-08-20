# Cluster nội bộ và phân vai — đầu ra B

Dùng ở pha 4 và pha 5. Bắt buộc chạy khi vị thế là Mạnh hoặc Ngang mà trang vẫn không lên top.

**Khác biệt cốt lõi so với cách phát hiện thông thường**: ở đây phát hiện nhiều trang tranh nhau
bằng **mật độ cụm từ đo trên từng trang**, không phải bằng thứ hạng luân phiên. Cách này bắt
được vấn đề sớm hơn và chỉ ra chính xác trang nào đang lấn.

---

## 1. Tìm tập trang cùng chủ đề

Ba nguồn, gộp lại:
1. `site:domain.com <cụm chính>` qua Chrome MCP.
2. Sitemap, lọc theo mẫu đường dẫn liên quan.
3. Internal link trỏ ra từ trang đích và trỏ vào trang đích.

Kết quả thường 2-6 trang. Chỉ có một trang thì không có vấn đề cluster, ghi rõ và bỏ qua mục này.

## 2. Đo và lập bảng

Bảng bắt buộc, mỗi trang một dòng:

| Cột | Nội dung |
|---|---|
| URL | Đường dẫn |
| Vai khai báo | pillar hoặc con, theo cấu trúc link hiện tại |
| Title | Nguyên văn |
| Số từ | Đếm theo `metrics.md` |
| Mật độ cụm chính | Số lần cụm từ khóa chính xuất hiện |
| Vấn đề | Nêu cụ thể |

Ví dụ dạng bảng:

```
/mau-nha-cap-4-mai-thai-dep       pillar  6.853 từ  ×154  Trang cần lên top, bị 3 trang dưới cạnh tranh
/nha-cap-4-mai-thai-3-phong-ngu   con     5.976 từ  ×84   Dày ngang pillar, nhồi cụm chính dù chỉ nên nhắm nhánh "3 phòng ngủ"
/mau-nha-cap-4-mai-thai-8x12m     con     6.285 từ  ×77   Tương tự, title còn ghi năm cũ
/nha-mai-Thai                     mẹ      5.300 từ  ×20   Trang mẹ chủ đề; URL viết hoa
```

## 3. Ba dấu hiệu xác nhận có vấn đề

Thỏa mãn một dấu hiệu là đủ để kết luận.

| Dấu hiệu | Ngưỡng |
|---|---|
| Trang con dày ngang pillar | Số từ trang con đạt từ 80% số từ pillar trở lên |
| Trang con nhồi cụm chính nặng | Mật độ cụm chính của trang con đạt từ 50% của pillar trở lên |
| Title trùng cụm chính và trùng dạng | Hai title cùng dùng cụm chính ở đầu, cùng kiểu con số dẫn đầu |

**Cách diễn giải đúng**: một cluster lành mạnh có pillar rộng và các trang con hẹp, mỗi trang con
tập trung vào biến thể riêng. Trang con dày ngang pillar và dùng cụm chính gần bằng pillar nghĩa là
chúng đang tự ứng cử cho cùng truy vấn thay vì dồn tín hiệu về pillar.

**Không kết luận vội**. Trang con có lượng tìm riêng và nội dung tốt thì đây không phải lý do để
gộp hay xóa. Vấn đề nằm ở phân vai và mật độ, không nằm ở sự tồn tại của trang.

## 4. Phân vai lại

Bảng bắt buộc, mỗi trang một dòng: URL, vai mới, việc cụ thể.

Bốn vai:

| Vai | Khi nào | Việc |
|---|---|---|
| Pillar duy nhất | Trang đang có mật độ cụm chính cao nhất và đúng ý định của từ khóa mục tiêu | Giữ và mở rộng. Nhận link từ mọi trang còn lại với anchor đúng từ khóa mục tiêu |
| Trang con nhánh | Trang có biến thể riêng, có lượng tìm riêng | Giảm mật độ cụm chung, tăng mật độ cụm nhánh của mình. Thêm link về pillar, anchor là từ khóa mục tiêu, đặt trong 200 từ đầu |
| Trang mẹ chủ đề | Trang bao chủ đề rộng hơn | Đẩy trọng tâm sang chủ đề rộng, link xuống pillar bằng anchor đúng |
| Gộp vào trang khác | Chỉ khi trang không có lượng tìm riêng và nội dung trùng lặp thật sự | 301 về trang giữ lại, nêu rõ lý do |

**Mặc định là không gộp, không xóa.** Chỉ đề xuất gộp khi trang thực sự không có lượng tìm riêng.
Phân vai và nối link đúng chiều là việc sửa nội dung nhẹ, không phải tái cấu trúc site —
nói rõ điều này để người thực thi không sợ.

**Quy tắc chọn pillar**: ưu tiên trang đang có mật độ cụm chính cao nhất và đang xếp hạng tốt nhất.
Trái ngược nhau thì ưu tiên trang đang xếp hạng, trừ khi trang kia là trang thương mại có giá trị
chuyển đổi cao hơn — khi đó nêu rõ đánh đổi để người dùng quyết.

## 5. Kế hoạch nối link

Bảng: trang nguồn, trang đích, anchor, vị trí đặt.

Quy tắc:
- Anchor phải là **nguyên văn từ khóa mục tiêu** của trang đích, không dùng "xem thêm", "tại đây".
- Link từ trang con về pillar đặt trong 200 từ đầu, không đặt ở chân bài.
- Mỗi trang con trỏ về pillar đúng một link với anchor chính. Nhồi nhiều link cùng anchor
  không tăng hiệu quả.
- Pillar trỏ xuống từng trang con bằng anchor là biến thể riêng của trang đó.

## 6. Việc kèm theo cho đầu ra B

Đầu ra B không chỉ có phân vai. Kèm bốn nhóm việc, mỗi nhóm chỉ đưa vào khi có bằng chứng số:

| Nhóm | Khi nào đưa vào | Nội dung |
|---|---|---|
| Bổ sung có mục tiêu | Có ô mật độ thấp bất thường trong ma trận | Bổ sung đúng cụm đó vào title, H1, mở bài, và một H2. Không viết lại cả trang |
| Chiều sâu chuyên môn | Có cụm chuyên môn mà mọi đối thủ nhắc nhiều còn mình gần như không | Thêm một H2 về chủ đề đó, nêu rõ đối thủ nào nhắc bao nhiêu lần |
| Kỹ thuật | Đo được vấn đề ảnh, schema, URL | Xem `report.md` mục kế hoạch ảnh và structured data |
| Độ tươi | dateModified cũ hơn đối thủ top | Cập nhật nội dung và ngày, sửa năm trong title nếu còn ghi năm cũ |

## 7. Lỗi cấp template

Cùng một lỗi xuất hiện trên nhiều trang trong cluster thì đây là lỗi cấp template, không phải
cấp bài viết. Phải nói rõ và đề xuất xử lý một lần cho toàn site.

Ba lỗi hay gặp ở cấp template:
- Schema khai nội dung không tồn tại trong HTML.
- Quy ước URL không nhất quán, ví dụ chữ hoa trong slug và chuyển hướng ngược chiều.
- Ảnh không có lazy-load hoặc srcset trên mọi trang.

Phát hiện lỗi cấp template thì ghi vào một mục riêng trong báo cáo, tách khỏi việc của cụm này.
