# Bộ chỉ số đo

Dùng ở pha 2. Mọi chỉ số đo trực tiếp từ HTML thô, không ước lượng, không lấy từ công cụ
bên thứ ba trừ khi ghi rõ nguồn.

Đo cho: trang mình, toàn bộ đối thủ đang top, và toàn bộ trang cùng chủ đề trên domain mình.

---

## 1. Mười lăm chỉ số bắt buộc

| # | Chỉ số | Cách đo | Dùng để |
|---|---|---|---|
| 1 | Số từ body | Đếm từ trong phần nội dung chính, loại bỏ menu, chân trang, thanh bên | So độ dày nội dung |
| 2 | Số ảnh nội dung | Đếm thẻ `img` trong phần nội dung chính, loại ảnh giao diện và biểu tượng | Nhóm truy vấn mẫu nhà, sản phẩm thì đây là chỉ số quan trọng nhất |
| 3 | Ảnh lazy-load | Đếm `loading="lazy"` hoặc thuộc tính lazy của thư viện | Tốc độ tải |
| 4 | Ảnh có srcset | Đếm thẻ `img` có `srcset` | Tối ưu ảnh theo màn hình |
| 5 | Ảnh WebP | Đếm ảnh định dạng WebP hoặc AVIF | Dung lượng |
| 6 | Dung lượng HTML | Kích thước file HTML thô, tính bằng KB | Chỉ báo tổng về độ nặng trang |
| 7 | Số H2 và H3 | Đếm riêng từng cấp, ghi dạng `H2/H3` | So độ chi tiết cấu trúc |
| 8 | FAQ | Ba trạng thái: không có / chỉ có trong schema / có render thật trong HTML | Bắt lỗi khai schema không tồn tại |
| 9 | dateModified | Đọc từ schema hoặc thẻ meta | So độ tươi với đối thủ |
| 10 | Số internal link | Đếm link trỏ về cùng domain trong phần nội dung | Sức mạnh liên kết nội bộ |
| 11 | Hạ tầng chuyển đổi | Có form, hotline, nút gọi hành động không | Phân biệt trang thương mại với trang thông tin |
| 12 | Title, description, H1, URL | Lấy nguyên văn | Lớp meta, và kiểm từ khóa có trong URL không |
| 13 | Số mục mẫu hoặc biến thể phủ | Đếm H3 thuộc nhóm liệt kê mẫu, phân theo chiều | Đo độ phủ truy vấn phụ |
| 14 | Structured data | Liệt kê loại schema khai báo, và đối chiếu với nội dung render thật | Bắt lỗi khai khống |
| 15 | Loại domain | Nhà sản xuất vật liệu / công ty xây dựng / kiến trúc / trang tổng hợp / sàn | Xác định Google đang ưu tiên loại domain nào ở SERP này |

## 2. Ma trận mật độ cụm từ

Chỉ số quan trọng nhất của toàn bộ skill. Đây là thứ chỉ ra nguyên nhân trực tiếp và đo được.

**Cách dựng**: bảng cụm từ × domain. Mỗi ô là số lần cụm đó xuất hiện trong nội dung chính.

Cụm cần đếm, theo thứ tự:
1. Từng từ khóa mục tiêu, **kể cả biến thể đảo trật tự**. Đây là chỗ hay bị bỏ sót nhất.
2. Các cụm phụ có lượng tìm mà đối thủ đang nhắm.
3. Các thuật ngữ chuyên môn của ngành liên quan tới chủ đề.

Ví dụ dạng bảng bắt buộc:

```
Cụm                        mình  đt1  đt2  đt3  đt4  đt5
nhà cấp 4 mái Thái          154  153  137   44   68   23
nhà mái Thái cấp 4           11    3    3   32    0    0
mẫu nhà cấp 4 mái Thái       22   41   86    6   46    5
ngói                          4   16    9   14    2    1
phong thủy                    2   10    2    5    0    0
```

**Cách đọc bảng:**
- Ô của mình thấp bất thường so với domain đang top cho chính từ khóa đó → nguyên nhân trực tiếp
  khiến từ khóa đó không lên. Nêu thẳng.
- Đối thủ có một cụm cao vượt trội → đó là nhánh họ đang nhắm. Xác định được ai nhắm nhánh nào.
- Cụm mà mọi đối thủ đều nhắc nhiều còn mình gần như không nhắc → thiếu chiều sâu chủ đề.

**Đặc biệt lưu ý biến thể đảo trật tự**: "nhà mái Thái cấp 4" và "nhà cấp 4 mái Thái" là hai
truy vấn khác nhau với lượng tìm khác nhau. Trang nhắc cụm thứ nhất 11 lần trong khi đối thủ
nhắc 32 lần và đặt vào cả title, H1, URL thì đó là lý do trực tiếp, không cần tìm đâu xa.

## 3. Chỉ số cấp cluster

Đo cho toàn bộ trang cùng chủ đề trên domain mình, dùng ở `cluster.md`.

| Chỉ số | Cách đo |
|---|---|
| Danh sách trang cùng chủ đề | Tìm bằng `site:` query, sitemap, và internal link từ trang đích |
| Số từ mỗi trang | Như chỉ số 1 |
| Mật độ cụm chính mỗi trang | Số lần cụm từ khóa chính xuất hiện trên từng trang |
| Title mỗi trang | Nguyên văn, để bắt trùng cụm chính và trùng con số |
| Vai trò khai báo | Trang nào là pillar, trang nào là con, theo cấu trúc link nội bộ |

## 4. Quy tắc đo

**Nội dung chính** nghĩa là phần bài viết, không tính menu, chân trang, thanh bên, khối liên quan.
Không tách được thì ghi rõ số đã bao gồm cả phần chung, và áp dụng cùng cách đo cho mọi trang
để so sánh vẫn có nghĩa.

**Áp dụng cùng một cách đo cho mọi trang trong tập.** Đo mình một kiểu, đo đối thủ kiểu khác
thì bảng so sánh vô giá trị.

**Ghi ngày crawl** vào báo cáo. Số liệu SERP thay đổi theo ngày.

**Trang đối thủ chặn crawl** thì ghi rõ, không bỏ qua im lặng. Ba trong tám trang chặn crawl
thì bảng so sánh chỉ còn năm dòng, và phải nói điều đó.

**Không suy diễn chỉ số không đo được.** Không có dữ liệu tốc độ tải thật thì không viết
"trang tải chậm" — chỉ viết những gì đo được: số ảnh, số lazy, dung lượng HTML.

## 5. Chỉ số nên đo thêm khi có điều kiện

Không bắt buộc, đo được thì tốt:

| Chỉ số | Lấy ở đâu |
|---|---|
| Vị trí hiện tại của từng từ khóa | File check top, hoặc GSC |
| Impressions và CTR của trang | GSC, dùng credential của `/seo-analyst` |
| Số domain trỏ tới trang | Ahrefs MCP |
| Trạng thái index | URL Inspection API |
| Lượng tìm từng từ khóa | Ahrefs MCP hoặc file người dùng cung cấp |

Có chỉ số vị trí thì báo cáo mạnh hơn nhiều — nêu được "đang ở vị trí 8, cần vượt ba trang này".
Không có thì phân tích vẫn chạy được, chỉ mất phần định vị chính xác.
