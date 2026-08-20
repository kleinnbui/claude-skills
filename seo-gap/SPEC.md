# SEO Gap — Đặc tả hệ thống

Tài liệu triển khai. Phiên bản 1.0 — 01/08/2026.

Đọc hết tài liệu này là đủ để dựng lại toàn bộ hệ thống.
Skill này là phần bổ trợ cho `seo-doctor`; hai hệ thống dùng chung một phần rules và case file,
nhưng luồng và đầu ra hoàn toàn khác nhau.

---

## Mục lục

| Phần | Nội dung | File rules |
|---|---|---|
| 0 | Tóm tắt cho người triển khai | — |
| 1 | Bối cảnh và ranh giới với seo-doctor | — |
| 2 | Kiến trúc | — |
| 3 | Luồng 7 pha | `SKILL.md` |
| 4 | Bộ chỉ số đo | `rules/metrics.md` |
| 5 | Tập đối thủ, vị thế, gap SERP | `rules/positioning.md` |
| 6 | Cluster nội bộ và phân vai — đầu ra B | `rules/cluster.md` |
| 7 | Outline nội dung — đầu ra A | `rules/outline.md` |
| 8 | Cấu trúc báo cáo | `rules/report.md` |
| 9 | Đặc tả 3 script | — |
| 10 | Tiêu chí nghiệm thu | — |
| 11 | Ràng buộc và điều cấm | — |

---

# 0. Tóm tắt cho người triển khai

**Sản phẩm**: skill Claude Code tên `seo-gap`, chạy trong hội thoại, phân tích khoảng cách
cạnh tranh ở cấp một cụm từ khóa và xuất kế hoạch để lên top.

**Câu hỏi nó trả lời**: vì sao trang chưa lên top, và cần làm gì để lên.
Không phải "vì sao tụt" — đó là việc của `seo-doctor`.

**Bốn thứ quyết định chất lượng, làm sai là hỏng:**

1. **Mọi con số đo trực tiếp từ HTML thô.** Không ước lượng, không lấy số từ công cụ bên thứ ba
   trừ khi ghi rõ nguồn. Đây là điều làm nên giá trị của bản phân tích — người đọc kiểm chứng được.

2. **Ghi nhận điểm mạnh trước khi nêu vấn đề.** Không xác định được thế mạnh thì không kết luận
   được nên viết lại hay chỉ cần tối ưu. Hệ thống chỉ tìm vấn đề sẽ luôn kết luận "viết thêm nội dung",
   kể cả khi nội dung đã mạnh nhất SERP.

3. **Ma trận mật độ cụm từ là chỉ số quan trọng nhất.** Bảng cụm từ × domain chỉ ra nguyên nhân
   trực tiếp và đo được. Ví dụ thật: cụm "nhà mái Thái cấp 4" xuất hiện 11 lần trên trang mình,
   32 lần trên trang đối thủ đang top và có trong cả title, H1, URL của họ. Đó là lý do từ khóa
   đó không lên, không cần tìm đâu xa.

4. **Hai loại đầu ra, chọn bằng cách chấm điểm chứ không bằng cảm tính.** Trang yếu hơn thì
   cần outline viết lại. Trang đã mạnh mà vẫn không lên top thì nguyên nhân nằm chỗ khác —
   thường là nhiều trang nội bộ tranh nhau — và đề xuất viết lại là sai và tốn kém.

**Công nghệ**: Claude Code skill (Markdown + Python scripts), Chrome MCP để tra SERP thật,
crawl HTML trực tiếp. Tùy chọn: Ahrefs MCP, credential GSC của `/seo-analyst`.

**Trạng thái**: đã hoàn tất. 5 file rules (nội dung trong tài liệu này), 3 script Python,
1 template HTML. Toàn bộ đã chạy thử trên dữ liệu thật — ma trận mật độ đo khớp chính xác
với bản phân tích thủ công đã có.

**Môi trường chạy**: dùng chung `~/.claude/skills/seo-analyst/.venv`. Script của seo-gap
import `common.py` từ `~/.claude/skills/seo-doctor/scripts/`.

---

# 1. Bối cảnh và ranh giới với seo-doctor

## 1.1 Vì sao tách riêng

`seo-doctor` xây quanh luồng giả thuyết → bằng chứng → loại trừ. Nó nhận một triệu chứng
(tụt top, tụt traffic) và tìm nguyên nhân.

Việc này khác về bản chất: không có triệu chứng để kiểm chứng, không có giả thuyết để loại trừ.
Đây là **đo, so sánh, rồi đề xuất**. Ép vào luồng 8 pha của seo-doctor sẽ làm méo cả hai.

## 1.2 Điểm nối

`seo-doctor` bàn giao sang `seo-gap` khi kết luận thuộc bốn giả thuyết:

| Giả thuyết bên seo-doctor | Nghĩa |
|---|---|
| H25 — đã index nhưng không lên top | Đúng phạm vi |
| H14 — nội dung mỏng hoặc lỗi thời | Chạy để biết mỏng ở đâu, cần thêm gì |
| H16 — thiếu trang đích | Chạy để dựng outline cho trang mới |
| H11 — nhiều trang tranh nhau | Chạy để phân vai lại bằng số liệu mật độ |

Cách bàn giao giống cách seo-doctor bàn giao H29 sang `/cro-analyst`: nêu lý do chuyển,
bàn giao số liệu đã thu thập, không bắt người dùng cung cấp lại.

## 1.3 Dùng chung

| Tài nguyên | Đường dẫn |
|---|---|
| Chuẩn trích dẫn số và chuẩn trình bày | `~/.claude/skills/seo-doctor/rules/evidence.md` |
| Độ tin cậy tổng | `~/.claude/skills/seo-doctor/rules/data-quality.md` mục 3 |
| Bảng độ trễ kỳ vọng | `~/.claude/skills/seo-doctor/rules/baseline.md` mục 4 |
| Hồ sơ dự án | `~/.claude/skills/seo-doctor/cases/<domain>/profile.md` |
| Ghi kết quả | `~/.claude/skills/seo-doctor/cases/<domain>/findings/` |

Case file thuộc quyền quản lý của `seo-doctor`. `seo-gap` chỉ đọc và ghi thêm vào `findings/`,
không tự tạo case file mới.

## 1.4 Hai bản phân tích mẫu

Chuẩn đầu ra của hệ thống. Team triển khai phải đọc cả hai trước khi bắt đầu.

| File | Loại đầu ra | Vị thế trang | Kết luận |
|---|---|---|---|
| `~/html/outline-nha-cap-4-chu-l-vinhtuong.html` | A | Yếu hơn đối thủ về nội dung | Viết lại: outline 7 H2 / 33 H3 có nhãn |
| `~/html/outline-nha-cap-4-mai-thai-vinhtuong.html` | B | Đã nằm nhóm mạnh nhất SERP | Không viết lại: phân vai 4 trang trong cluster + tối ưu ảnh + sửa schema |

Cùng một khung phân tích, hai kết luận trái ngược. Việc tự xác định được vị thế rồi mới chọn
loại đầu ra là phần khó nhất của hệ thống.

## 1.5 Phạm vi

**Trong phạm vi**: phân tích một hoặc nhiều cụm từ khóa, mỗi cụm gồm một trang đích và
2-5 từ khóa mục tiêu. Crawl và đo trang mình cùng toàn bộ đối thủ đang top. Xuất kế hoạch
và outline. Chạy nhiều cụm song song.

**Ngoài phạm vi**: chẩn đoán sự cố tụt hạng, nghiên cứu từ khóa từ đầu, viết nội dung thật,
sửa website, đăng bài.

---

# 2. Kiến trúc

## 2.1 Cây thư mục

```
~/.claude/skills/seo-gap/
├── SKILL.md                    điểm vào: nguyên tắc, luồng 7 pha, ranh giới
├── SPEC.md                     tài liệu này
├── rules/
│   ├── metrics.md              15 chỉ số + ma trận mật độ + quy tắc đo
│   ├── positioning.md          tập đối thủ, chấm điểm vị thế, gap SERP, mổ xẻ đối thủ
│   ├── cluster.md              cannibalization đo bằng mật độ, phân vai — đầu ra B
│   ├── outline.md              outline có nhãn, meta, FAQ, ảnh, checklist — đầu ra A
│   └── report.md               cấu trúc báo cáo hai loại + trang tổng hợp
├── scripts/
│   ├── fetch_serp.py           lấy tập đối thủ từ file check top hoặc SERP thật
│   ├── measure_pages.py        crawl và đo 15 chỉ số + ma trận mật độ
│   └── build_gap_report.py     sinh HTML
└── templates/
    └── report.html
```

## 2.2 Sơ đồ

```
Người dùng: "phân tích cụm X, Y, Z cho domain D"
   |
   v
/seo-gap (skill, hội thoại chính)
   |
   +-- pha 0-1  chạy một lần: nhận đầu vào, dựng tập đối thủ
   |
   +-- pha 2-5  chạy song song, mỗi cụm một subagent
   |      |
   |      +-- measure_pages.py   crawl mình + đối thủ + cluster nội bộ
   |      +-- rules/positioning  chấm điểm vị thế -> chọn A hoặc B
   |      +-- rules/cluster hoặc rules/outline
   |
   +-- pha 6    gom kết quả, sinh HTML từng cụm + trang tổng hợp
   |
   v
~/html/seo-gap-<domain>-<cụm>-<ngày>.html  (mỗi cụm)
~/html/seo-gap-<domain>-tong-hop-<ngày>.html
+ ghi vào seo-doctor/cases/<domain>/findings/
```

Toàn bộ logic phân tích nằm trong `rules/`. Script chỉ crawl, đếm, và render.

## 2.3 Bảy nguyên tắc bất di bất dịch

1. **Đo trực tiếp, không ước lượng.** Mỗi con số truy được về một lần crawl cụ thể, có ngày.
2. **Luôn ghi nhận điểm mạnh trước khi nêu vấn đề.**
3. **Mỗi vấn đề phải kèm số của đối thủ để so.**
4. **Không đề xuất viết lại khi nội dung đã mạnh.**
5. **Phân biệt lỗi cấp trang với lỗi cấp template.** Lỗi lặp ở nhiều trang thì xử lý một lần
   cho toàn site.
6. **Không emoji** trong mọi output.
7. **Không tự sửa website.** Chỉ phân tích và bàn giao.

---

# 3. Luồng 7 pha

| Pha | Tên | Rules | Song song |
|---|---|---|---|
| 0 | Nhận đầu vào và kiểm dữ liệu | — | Không |
| 1 | Xác định tập đối thủ | `positioning.md` mục 1 | Không |
| 2 | Crawl và đo | `metrics.md` | Có |
| 3 | Xác định vị thế và chọn đầu ra | `positioning.md` mục 2 | Có |
| 4 | Phân tích: mạnh, yếu, gap | `positioning.md`, `cluster.md` | Có |
| 5 | Dựng đầu ra A hoặc B | `outline.md` hoặc `cluster.md` | Có |
| 6 | Xuất báo cáo | `report.md` | Không |

## Pha 0 — Nhận đầu vào

Ba thứ bắt buộc cho mỗi cụm:

| Bắt buộc | Ghi chú |
|---|---|
| Trang đích | URL đầy đủ. Chưa có trang thì đây là trường hợp tạo mới, báo ngay và chuyển sang đầu ra A |
| Từ khóa mục tiêu | 2-5 từ khóa, **bắt buộc gồm cả biến thể đảo trật tự**. Biến thể đảo hay bị bỏ sót và là nguyên nhân trực tiếp khiến từ khóa đó không lên |
| Tập đối thủ | File check top có SERP đầy đủ, hoặc để skill tự tra qua Chrome MCP |

Nhận nhiều cụm: xác nhận lại danh sách trước khi chạy, kèm ước lượng số trang sẽ crawl
(mỗi cụm khoảng 8-10 trang, cộng 2-6 trang cluster nội bộ).

Kiểm tra `~/.claude/skills/seo-doctor/cases/<domain>/profile.md`. Có thì đọc để lấy bối cảnh
và danh sách đối thủ đã biết, không hỏi lại.

## Pha 1 — Tập đối thủ

Chi tiết ở phần 5 mục 5.1. Gộp toàn bộ domain trong top 10 của mọi từ khóa mục tiêu.
Trên 12 trang thì cắt còn 8, ghi rõ tiêu chí cắt.

Loại khỏi bảng đo: diễn đàn, mạng xã hội, sàn, video — khác loại nội dung nên so số không có nghĩa.
Tỷ lệ loại này cao trong top 10 là phát hiện riêng, nêu ở phần gap.

## Pha 2 — Crawl và đo

Crawl HTML thô của ba nhóm:
1. Trang đích của mình.
2. Toàn bộ đối thủ trong tập.
3. **Toàn bộ trang cùng chủ đề trên domain mình** — để bắt cannibalization ở pha 4.

Đo 15 chỉ số và dựng ma trận mật độ theo phần 4. Ghi ngày crawl.

Trang chặn crawl thì ghi rõ, không bỏ qua im lặng.

## Pha 3 — Chấm điểm vị thế

Chấm theo bảng ở phần 5 mục 5.2, không chọn theo cảm tính.

| Vị thế | Đầu ra |
|---|---|
| Yếu | A — outline viết lại |
| Mạnh hoặc Ngang | B — phân vai cluster và tối ưu |
| Hỗn hợp | B cho phần mạnh, mục riêng cho phần yếu |

**Kiểm tra chéo bắt buộc**: vị thế Mạnh hoặc Ngang mà trang vẫn không lên top thì phải chạy
phần 6 trước khi kết luận.

## Pha 4 — Phân tích

Ba việc, đúng thứ tự:
1. Điểm mạnh đang có — 4-6 mục, mỗi mục có số mình và số đối thủ.
2. Vấn đề xếp theo mức tác động — bốn mức.
3. Gap SERP — mục không đối thủ top 3 nào có.

Cộng: mổ xẻ từng đối thủ (phần 5 mục 5.4), và chạy phần 6 để bắt cluster.

## Pha 5 — Dựng đầu ra

Đầu ra A theo phần 7. Đầu ra B theo phần 6 mục 6.6.

Cả hai đều kèm: lớp meta, bộ FAQ hiển thị thật, kế hoạch ảnh, structured data cần sửa,
checklist triển khai theo đợt.

## Pha 6 — Xuất báo cáo

Theo phần 8. Một HTML mỗi cụm, cộng trang tổng hợp nếu chạy nhiều cụm.
Ghi ngược vào `findings/` của case file nếu có.

---

# 4. Bộ chỉ số đo

Nội dung phần này là file `rules/metrics.md`.

## 4.1 Mười lăm chỉ số bắt buộc

| # | Chỉ số | Cách đo | Dùng để |
|---|---|---|---|
| 1 | Số từ body | Đếm từ trong nội dung chính, loại menu, chân trang, thanh bên | So độ dày |
| 2 | Số ảnh nội dung | Đếm `img` trong nội dung chính, loại ảnh giao diện và biểu tượng | Truy vấn dạng mẫu thì đây là chỉ số quan trọng nhất |
| 3 | Ảnh lazy-load | Đếm `loading="lazy"` hoặc thuộc tính lazy của thư viện | Tốc độ tải |
| 4 | Ảnh có srcset | Đếm `img` có `srcset` | Tối ưu theo màn hình |
| 5 | Ảnh WebP | Đếm ảnh WebP hoặc AVIF | Dung lượng |
| 6 | Dung lượng HTML | KB của file HTML thô | Chỉ báo tổng về độ nặng |
| 7 | Số H2 và H3 | Đếm riêng, ghi dạng `H2/H3` | So độ chi tiết cấu trúc |
| 8 | FAQ | Ba trạng thái: không có / chỉ trong schema / có render thật | Bắt lỗi khai schema không tồn tại |
| 9 | dateModified | Từ schema hoặc thẻ meta | So độ tươi |
| 10 | Số internal link | Link cùng domain trong nội dung | Sức mạnh liên kết nội bộ |
| 11 | Hạ tầng chuyển đổi | Form, hotline, nút gọi hành động | Phân biệt trang thương mại với trang thông tin |
| 12 | Title, description, H1, URL | Nguyên văn | Lớp meta, kiểm từ khóa có trong URL không |
| 13 | Số mục mẫu hoặc biến thể phủ | Đếm H3 thuộc nhóm liệt kê, phân theo chiều | Độ phủ truy vấn phụ |
| 14 | Structured data | Loại schema khai báo, đối chiếu với nội dung render thật | Bắt lỗi khai khống |
| 15 | Loại domain | Nhà sản xuất / xây dựng / kiến trúc / tổng hợp / sàn | Google đang ưu tiên loại nào |

## 4.2 Ma trận mật độ cụm từ

Chỉ số quan trọng nhất của toàn hệ thống.

Bảng cụm từ × domain, mỗi ô là số lần cụm xuất hiện trong nội dung chính.

Cụm cần đếm:
1. Từng từ khóa mục tiêu, **kể cả biến thể đảo trật tự**.
2. Các cụm phụ có lượng tìm mà đối thủ đang nhắm.
3. Thuật ngữ chuyên môn của ngành liên quan tới chủ đề.

```
Cụm                        mình  đt1  đt2  đt3  đt4  đt5
nhà cấp 4 mái Thái          154  153  137   44   68   23
nhà mái Thái cấp 4           11    3    3   32    0    0
mẫu nhà cấp 4 mái Thái       22   41   86    6   46    5
ngói                          4   16    9   14    2    1
phong thủy                    2   10    2    5    0    0
```

Cách đọc:
- Ô của mình thấp bất thường so với domain đang top cho chính từ khóa đó → nguyên nhân trực tiếp.
- Đối thủ có một cụm cao vượt trội → đó là nhánh họ nhắm.
- Cụm mà mọi đối thủ đều nhắc nhiều còn mình gần như không → thiếu chiều sâu chủ đề.

**Biến thể đảo trật tự**: "nhà mái Thái cấp 4" và "nhà cấp 4 mái Thái" là hai truy vấn khác nhau
với lượng tìm khác nhau. Đây là chỗ hay bị bỏ sót nhất.

## 4.3 Chỉ số cấp cluster

| Chỉ số | Cách đo |
|---|---|
| Danh sách trang cùng chủ đề | `site:` query, sitemap, internal link |
| Số từ mỗi trang | Như chỉ số 1 |
| Mật độ cụm chính mỗi trang | Số lần cụm chính xuất hiện |
| Title mỗi trang | Nguyên văn, để bắt trùng cụm và trùng con số |
| Vai trò khai báo | pillar hay con, theo cấu trúc link |

## 4.4 Quy tắc đo

- **Nội dung chính** = phần bài viết, không tính menu, chân trang, thanh bên, khối liên quan.
  Không tách được thì ghi rõ và áp dụng cùng cách đo cho mọi trang.
- **Cùng một cách đo cho mọi trang trong tập.** Đo mình một kiểu, đo đối thủ kiểu khác thì
  bảng so sánh vô giá trị.
- **Ghi ngày crawl** vào báo cáo.
- **Trang chặn crawl** thì ghi rõ số trang đo được thực tế.
- **Không suy diễn chỉ số không đo được.** Không có dữ liệu tốc độ tải thật thì chỉ viết
  những gì đo được: số ảnh, số lazy, dung lượng HTML.

## 4.5 Chỉ số nên đo thêm khi có điều kiện

| Chỉ số | Lấy ở đâu |
|---|---|
| Vị trí hiện tại từng từ khóa | File check top hoặc GSC |
| Impressions và CTR của trang | GSC qua credential của `/seo-analyst` |
| Số domain trỏ tới trang | Ahrefs MCP |
| Trạng thái index | URL Inspection API |
| Lượng tìm từng từ khóa | Ahrefs MCP hoặc file người dùng |

Có chỉ số vị trí thì báo cáo mạnh hơn nhiều. Không có thì vẫn chạy được.

---

# 5. Tập đối thủ, vị thế, gap SERP

Nội dung phần này là file `rules/positioning.md`.

## 5.1 Xác định tập đối thủ

| Nguồn | Ưu tiên | Ghi chú |
|---|---|---|
| File check top có SERP đầy đủ | 1 | Chính xác nhất, có lịch sử |
| Chrome MCP tra SERP thật | 2 | Ghi rõ ngày tra và vùng địa lý |
| Ahrefs MCP | 3 | Dự phòng |

Gộp thành tập duy nhất, đếm số từ khóa mục tiêu mà mỗi domain có mặt trong top 10.

Trên 12 trang thì cắt còn 8 theo thứ tự: có mặt top 3 nhiều từ khóa nhất, có mặt top 10 mọi từ khóa,
cùng loại domain với mình. Ghi rõ đã cắt.

Loại khỏi bảng đo nhưng vẫn ghi nhận: diễn đàn, mạng xã hội, sàn, video.

## 5.2 Chấm điểm vị thế

**Bước 1** — xếp hạng mình trong tập ở sáu chỉ số nội dung:

| # | Chỉ số | Trọng số |
|---|---|---|
| 1 | Số từ body | 1 |
| 2 | Số ảnh nội dung | 1 |
| 3 | Mật độ cụm chính | 2 |
| 4 | Số H2 và H3 | 1 |
| 5 | Số mục mẫu hoặc biến thể phủ | 2 |
| 6 | Độ phủ cụm phụ trong ma trận | 1 |

Hạng 1-2 là mạnh, hạng giữa là ngang, nửa dưới là yếu.

**Bước 2** — quy ra vị thế:

| Vị thế | Điều kiện | Đầu ra |
|---|---|---|
| Mạnh | Mạnh ở ≥4 trong 6 chỉ số, tính theo trọng số | B |
| Ngang | Không mạnh cũng không yếu ở đa số | B, bổ sung có chọn lọc |
| Yếu | Yếu ở ≥4 trong 6 chỉ số | A |
| Hỗn hợp | Mạnh rõ một nhóm, yếu rõ nhóm khác | B cho phần mạnh, mục riêng cho phần yếu |

**Bước 3** — kiểm tra chéo bắt buộc khi vị thế Mạnh hoặc Ngang mà vẫn không lên top:

| Khả năng | Dấu hiệu | Xử lý |
|---|---|---|
| Nhiều trang nội bộ tranh nhau | Trang khác cùng domain nhồi cụm chính gần bằng hoặc hơn trang đích | Đầu ra B, phân vai lại |
| Một từ khóa mục tiêu bị bỏ trống | Ô biến thể đó trong ma trận thấp bất thường | Bổ sung có mục tiêu, không viết lại cả trang |
| Rào cản kỹ thuật | URL không chứa từ khóa, ảnh không tối ưu, schema khai khống, nội dung chỉ render bằng JS | Mục riêng về kỹ thuật |

**Không được kết luận "cần viết thêm nội dung" khi vị thế là Mạnh.**

**Bước 4** — đánh giá khả năng lên top:

| Cấu trúc top 3 | Kết luận |
|---|---|
| Cùng loại domain, quy mô tương đương | Khả thi |
| Có domain nhỏ hơn mình đang top | Khả thi cao. Phân tích kỹ trang đó — họ thắng bằng gì |
| Toàn sàn lớn, báo lớn, trang chính phủ | Không khả thi trực tiếp. Chuyển hướng sang truy vấn dài hơn |
| Toàn diễn đàn, hỏi đáp, video | Google hiểu truy vấn theo hướng khác. Đổi loại nội dung trước |

Trường hợp đáng chú ý nhất: **trang ít nội dung mà vẫn top 3**. Ví dụ thật: trang 2.208 từ
và 9 ảnh top 3, trong khi trang mình 6.853 từ và 130 ảnh không lên. Đây là bằng chứng mạnh
rằng độ dày không phải yếu tố quyết định — phải tìm xem họ có gì mà mình không có.

## 5.2b Cổng chặn trước khi chấm điểm — bắt buộc

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

## 5.3 Phát hiện gap SERP

Cách tìm: trích toàn bộ H2 và H3 của mọi trang trong tập, gom về nhóm chuẩn hóa,
lập bảng nhóm mục × domain, tìm nhóm mà top 3 đều không có.

| Loại gap | Đặc điểm | Xử lý |
|---|---|---|
| Gap thật | Không ai có, người dùng thực sự cần | Đề xuất |
| Gap giả | Không ai có vì không liên quan ý định tìm kiếm | Bỏ qua, không liệt kê cho đủ số |
| Gap thương hiệu | Chỗ chèn giải pháp của mình tự nhiên | Đề xuất, đánh nhãn BRAND |

Kiểm tra ngược: mục mà mọi đối thủ đều có mà mình không có thì không phải gap —
đó là thiếu sót, xếp vào danh sách vấn đề.

## 5.4 Mổ xẻ từng đối thủ

Mỗi trang một khối, ba câu, mỗi câu phải có số:
- Họ mạnh nhất ở đâu, nhắm nhánh truy vấn nào (đọc từ ma trận mật độ).
- Họ yếu ở đâu.
- Chỗ mình chen vào — cụ thể làm gì để vượt trang này.

Phân tích kỹ hơn: trang đứng đầu, và trang có vị thế yếu nhất mà vẫn trong top 3.

---

# 6. Cluster nội bộ và phân vai — đầu ra B

Nội dung phần này là file `rules/cluster.md`.

Điểm khác biệt cốt lõi: phát hiện nhiều trang tranh nhau bằng **mật độ cụm từ đo trên từng trang**,
không phải bằng thứ hạng luân phiên. Bắt được sớm hơn và chỉ ra chính xác trang nào đang lấn.

## 6.1 Tìm tập trang cùng chủ đề

Ba nguồn gộp lại: `site:` query, sitemap lọc theo mẫu đường dẫn, internal link hai chiều
với trang đích. Kết quả thường 2-6 trang.

## 6.2 Bảng đo

```
/mau-nha-cap-4-mai-thai-dep       pillar  6.853 từ  ×154  Trang cần lên top, bị 3 trang dưới cạnh tranh
/nha-cap-4-mai-thai-3-phong-ngu   con     5.976 từ  ×84   Dày ngang pillar, nhồi cụm chính dù chỉ nên nhắm nhánh riêng
/mau-nha-cap-4-mai-thai-8x12m     con     6.285 từ  ×77   Tương tự, title còn ghi năm cũ
/nha-mai-Thai                     mẹ      5.300 từ  ×20   Trang mẹ chủ đề; URL viết hoa
```

## 6.3 Ba dấu hiệu xác nhận

Thỏa mãn một dấu hiệu là đủ:

| Dấu hiệu | Ngưỡng |
|---|---|
| Trang con dày ngang pillar | Số từ trang con ≥80% số từ pillar |
| Trang con nhồi cụm chính nặng | Mật độ cụm chính trang con ≥50% của pillar |
| Title trùng cụm chính và trùng dạng | Cùng dùng cụm chính ở đầu, cùng kiểu con số dẫn đầu |

Diễn giải đúng: cluster lành mạnh có pillar rộng và trang con hẹp. Trang con dày ngang pillar
và dùng cụm chính gần bằng pillar nghĩa là chúng tự ứng cử cho cùng truy vấn thay vì dồn tín hiệu
về pillar.

## 6.4 Phân vai lại

| Vai | Khi nào | Việc |
|---|---|---|
| Pillar duy nhất | Mật độ cụm chính cao nhất, đúng ý định từ khóa mục tiêu | Giữ và mở rộng. Nhận link từ mọi trang còn lại, anchor đúng từ khóa mục tiêu |
| Trang con nhánh | Có biến thể riêng, có lượng tìm riêng | Giảm mật độ cụm chung, tăng mật độ cụm nhánh. Link về pillar trong 200 từ đầu |
| Trang mẹ chủ đề | Bao chủ đề rộng hơn | Đẩy trọng tâm sang chủ đề rộng, link xuống pillar |
| Gộp vào trang khác | Chỉ khi không có lượng tìm riêng và nội dung trùng thật | 301 về trang giữ lại, nêu rõ lý do |

**Mặc định là không gộp, không xóa.** Phân vai và nối link đúng chiều là việc sửa nội dung nhẹ,
không phải tái cấu trúc site — nói rõ điều này để người thực thi không sợ.

## 6.5 Kế hoạch nối link

Bảng: trang nguồn, trang đích, anchor, vị trí đặt.

- Anchor là **nguyên văn từ khóa mục tiêu** của trang đích. Không dùng "xem thêm", "tại đây".
- Link từ trang con về pillar đặt trong 200 từ đầu, không ở chân bài.
- Mỗi trang con trỏ về pillar đúng một link với anchor chính.
- Pillar trỏ xuống từng trang con bằng anchor là biến thể riêng của trang đó.

## 6.6 Việc kèm theo cho đầu ra B

| Nhóm | Khi nào đưa vào | Nội dung |
|---|---|---|
| Bổ sung có mục tiêu | Có ô mật độ thấp bất thường | Bổ sung đúng cụm đó vào title, H1, mở bài, một H2. Không viết lại cả trang |
| Chiều sâu chuyên môn | Cụm chuyên môn mà mọi đối thủ nhắc nhiều còn mình gần như không | Thêm một H2, nêu rõ đối thủ nào nhắc bao nhiêu lần |
| Kỹ thuật | Đo được vấn đề ảnh, schema, URL | Theo phần 7 mục 7.7 và 7.9 |
| Độ tươi | dateModified cũ hơn đối thủ top | Cập nhật nội dung và ngày, sửa năm trong title |

## 6.7 Lỗi cấp template

Cùng một lỗi xuất hiện trên nhiều trang thì đây là lỗi cấp template. Ghi vào mục riêng,
tách khỏi việc của cụm này, đề xuất xử lý một lần cho toàn site.

Ba lỗi hay gặp: schema khai nội dung không tồn tại; quy ước URL không nhất quán;
ảnh không có lazy-load hoặc srcset trên mọi trang.

---

# 7. Outline nội dung — đầu ra A

Nội dung phần này là file `rules/outline.md`.

## 7.1 Khối mục tiêu

Bốn con số suy từ tập đối thủ, không tự nghĩ:

| Mục tiêu | Cách suy |
|---|---|
| Độ dài body | Khoảng giữa trung vị và mức cao nhất của tập, không phải cao nhất |
| Số ảnh nội dung | Ngang mức cao nhất nếu là truy vấn dạng mẫu, ngang trung vị nếu không |
| Cấu trúc | Số H2 và H3 mục tiêu, so với trang chi tiết nhất trong tập |
| Số mục mới hoàn toàn | Đếm từ outline sau khi dựng |

Ghi kèm số hiện tại để thấy khoảng cách. **Không đặt mục tiêu vượt xa trang đứng đầu.**

## 7.2 Năm nhãn

| Nhãn | Nghĩa | Người viết làm gì |
|---|---|---|
| GIỮ | Nội dung cũ đã ổn | Viết lại nhẹ, giữ ý và giữ số |
| SỬA | Đã có nhưng chưa đủ sâu | Làm sâu hơn theo yêu cầu cụ thể |
| MỚI | Chưa có trên trang | Viết mới hoàn toàn |
| GAP SERP | Không đối thủ top 3 nào có | Viết mới, ưu tiên vì tạo khác biệt |
| BRAND | Chỗ chèn giải pháp của mình tự nhiên | Gắn sản phẩm vào đúng ngữ cảnh vấn đề |

Một mục có thể mang hai nhãn (MỚI + GAP SERP, hoặc MỚI + BRAND).

**Tỷ lệ hợp lý**: nhãn MỚI quá 70% tổng số mục nghĩa là đang viết lại từ đầu — xem lại
có chấm sai vị thế ở pha 3 không.

## 7.3 Cấu trúc mỗi mục

Mỗi H2: tiêu đề, độ dài mục tiêu, số H3 con, số ảnh và bảng cần có.

Mỗi H3: tiêu đề nguyên văn, nhãn, các ý cụ thể (có số thì đưa số vào), yêu cầu ảnh hoặc bảng.

Gắn nhãn MỚI hoặc GAP SERP thì phải dẫn số của đối thủ làm lý do.

## 7.4 Mở bài

| Câu | Nội dung |
|---|---|
| 1-2 | Định nghĩa gọn, chứa nguyên văn từ khóa chính |
| 3-4 | Ba con số neo. Kiểm tra đối thủ có đưa số trong mở bài không — không có thì đây là khác biệt |
| 5 | Nêu bài có gì để giữ chân người đọc |

Bắt buộc chèn các biến thể còn lại tự nhiên trong 100 từ đầu, nêu rõ biến thể nào đang
xuất hiện quá ít, dẫn số từ ma trận mật độ. Độ dài 130-160 từ, không đặt heading.

## 7.5 Lớp meta

Bảng bốn dòng, mỗi dòng có bản hiện tại và bản đề xuất: Title, Description, URL, H1.

URL không chứa từ khóa chính trong khi từ khóa mục tiêu có cụm đó → vấn đề tác động cao.
Đề xuất đổi URL phải kèm kế hoạch 301 và cảnh báo rủi ro mất tín hiệu tạm thời.

## 7.6 Bộ FAQ

Tám câu, **hiển thị thật trong HTML**, không chỉ khai trong schema.

Nguồn: hộp câu hỏi liên quan trên SERP thật; câu hỏi đối thủ có mà mình không có;
biến thể từ khóa chưa dùng được ở heading chính.

Mỗi câu: câu hỏi nguyên văn, trả lời 40-60 từ, ghi rõ có lấy từ hộp câu hỏi liên quan không.

## 7.7 Kế hoạch ảnh

Số ảnh mục tiêu, phân bổ theo H2, quy ước alt text, yêu cầu kỹ thuật (lazy-load, srcset, WebP,
kích thước tối đa), và danh sách ảnh cần vẽ mới. Dẫn số đối thủ để biện minh.

## 7.8 Internal link

Bảng hai chiều: link vào trang này từ các trang liên quan (anchor là từ khóa mục tiêu),
và link ra từ trang này tới trang con và trang sản phẩm. Áp dụng quy tắc anchor ở mục 6.5.

## 7.9 Structured data

Schema hiện có, cần sửa, cần thêm. Ba lỗi phải kiểm mỗi lần: khai nội dung không tồn tại;
dateModified không cập nhật; thiếu schema phù hợp loại nội dung.

## 7.10 Checklist theo đợt

| Đợt | Nội dung | Vì sao xếp ở đây |
|---|---|---|
| 1 | Kỹ thuật làm ngay: sửa URL, sửa schema, bật lazy-load | Rẻ, nhanh, không phụ thuộc nội dung |
| 2 | Lớp meta và mở bài | Tác động nhanh, không cần viết nhiều |
| 3 | Các mục SỬA | Dựa trên nội dung đã có |
| 4 | Các mục MỚI và GAP SERP | Tốn công nhất, làm sau khi nền đã sạch |
| 5 | Ảnh và internal link | Làm cùng lúc đợt 4 |

Mỗi việc ghi: ai làm, ước lượng thời gian, cách kiểm tra đã xong.

## 7.11 Đối chiếu trước và sau

Bảng cuối: từng khoảng cách đã nêu ở phần vấn đề, trạng thái hiện tại, trạng thái sau khi
làm xong outline. Khoảng cách nào outline không giải quyết thì ghi rõ lý do.

---

# 8. Cấu trúc báo cáo

Nội dung phần này là file `rules/report.md`.

Đường dẫn: `~/html/seo-gap-<domain>-<slug-cụm>-<YYYYMMDD>.html`.
Trang tổng hợp: `~/html/seo-gap-<domain>-tong-hop-<YYYYMMDD>.html`.

Style: template `templates/report.html` tự chứa toàn bộ CSS, không phụ thuộc thư viện ngoài.
Không emoji. Không dùng dòng nhãn nhỏ viết hoa phía trên tiêu đề.

## 8.1 Khối đầu trang

Tiêu đề cụm; câu mô tả phạm vi có ngày crawl; danh sách từ khóa mục tiêu; bốn ô chỉ số nổi bật;
mục lục.

Bốn ô chỉ số khác nhau theo loại đầu ra:

| | Đầu ra A | Đầu ra B |
|---|---|---|
| Ô 1 | Độ dài mục tiêu, kèm số hiện tại | Vị thế hiện tại, một câu |
| Ô 2 | Số ảnh mục tiêu, kèm số hiện tại | Rào cản số 1, một câu có số |
| Ô 3 | Cấu trúc mục tiêu | Rào cản số 2, một câu có số |
| Ô 4 | Số mục mới hoàn toàn | Từ khóa yếu nhất, kèm số |

## 8.2 Các mục

| # | Mục | Nội dung |
|---|---|---|
| 1 | Hiện trạng trang | Điểm mạnh (4-6 mục có số so sánh) rồi mới tới N vấn đề xếp theo bốn mức tác động |
| 2 | Vấn đề trọng tâm | Chỉ có khi phát hiện cluster. Theo phần 6 |
| 3 | So sánh toàn bộ trang trong SERP | Bảng chỉ số + bảng mật độ, mỗi bảng có 2-3 câu đọc bảng |
| 4 | Mổ xẻ từng đối thủ | Theo phần 5 mục 5.4 |
| 5+ | Phần đề xuất | Đầu ra A theo phần 7; đầu ra B theo phần 6 mục 6.6 |
| Cuối | Checklist triển khai theo đợt | Bắt buộc cho cả hai loại |

Không để bảng đứng trần. Mỗi bảng có câu đọc bảng chỉ ra điều quan trọng nhất.

## 8.3 Trang tổng hợp

Bảng, mỗi cụm một dòng: cụm (link tới báo cáo riêng), trang đích, vị thế, loại đầu ra,
rào cản chính (một câu có số), khả năng lên top, công sức, thứ tự đề nghị.

Thứ tự đề nghị: khả năng lên top trước, rồi công sức thấp trước. Cụm không khả thi xếp cuối,
kèm ghi chú nên chuyển hướng sang truy vấn nào.

Dưới bảng: đoạn ngắn nêu lỗi cấp template xuất hiện ở nhiều cụm — việc nên làm một lần
cho toàn site.

## 8.4 Ghi ngược vào case file

Có `~/.claude/skills/seo-doctor/cases/<domain>/` thì ghi thêm
`findings/<YYYY-MM-DD>-gap-<slug-cụm>.md`: vị thế, rào cản chính, việc đã đề xuất, mốc kiểm chứng.

Mốc kiểm chứng lấy độ trễ từ `seo-doctor/rules/baseline.md` mục 4 — tối ưu nội dung trang cũ
cần 4-8 tuần mới ổn định để đánh giá.

Chưa có case file thì không tự tạo.

---

# 9. Đặc tả 3 script

Nguyên tắc chung: Python 3.10+, JSON ra stdout, log ra stderr, lỗi trả JSON có khóa `error`
với thông điệp tiếng Việt. Không script nào chứa logic phân tích — script crawl, đếm, render.

## 9.1 `fetch_serp.py`

**Mục đích**: dựng tập đối thủ cho một cụm từ khóa.

```
fetch_serp.py --keywords "kw1,kw2,kw3" [--rank-file <file check top>]
              [--region "Google Vietnam, Ho Chi Minh City"] [--max-competitors 8]
```

```json
{
  "keywords": ["nhà cấp 4 mái Thái", "nhà mái Thái cấp 4"],
  "source": "rank_file",
  "crawl_date": "2026-07-31",
  "region": "Google Vietnam, Ho Chi Minh City",
  "competitors": [
    { "url": "https://...", "domain": "neohouse.vn", "domain_type": "cong-ty-xay-dung",
      "positions": { "nhà cấp 4 mái Thái": 1, "nhà mái Thái cấp 4": 4 },
      "top3_count": 1, "appears_for": 2 }
  ],
  "excluded": [ { "url": "...", "reason": "diễn đàn" } ],
  "trimmed": { "from": 14, "to": 8, "criteria": "top3_count desc, appears_for desc" },
  "error": null
}
```

- `domain_type` phân loại thủ công theo danh mục ở chỉ số 15; không suy được thì trả `null`
  và để model điền.
- `excluded` bắt buộc có, không được im lặng loại bỏ.

## 9.2 `measure_pages.py`

**Mục đích**: crawl và đo 15 chỉ số + ma trận mật độ.

```
measure_pages.py --own <url trang mình> --competitors <file JSON từ fetch_serp.py>
                 --terms "cụm1,cụm2,cụm3" [--cluster-scan] [--rate 2]
```

```json
{
  "crawl_date": "2026-07-31",
  "pages": [
    {
      "url": "https://...", "role": "own",
      "word_count": 6853, "content_images": 130, "lazy": 23, "srcset": 0, "webp": 0,
      "html_kb": 538, "h2": 9, "h3": 34,
      "faq": "schema_only",
      "date_modified": "2026-01-21",
      "internal_links": 179,
      "conversion": { "form": true, "hotline": true, "cta": true },
      "title": "...", "description": "...", "h1": "...", "url_slug": "...",
      "sample_items": 17,
      "schema": { "declared": ["FAQPage", "Article"], "rendered_mismatch": ["FAQPage"] },
      "headings": [ { "level": 2, "text": "..." } ]
    }
  ],
  "term_matrix": {
    "nhà cấp 4 mái Thái": { "own": 154, "neohouse.vn": 153, "duraflex.vn": 137 }
  },
  "cluster": [
    { "url": "...", "role_declared": "pillar", "word_count": 6853, "main_term_count": 154, "title": "..." }
  ],
  "blocked": [ { "url": "...", "reason": "403" } ],
  "error": null
}
```

- `faq` nhận một trong `none`, `schema_only`, `rendered`. Giá trị `schema_only` là lỗi,
  model phải nêu trong báo cáo.
- `schema.rendered_mismatch` liệt kê loại schema khai mà nội dung không có trong HTML.
- `headings` bắt buộc có — dùng để tìm gap SERP ở pha 4.
- `--cluster-scan` bật thì quét thêm trang cùng chủ đề trên domain mình.
- `blocked` bắt buộc có. Model phải nêu số trang đo được thực tế trong báo cáo.
- Mặc định `--rate 2` request mỗi giây.

## 9.3 `build_gap_report.py`

**Mục đích**: sinh HTML từ kết quả phân tích.

```
build_gap_report.py --input <file JSON> --out-dir ~/html [--summary]
```

Schema đầu vào tối thiểu:

```json
{
  "domain": "...", "cluster_name": "...", "date": "2026-08-01",
  "target_url": "...", "keywords": [],
  "crawl_date": "2026-07-31", "competitors_measured": 7, "competitors_blocked": 1,
  "position_verdict": "manh",
  "output_type": "B",
  "feasibility": { "verdict": "kha thi", "top3_structure": "..." },
  "highlights": [ { "label": "...", "value": "...", "note": "..." } ],
  "strengths": [ { "title": "...", "own": "...", "comparison": "..." } ],
  "issues": [ { "severity": "nghiem_trong", "title": "...", "own": "...",
                "comparison": "...", "why": "...", "evidence_block": "...",
                "template_level": false } ],
  "serp_table": [], "term_matrix": {},
  "competitor_breakdown": [ { "domain": "...", "strong": "...", "weak": "...", "entry_point": "..." } ],
  "cluster": { "pages": [], "signals": [], "reassignment": [], "link_plan": [] },
  "outline": { "targets": {}, "intro": {}, "sections": [] },
  "meta_layer": [], "faq": [], "image_plan": {}, "schema_fixes": [],
  "checklist": [ { "phase": 1, "tasks": [] } ],
  "before_after": []
}
```

- `output_type` quyết định render mục 5 trở đi theo phần 7 hay phần 6 mục 6.6.
- `--summary` sinh trang tổng hợp từ nhiều file JSON.
- Không emoji trong bất kỳ đầu ra nào.
- Mỗi bảng render kèm chỗ cho câu đọc bảng; thiếu câu đọc bảng thì cảnh báo ra stderr.

---

# 10. Tiêu chí nghiệm thu

## 10.1 Hai case hồi quy

Chạy lại trên đúng hai cụm đã có bản phân tích thủ công, không cho biết trước kết luận.

**Case 1 — nhà cấp 4 chữ L, vinhtuong.com**

| Tiêu chí | Đạt khi |
|---|---|
| Vị thế | Chấm ra Yếu, chọn đầu ra A |
| Điểm mạnh | Nhận ra trang đang có bộ ảnh lớn nhất và nội dung dài nhất nhóm — không kết luận "nội dung yếu" chung chung |
| Vấn đề tác động cao | Bắt được URL không chứa cụm "cấp 4", và chuyển hướng ngược chiều giữa bản chữ hoa và chữ thường |
| Schema | Phát hiện FAQPage khai câu hỏi không có trong HTML |
| Outline | Sinh được outline có nhãn, tỷ lệ nhãn MỚI không vượt 70% |
| Gap SERP | Tìm ra ít nhất một mục mà không đối thủ top 3 nào có |

**Case 2 — nhà cấp 4 mái Thái, vinhtuong.com**

| Tiêu chí | Đạt khi |
|---|---|
| Vị thế | Chấm ra Mạnh, chọn đầu ra B. **Đây là tiêu chí quan trọng nhất** |
| Không đề xuất viết lại | Kết luận rõ "nội dung đã mạnh, không phải làm lại" |
| Cluster | Phát hiện 4 trang cùng nhắm một cụm, đo được mật độ từng trang |
| Phân vai | Ra được bảng phân vai, và kết luận không cần gộp hay xóa trang nào |
| Biến thể bỏ trống | Bắt được cụm đảo trật tự xuất hiện ít hơn hẳn đối thủ đang top |
| Lỗi cấp template | Nhận ra schema khai khống là lỗi lặp lại ở cả hai cụm, đề xuất xử lý một lần |

Sai tiêu chí "chấm ra Mạnh" ở case 2 là lỗi nghiêm trọng nhất — hệ thống sẽ đề xuất viết lại
một trang đã mạnh nhất SERP.

## 10.2 Checklist chất lượng đầu ra

| # | Kiểm tra |
|---|---|
| 1 | Mục điểm mạnh có mặt và đứng trước mục vấn đề |
| 2 | Mỗi điểm mạnh và mỗi vấn đề đều có số của mình và số của đối thủ |
| 3 | Ma trận mật độ có đủ cả biến thể đảo trật tự |
| 4 | Ngày crawl có mặt trong câu mô tả phạm vi |
| 5 | Trang bị chặn crawl được nêu rõ, không im lặng bỏ qua |
| 6 | Mỗi bảng có câu đọc bảng, không để bảng đứng trần |
| 7 | Lỗi cấp template được tách riêng khỏi việc của cụm |
| 8 | Checklist chia theo đợt, mỗi việc có người làm và cách kiểm tra |
| 9 | Không có câu đề xuất nào thiếu số làm căn cứ |
| 10 | Không emoji |
| 11 | Đầu ra A: có đối chiếu trước và sau |
| 12 | Đầu ra B: có kết luận rõ về việc có cần gộp hay xóa trang không |

## 10.3 Kiểm thử luồng dừng

| Tình huống | Hành vi đúng |
|---|---|
| Không có tập đối thủ và không tra được SERP | Dừng, không phân tích chay |
| Trên nửa số trang đối thủ chặn crawl | Cảnh báo rõ, hỏi người dùng có tiếp tục với tập nhỏ hơn không |
| Vị thế Mạnh nhưng chưa chạy quét cluster | Không được xuất báo cáo, phải quét cluster trước |
| Trang đích đang có sự cố kỹ thuật nặng | Chuyển sang `/seo-doctor`, không phân tích khoảng cách trên trang đang hỏng |
| Đo được dưới 3 đối thủ (do render JS hoặc bị chặn) | KHÔNG chấm vị thế. Lấy HTML sau render bằng Chrome MCP, đổi tập đối thủ, hoặc báo chưa đánh giá được |
| Trang đích của mình render bằng JS | Dừng hẳn, mọi chỉ số nội dung đều sai |

---

# 11. Ràng buộc và điều cấm

## 11.1 Không được làm nếu chưa hỏi

Sửa file trên website. Đăng hoặc chỉnh nội dung. Thay đổi URL hoặc chuyển hướng.
Chạy crawl với tần suất cao trên site production hoặc site đối thủ.

## 11.2 Cấm tuyệt đối

- Đưa ra con số không đo được từ crawl mà không ghi rõ nguồn khác.
- Đề xuất viết lại khi vị thế là Mạnh.
- Kết luận "nội dung yếu" mà không có bảng so sánh cụ thể.
- Liệt kê gap giả cho đủ số.
- Bỏ qua mục điểm mạnh.
- Dùng emoji.

## 11.3 Ranh giới

| Tình huống | Chuyển sang |
|---|---|
| Trang đang tụt hạng, cần biết vì sao | `/seo-doctor` |
| Cần báo cáo traffic định kỳ | `/seo-analyst` |
| Traffic tốt nhưng không ra đơn | `/cro-analyst` |

Trang vừa tụt mạnh thì chạy `/seo-doctor` trước — phân tích khoảng cách trên một trang đang có
sự cố kỹ thuật là lãng phí.
