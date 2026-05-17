# Setup Guide — SEO Traffic Analyst

## Tổng quan luồng

```
Admin (1 lần)                          Mỗi user (1 lần)
──────────────────────────────         ─────────────────────────────────────
1. Tạo OAuth2 Desktop client     →     2. Nhận thư mục seo-analyst/
   Google Cloud Console                3. python manage_accounts.py auth
   manage_accounts.py set-oauth-client    → browser mở → đăng nhập Google
   Share thư mục cho users                → chọn GA4 property + GSC site
                                          → xong, không cần làm gì thêm
```

---

## Bước 1 — Admin: Tạo OAuth2 Client (1 lần)

### 1.1 Enable APIs

Vào [console.cloud.google.com](https://console.cloud.google.com) → chọn project → **APIs & Services → Enable APIs**, bật:
- Google Analytics Data API
- Google Analytics Admin API  ← cần để auto-discover properties
- Google Search Console API
- Google Sheets API
- Google Drive API

### 1.2 Tạo OAuth2 Client

**APIs & Services → Credentials → Create Credentials → OAuth client ID**
- Application type: **Desktop app**
- Name: `SEO Analyst` (tùy đặt)
- Download JSON → lưu file `client_secret_xxx.json`

> Nếu lần đầu dùng OAuth, GCP sẽ yêu cầu cấu hình **OAuth consent screen** trước:
> - User type: External (hoặc Internal nếu dùng Google Workspace)
> - App name + email
> - Scopes: thêm các scope analytics/webmasters/sheets (hoặc để trống, add sau)
> - Test users: thêm email của những user sẽ dùng skill

### 1.3 Đăng ký OAuth client vào skill

```bash
cd ~/.claude/skills/seo-analyst
.venv/bin/python manage_accounts.py set-oauth-client ~/Downloads/client_secret_xxx.json
```

### 1.4 Cài dependencies (nếu chưa)

```bash
.venv/bin/pip install -r requirements.txt
```

### 1.5 Share cho users

Compress và share thư mục `~/.claude/skills/seo-analyst/` (đã có `oauth_client.json` bên trong).
**Không share** thư mục `credentials/` — đó là token cá nhân của từng user.

---

## Bước 2 — Mỗi user: Auth 1 lần

```bash
cd ~/.claude/skills/seo-analyst
.venv/bin/python manage_accounts.py auth
```

Quá trình:
1. Browser mở → đăng nhập bằng Google account có quyền GA4/GSC
2. Approve quyền truy cập
3. Script tự discover danh sách GA4 properties và GSC sites
4. User chọn property/site muốn phân tích
5. Nhập tên profile (vd: `blog-abc`)
6. Profile được lưu, token được store tại `credentials/blog-abc.json`

> Nếu có nhiều site, chạy `auth` nhiều lần với `--name` khác nhau mỗi lần.

---

## Format Google Sheet nhóm URL (optional)

Nếu muốn phân tích theo nhóm chủ đề, tạo Google Sheet với format:

| url | topic | keyword_cluster | publish_date |
|-----|-------|-----------------|--------------|
| /bai-viet-1 | SEO | Link Building | 2024-01-15 |
| /bai-viet-2 | Content | Content Strategy | 2024-02-20 |

- Header dòng 1, cột `url` là bắt buộc
- Các cột còn lại tùy đặt — skill tự detect và phân nhóm theo từng cột
- Lấy Sheet ID từ URL: `docs.google.com/spreadsheets/d/**{ID}**/edit`
- Thêm vào profile: `.venv/bin/python manage_accounts.py update --name blog-abc --sheet-id {ID}`

---

## Sử dụng

```bash
# Phân tích 30 ngày (default profile)
.venv/bin/python scripts/main.py 30d

# Chỉ định profile cụ thể
.venv/bin/python scripts/main.py 30d --profile blog-abc

# Hoặc đặt default rồi chạy không cần --profile
.venv/bin/python manage_accounts.py default --name blog-abc
.venv/bin/python scripts/main.py 30d

# Xem danh sách profiles
.venv/bin/python manage_accounts.py list

# Test kết nối
.venv/bin/python manage_accounts.py test --name blog-abc
```

---

## Troubleshooting

**"OAuth client not configured"**
→ Chạy `set-oauth-client` với file client_secret đúng

**"Access blocked: This app's request is invalid"**
→ OAuth consent screen chưa add test user. Vào GCP → OAuth consent screen → Test users → Add email

**"Token has been expired or revoked"**
→ Chạy lại `auth --name <profile>` để re-authenticate

**Không thấy GA4 property trong danh sách**
→ Đảm bảo đăng nhập đúng Google account có quyền GA4. Hoặc nhập GA4 ID thủ công khi được hỏi.
