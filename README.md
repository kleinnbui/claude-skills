# Claude Code Skills — CRO & SEO

Bộ 3 skills cho Claude Code giúp tự động hóa CRO measurement và phân tích SEO traffic, không cần click thủ công hay copy-paste terminal.

> Yêu cầu **Claude Code** (CLI hoặc desktop app) — không hoạt động trên Claude.ai web.

---

## Cài đặt nhanh

### Bước 1 — Cài Claude Code & Python

- Claude Code: [claude.ai/download](https://claude.ai/download) (Mac hoặc Windows)
- Python 3.10+: [python.org/downloads](https://www.python.org/downloads/) — kiểm tra bằng `python3 --version`

### Bước 2 — Tải file `.skill`

Vào thư mục [`dist/`](./dist/) và tải file `.skill` của skill bạn muốn dùng:

| File | Skill |
|------|-------|
| [`dist/cro-setup.skill`](./dist/cro-setup.skill) | `/cro-setup` — CRO Measurement Auto-Installer |
| [`dist/cro-report.skill`](./dist/cro-report.skill) | `/cro-report` — CRO Report Generator |
| [`dist/cro-analyst.skill`](./dist/cro-analyst.skill) | `/cro-analyst` — CRO Diagnostic + Prescriptive Analyst |
| [`dist/seo-analyst.skill`](./dist/seo-analyst.skill) | `/seo-analyst` — SEO Traffic Analyst |

### Bước 3 — Import vào Claude Code

1. Mở Claude Code → click **⚙ Settings** (góc dưới trái)
2. Chọn tab **Skills** → click **+ Add skill**
3. Chọn file `.skill` vừa tải → **Open**
4. Skill xuất hiện trong danh sách là OK

**Kiểm tra:** Gõ `/` trong chat → tên skill xuất hiện trong gợi ý.

### Bước 4 — Thứ tự cài đặt khuyến nghị

```
/cro-setup  →  /cro-report  →  /cro-analyst  →  /seo-analyst
```

`/cro-report` và `/cro-analyst` reuse OAuth + profiles của `/cro-setup` → setup 1 lần dùng chung cả 3.

### Bước 5 — Chạy lần đầu

Gõ tên skill trong chat (vd: `/cro-setup`). Skill sẽ tự hướng dẫn từng bước — không cần đọc tài liệu trước.

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

### [/cro-analyst](./cro-analyst/) — CRO Diagnostic + Prescriptive Analyst

Lớp **chẩn đoán + đề xuất** — trả lời "tại sao?" và "nên làm gì?" thay vì chỉ hiển thị số.

- 5 analyzers: funnel bottleneck, form triage, failure postmortem, channel ROI, anomaly detection
- Health score 0-100 + top 3 issues + top 3 opportunities
- Natural-language Q&A tiếng Việt
- Reuse OAuth + profiles của `/cro-setup` — zero setup nếu đã có

**Yêu cầu:** Đã cài `/cro-setup` (recommended) hoặc Viewer access GA4 property

---

### [/seo-analyst](./seo-analyst/) — SEO Traffic Analyst

Phân tích traffic GA4 + GSC theo chiều sâu. Hỏi bằng ngôn ngữ tự nhiên.

- Trend, content decay, CTR opportunity, keyword cannibalization
- YoY comparison, drill-down URL, batch multi-site
- Export 20-tab Google Sheets, watch list
- Multi-profile, anomaly detection

**Yêu cầu:** Quyền Viewer GA4 + Full User Google Search Console

---

## Cấu trúc repo

```
claude-skills/
├── dist/                  # File .skill — tải về và import vào Claude Code
│   ├── cro-setup.skill
│   ├── cro-report.skill
│   ├── cro-analyst.skill
│   └── seo-analyst.skill
├── cro-setup/             # Source code + hướng dẫn chi tiết
├── cro-report/
├── cro-analyst/
└── seo-analyst/
```
