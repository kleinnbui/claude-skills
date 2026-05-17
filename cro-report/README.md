# /cro-report — CRO Report Generator

Sinh báo cáo HTML self-contained từ GA4 data của CRO Engine. Mở thẳng trong browser, không cần đăng nhập Google để xem.

**Báo cáo gồm 6 sections:** KPI overview, timeline, conversion funnel, per-form table, failed attempts, journey insights — filter client-side tức thì.

> Yêu cầu **Claude Code** (CLI hoặc desktop app). Không hoạt động trên Claude.ai web.

---

## Cài đặt

### 1. Yêu cầu

- Claude Code đã cài — [tải tại claude.ai/download](https://claude.ai/download)
- Python 3.10+ — kiểm tra: `python3 --version`
- Đã cài `/cro-setup` và có ít nhất 1 form submission sau khi publish container

> **Lưu ý:** Nếu đã có `/cro-setup`, skill này reuse toàn bộ OAuth + profiles → không cần setup thêm.

### 2. Tải file `.skill`

Tải [`dist/cro-report.skill`](../dist/cro-report.skill) từ thư mục `dist/` của repo này.

### 3. Import vào Claude Code

1. Mở Claude Code → click **⚙ Settings** (góc dưới trái)
2. Chọn tab **Skills** → click **+ Add skill**
3. Chọn file `cro-report.skill` vừa tải → **Open**
4. Gõ `/` trong chat → `/cro-report` xuất hiện trong gợi ý là OK

### 3. Lần đầu chạy

```
/cro-report
```

Skill tự detect nếu đã có `/cro-setup` → chọn date range → tạo report ngay.

Nếu chưa có `/cro-setup` (standalone):
1. Setup OAuth Client trên Google Cloud Console (bật **Google Analytics Data API** + **Admin API**)
2. Đăng nhập Google → chọn GA4 property
3. Chọn date range → tạo report

---

## Output

File HTML được lưu tại:
```
~/.claude/skills/cro-report/reports/<site>-YYYYMMDD-HHMM.html
```

Mở bằng `file://` trên browser bất kỳ. Muốn data mới → chạy lại `/cro-report`.

### Deploy auto-refresh (tùy chọn nâng cao)

Nếu có VPS/server riêng với SSH access, `/cro-report` có thể deploy cron job để tự update mỗi N giờ và phục vụ qua URL public.

---

## Cấu trúc thư mục

```
cro-report/
├── SKILL.md                    # Skill definition (đọc bởi Claude)
├── install.py                  # Cài Python venv + dependencies (cross-platform)
├── manage_accounts.py          # CLI quản lý profiles
├── requirements.txt            # Python dependencies
├── accounts.example.json       # Template — accounts.json tự tạo khi chạy
├── reports/                    # Generated HTML reports (gitignored)
│   └── .gitkeep
├── templates/
│   └── report.html             # HTML template
└── scripts/
    ├── auth.py
    ├── config.py
    ├── ga4_fetcher.py
    ├── main.py
    ├── report_builder.py
    └── setup_flow.py
```

---

## Lưu ý bảo mật

| File | Trạng thái | Ghi chú |
|------|-----------|---------|
| `accounts.json` | Gitignored | Profile data |
| `reports/*.html` | Gitignored | Có thể chứa data nhạy cảm của client |
| `oauth_client.json` | Gitignored | Nếu dùng standalone (không qua cro-setup) |
