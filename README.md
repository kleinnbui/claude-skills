# Claude Code Skills — CRO & SEO

Bộ 3 skills cho Claude Code giúp tự động hóa CRO measurement và phân tích SEO traffic, không cần click thủ công hay copy-paste terminal.

> Tất cả skills yêu cầu **Claude Code** (CLI hoặc desktop app) — không hoạt động trên Claude.ai web.

---

## Skills

### [/cro-setup](./cro-setup/) — CRO Measurement Auto-Installer

Tự động tạo toàn bộ GTM + GA4 setup cho CRO tracking trong ~5 phút.

- 14 GTM Data Layer Variables + 1 Trigger + 2 Tags
- 10 GA4 Custom Dimensions + 3 Custom Metrics + 1 Key Event
- Wizard Q&A (forms, conversions, A/B tests)
- Multi-profile, preview dry-run, save-version-only (không auto publish)

**Yêu cầu:** Quyền Edit GTM container + Editor/Admin GA4 property

---

### [/cro-report](./cro-report/) — CRO Report Generator

Sinh báo cáo HTML self-contained từ GA4 data. Mở trong browser, filter tức thì, không cần login.

- 6 sections: KPI, timeline, funnel, per-form table, failures, journey insights
- Reuse OAuth + profiles của `/cro-setup` — zero setup nếu đã có
- Deploy auto-refresh lên server (tùy chọn)

**Yêu cầu:** Đã cài `/cro-setup` với ít nhất 1 form submission

---

### [/seo-analyst](./seo-analyst/) — SEO Traffic Analyst

Phân tích traffic GA4 + GSC theo chiều sâu. Hỏi bằng ngôn ngữ tự nhiên.

- Trend, content decay, CTR opportunity, keyword cannibalization
- YoY comparison, drill-down URL, batch multi-site
- Export 20-tab Google Sheets, watch list
- Multi-profile, anomaly detection

**Yêu cầu:** Quyền Viewer GA4 + Full User Google Search Console

---

## Cài đặt nhanh

### 1. Cài Claude Code

Tải tại [claude.ai/download](https://claude.ai/download) (Mac hoặc Windows).

### 2. Cài Python 3.10+

```bash
python3 --version  # Kiểm tra
```

Nếu chưa có: [python.org/downloads](https://www.python.org/downloads/)

### 3. Import skills

Trong Claude Code → **Settings** → tab **Skills** → **+ Add skill** → chọn file `.skill` tương ứng.

### 4. Thứ tự cài đặt khuyến nghị

```
/cro-setup  →  /cro-report  →  /seo-analyst
```

`/cro-report` reuse OAuth của `/cro-setup` → setup 1 lần cho cả 2.

---

## Setup OAuth Client (bắt buộc, 1 lần duy nhất)

Mỗi skill cần một **OAuth Client ID** từ Google Cloud Console để đăng nhập Google API.

1. Vào [Google Cloud Console](https://console.cloud.google.com/) → tạo project
2. **APIs & Services → Library** → bật các API cần thiết (xem README từng skill)
3. **Credentials → Create OAuth Client ID** → Desktop app → Download JSON
4. Copy `oauth_client.example.json` thành `oauth_client.json` và điền thông tin

> Khi chạy lần đầu, từng skill sẽ hướng dẫn chi tiết từng bước — không cần đọc trước.

---

## Bảo mật

Các file sau **đã được `.gitignore`** — không bao giờ commit:

| Pattern | Nội dung |
|---------|---------|
| `oauth_client.json` | OAuth client secret |
| `credentials/*.json` | OAuth access/refresh tokens |
| `accounts.json` | Profile data (GTM/GA4 IDs thật) |
| `configs/<site>.json` | Config client thật |
| `reports/*.html` | Reports có thể chứa data nhạy cảm |

Chỉ commit các file `*.example.json` — là template trống, không có thông tin thật.

---

## Cấu trúc repo

```
claude-skills/
├── .gitignore
├── README.md
├── cro-setup/          # /cro-setup skill
├── cro-report/         # /cro-report skill
└── seo-analyst/        # /seo-analyst skill
```
