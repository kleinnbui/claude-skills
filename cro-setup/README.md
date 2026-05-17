# /cro-setup — CRO Measurement Auto-Installer

Tự động cài đặt toàn bộ CRO measurement lên GTM + GA4 trong vài phút — không cần click thủ công.

**Tạo tự động:**
- 14 GTM Data Layer Variables
- 1 GTM Trigger + 2 GTM Tags (CRO Engine + GA4 event)
- 10 GA4 Custom Dimensions, 3 GA4 Custom Metrics, 1 Key Event

> Yêu cầu **Claude Code** (CLI hoặc desktop app). Không hoạt động trên Claude.ai web.

---

## Cài đặt

### 1. Yêu cầu

- Claude Code đã cài — [tải tại claude.ai/download](https://claude.ai/download)
- Python 3.10+ — kiểm tra: `python3 --version`
- Google account có quyền **Edit** GTM container + **Editor/Admin** GA4 property

### 2. Import skill vào Claude Code

1. Mở Claude Code → **Settings** (⚙ góc dưới trái) → tab **Skills**
2. Click **+ Add skill** → chọn file `cro-setup.skill`
3. Gõ `/` trong chat → `/cro-setup` xuất hiện trong gợi ý là OK

### 3. Setup OAuth Client (1 lần duy nhất)

Khi chạy `/cro-setup` lần đầu, skill sẽ hướng dẫn bạn:

1. Vào [Google Cloud Console](https://console.cloud.google.com/)
2. Tạo/chọn project → bật 2 APIs:
   - **Tag Manager API**
   - **Google Analytics Admin API**
3. **Credentials → Create OAuth Client ID** → Desktop app → Download JSON
4. Lưu file JSON vào `~/Downloads/client_secret.json`
5. **OAuth consent screen → Test users** → thêm email Google của bạn

Sau đó copy `oauth_client.example.json` thành `oauth_client.json` và điền thông tin:

```bash
cp oauth_client.example.json oauth_client.json
# Mở oauth_client.json và điền client_id + client_secret từ file download
```

> **Bảo mật:** `oauth_client.json` chứa client secret — đã được `.gitignore`. Không commit file này.

### 4. Lần đầu chạy

```
/cro-setup
```

Skill tự cài Python dependencies (~30s), sau đó hướng dẫn qua 6 bước:
1. Setup OAuth client (đã làm ở trên → skip)
2. Đăng nhập Google + chọn GTM container
3. Chọn GA4 property
4. Wizard Q&A (forms, conversions, A/B tests)
5. Preview dry-run
6. Apply → tạo GTM version (không auto publish)

---

## Cấu trúc thư mục

```
cro-setup/
├── SKILL.md                    # Skill definition (đọc bởi Claude)
├── install.sh                  # Cài Python venv + dependencies
├── manage_accounts.py          # CLI quản lý profiles
├── requirements.txt            # Python dependencies
├── oauth_client.example.json   # Template — copy thành oauth_client.json
├── accounts.example.json       # Template — accounts.json tự tạo khi chạy
├── configs/
│   └── example.json            # Template config cho 1 site
├── credentials/                # OAuth tokens (gitignored)
└── scripts/
    ├── auth.py
    ├── config.py
    ├── engine.py               # CRO Engine code (embed vào GTM tag)
    ├── ga4_sync.py
    ├── gtm_sync.py
    ├── main.py
    └── setup_flow.py
```

---

## Quản lý profiles

```bash
cd ~/.claude/skills/cro-setup

# Xem danh sách sites
.venv/bin/python manage_accounts.py list

# Xem chi tiết 1 site
.venv/bin/python manage_accounts.py show --name elitedental

# Đổi site mặc định
.venv/bin/python manage_accounts.py default --name elitedental

# Xóa site
.venv/bin/python manage_accounts.py remove --name elitedental
```

---

## Lưu ý bảo mật

| File | Trạng thái | Ghi chú |
|------|-----------|---------|
| `oauth_client.json` | Gitignored | Chứa client secret |
| `credentials/*.json` | Gitignored | OAuth access/refresh tokens |
| `accounts.json` | Gitignored | Profile data với GTM/GA4 IDs |
| `configs/<site>.json` | Gitignored | Config client thật (chỉ `example.json` được commit) |
