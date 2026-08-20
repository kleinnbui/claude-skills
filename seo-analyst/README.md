# /seo-analyst — SEO Traffic Analyst

Phân tích traffic GA4 + GSC theo chiều sâu — trend, content decay, CTR opportunity, keyword cannibalization, traffic tiềm năng. Multi-profile, OAuth2.

> Yêu cầu **Claude Code** (CLI hoặc desktop app). Không hoạt động trên Claude.ai web.

---

## Cài đặt

### 1. Yêu cầu

- Claude Code đã cài — [tải tại claude.ai/download](https://claude.ai/download)
- Python 3.10+ — kiểm tra: `python3 --version`
- Google account có quyền **Viewer** GA4 property + **Full User** Google Search Console

### 2. Tải file `.skill`

Tải [`dist/seo-analyst.skill`](../dist/seo-analyst.skill) từ thư mục `dist/` của repo này.

### 3. Import vào Claude Code

1. Mở Claude Code → click **⚙ Settings** (góc dưới trái)
2. Chọn tab **Skills** → click **+ Add skill**
3. Chọn file `seo-analyst.skill` vừa tải → **Open**
4. Gõ `/` trong chat → `/seo-analyst` xuất hiện trong gợi ý là OK

### 4. Lần đầu chạy

```
/seo-analyst
```

Skill tự cài Python dependencies, sau đó hướng dẫn:
1. Đăng nhập Google → chọn GA4 property + GSC site
2. (Optional) Sheet ID phân nhóm URL, KPI tháng, brand keywords
3. Tự động chạy báo cáo 30 ngày ngay lập tức

---

## Phân tích có sẵn

| Lệnh tự nhiên | Mô tả |
|---------------|-------|
| `/seo-analyst` | Báo cáo tổng quan 30 ngày |
| `"Chạy 90 ngày"` | Thay đổi khoảng thời gian |
| `"So với cùng kỳ năm ngoái"` | YoY comparison |
| `"Xem queries của URL [url]"` | Drill-down 1 trang |
| `"Lưu ra Sheets"` | Export 20 tabs Google Sheets |
| `"So sánh tất cả sites"` | Batch view |
| `"Check nhanh traffic hôm nay"` | Anomaly detection |

---

## Cấu trúc thư mục

```
seo-analyst/
├── SKILL.md                    # Skill definition (đọc bởi Claude)
├── SETUP.md                    # Hướng dẫn chi tiết
├── install.sh                  # Cài Python venv + dependencies
├── manage_accounts.py          # CLI quản lý profiles
├── requirements.txt            # Python dependencies
├── oauth_client.example.json   # Template — copy thành oauth_client.json
├── accounts.example.json       # Template — accounts.json tự tạo khi chạy
├── credentials/                # OAuth tokens (gitignored)
│   └── .gitkeep
└── scripts/
    ├── auth.py
    ├── config.py
    ├── export_sheets.py
    ├── fetch_ga4.py
    ├── fetch_gsc.py
    ├── fetch_sheets.py
    ├── main.py
    └── setup_flow.py
```

---

## Quản lý profiles

```bash
cd ~/.claude/skills/seo-analyst

# Xem danh sách sites
bash run.sh manage_accounts.py list

# Cập nhật KPI tháng
bash run.sh manage_accounts.py update --name myblog --kpi-target 5000 --kpi-source gsc

# Cập nhật brand keywords
bash run.sh manage_accounts.py update --name myblog --brand-keywords "mybrand,my brand"

# Thêm URL vào watch list
bash run.sh manage_accounts.py watchlist-add --name myblog --url "https://example.com/page/"

# Xóa site
bash run.sh manage_accounts.py remove --name myblog
```

---

## Lưu ý bảo mật

| File | Trạng thái | Ghi chú |
|------|-----------|---------|
| `oauth_client.json` | Gitignored | Chứa client secret |
| `credentials/*.json` | Gitignored | OAuth access/refresh tokens |
| `accounts.json` | Gitignored | Profile data |
