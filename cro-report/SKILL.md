---
name: cro-report
description: Sinh báo cáo CRO online từ GA4 — single HTML file với 6 sections (KPI, timeline, funnel, per-form table, failures, journey insights), filter client-side instant. Reuse profile + OAuth của /cro-setup nếu có.
dependencies:
  - google-analytics-data>=0.18.0
  - google-analytics-admin>=0.22.0
  - google-api-python-client>=2.100.0
  - google-auth>=2.23.0
  - google-auth-oauthlib>=1.1.0
---

# /cro-report — CRO Report Generator

Sinh báo cáo HTML self-contained từ GA4 data của CRO Engine. Reuse profile của `/cro-setup` (nếu có) → 0 setup nếu user đã cài cro-setup. Mở thẳng trong browser, không cần Google login khi xem.

Yêu cầu: Claude Code (CLI / desktop). Không hoạt động trong Claude.ai web chat.

---

## Cài đặt (người dùng nhận file .skill)

### 1. Yêu cầu trước
- **Claude Code desktop app** đã cài (Mac hoặc Windows) — tải tại https://claude.ai/download
- **Python 3.10+** đã cài — kiểm tra bằng `python3 --version` trong terminal. Nếu chưa có: https://www.python.org/downloads/

### 2. Import skill

**Mac / Windows (app):**
1. Mở Claude Code → click icon **⚙ Settings** (góc dưới trái)
2. Chọn tab **Skills** → click **+ Add skill**
3. Chọn file `cro-report.skill` vừa nhận → **Open**
4. Skill xuất hiện trong danh sách → đóng Settings

**Kiểm tra:** Gõ `/` trong chat → `/cro-report` xuất hiện trong gợi ý.

### 3. Lần đầu chạy

Gõ `/cro-report` → skill tự làm các việc sau (ẩn với user):
- Tạo Python virtual environment (`~/.claude/skills/cro-report/.venv/`)
- Cài dependencies (~30–60 giây, chỉ lần đầu)

Sau đó skill hỏi tuỳ trường hợp:

| Tình huống | Flow tiếp theo |
|---|---|
| Đã có `/cro-setup` trên máy | **Không cần setup thêm** — chọn date range → tạo report ngay |
| Chưa có gì | Hỏi: cài `/cro-setup` (khuyến nghị) hoặc standalone setup |
| Standalone (chưa có OAuth) | BƯỚC 1b → tạo OAuth client trên GCP (~5 phút, 1 lần duy nhất) |
| Standalone (đã có OAuth, chưa có profile) | BƯỚC 1c → đăng nhập Google + chọn GA4 property (~2 phút) |

### 4. Tạo report

Sau khi có profile:
1. Chọn date range (mặc định 30 ngày)
2. Skill fetch ~16 GA4 queries (~20–30 giây)
3. File HTML tự mở trong browser — không cần login Google để xem

> **Output là file local** (`~/.claude/skills/cro-report/reports/client-YYYYMMDD-HHMM.html`), mở bằng `file://`. Muốn data mới → chạy lại `/cro-report`.
>
> **Deploy lên server** (BƯỚC 6 bên dưới) là tính năng nâng cao — chỉ dùng được nếu bạn có SSH access đến VPS/server riêng. Người dùng thông thường bỏ qua phần đó.

---

## BƯỚC 0 — Bootstrap (chạy tự động, trong suốt với user)

Kiểm tra cài đặt:

```bash
test -f ~/.claude/skills/cro-report/.venv/bin/python || test -f ~/.claude/skills/cro-report/.venv/Scripts/python.exe && echo "READY" || echo "NEED_SETUP"
```

Nếu `NEED_SETUP`, tự chạy installer (cross-platform):

```bash
(command -v python3 >/dev/null && python3 ~/.claude/skills/cro-report/install.py) || \
(command -v python >/dev/null && python ~/.claude/skills/cro-report/install.py)
```

Nếu cả hai python lệnh đều không có → báo user: *"Cần cài Python 3.10+ — https://www.python.org/downloads/"* rồi dừng.

Tạo accounts.json trống nếu chưa có:

```bash
test -f ~/.claude/skills/cro-report/accounts.json || echo '{"default":null,"profiles":{}}' > ~/.claude/skills/cro-report/accounts.json
```

---

## BƯỚC 1 — Detect profile source + list profiles

```bash
cd ~/.claude/skills/cro-report && .venv/bin/python scripts/main.py list-profiles 2>&1
```

(Trên Windows: `.venv\Scripts\python.exe scripts\main.py list-profiles`)

Parse JSON output:

```json
{
  "ok": true,
  "default": "elitedental",
  "oauth_client": {"configured": true, "exists": true, "source": "cro-setup", ...},
  "profiles": {
    "elitedental": {"_source": "cro-setup", "client_name": "Elite Dental", "ga4_property_id": "315143198", ...}
  },
  "last_run": {"profile": "elitedental", "date_preset": "last_30_days", ...}
}
```

3 nhánh:

### Nhánh A — Profile có sẵn (đa số case sau khi cài cro-setup)
→ Skip OAuth setup, đi thẳng **BƯỚC 3 (last_run optimization)** hoặc **BƯỚC 4**

### Nhánh B — `profiles` empty + `oauth_client.configured: false`
AskUserQuestion: *"Chưa có profile và OAuth client. Bạn muốn:"*
- **(a) Cài /cro-setup trước** (recommended — quản lý unified cả GTM/GA4 setup + report)
- **(b) Setup standalone cho cro-report** (chỉ cần read GA4, nhẹ hơn)

Nếu (a): hiển thị link import `cro-setup.skill` → dừng skill này.
Nếu (b): đi **BƯỚC 1b standalone setup**.

### Nhánh C — `profiles` empty + OAuth client có (từ cro-setup)
→ Đi **BƯỚC 1c-OAuth** (skip OAuth client setup, chỉ cần auth flow + chọn GA4 property)

---

## BƯỚC 1b — Standalone OAuth client setup (1 lần duy nhất, admin)

Hiển thị cho user (tương tự cro-setup BƯỚC 1b):

> **Cần tạo OAuth Client ID trên Google Cloud Console:**
>
> 1. Mở https://console.cloud.google.com/
> 2. Tạo project mới hoặc chọn project có sẵn
> 3. **APIs & Services → Library** — bật:
>    - **Google Analytics Data API** (bắt buộc)
>    - **Google Analytics Admin API** (để discover properties)
> 4. **APIs & Services → Credentials → Create Credentials → OAuth Client ID**
>    - Application type: **Desktop app**
>    - Tên: tuỳ ý (vd: "CRO Report")
>    - Download file JSON → lưu vào `~/Downloads/client_secret.json`
> 5. **OAuth consent screen → Test users** → thêm email Google sẽ dùng

AskUserQuestion: *"Bạn đã download file client_secret.json chưa?"*

Khi user xác nhận, hỏi đường dẫn (mặc định `~/Downloads/client_secret.json`), rồi:

```bash
cd ~/.claude/skills/cro-report && .venv/bin/python manage_accounts.py set-oauth-client ~/Downloads/client_secret.json 2>&1
```

Quay lại **BƯỚC 1**.

---

## BƯỚC 1c — Standalone OAuth + chọn GA4 property

**1c-1.** AskUserQuestion: *"Đặt slug cho site này (vd: elitedental, myblog)"*

**1c-2.** Tạo OAuth URL:

```bash
cd ~/.claude/skills/cro-report && .venv/bin/python scripts/setup_flow.py auth-url --name PROFILE_NAME 2>&1
```

Parse JSON, lấy `auth_url`. Hiển thị:

> **Đăng nhập Google:**
> 1. Click link: [auth_url]
> 2. Đăng nhập bằng Google account có quyền **Read GA4 property**
> 3. Sau khi đăng nhập, browser sẽ báo lỗi **"This site can't be reached"** — đó là bình thường
> 4. **Copy toàn bộ URL** từ address bar (bắt đầu bằng `http://localhost:8766/...`)
> 5. Paste URL đó vào đây

AskUserQuestion: *"Paste URL từ address bar:"* (user nhập vào "Other").

**1c-3.** Hoàn tất OAuth + discover GA4:

```bash
cd ~/.claude/skills/cro-report && .venv/bin/python scripts/setup_flow.py auth-complete --name PROFILE_NAME --redirect-url "URL_USER_PASTE" 2>&1
```

Parse JSON: lấy `ga4_properties` (mỗi item: `id`, `display_name`, `measurement_id`).

**1c-4.** Chọn GA4 property (AskUserQuestion):
- 1 property → chọn tự động
- Nhiều → max 4 options format: *"Display Name (ID: 123) — G-XXXXXXXXXX"*

Lưu `GA4_PROPERTY_ID`, `GA4_MEASUREMENT_ID`.

**1c-5.** Lưu profile:

```bash
cd ~/.claude/skills/cro-report && .venv/bin/python scripts/setup_flow.py save \
  --name PROFILE_NAME \
  --client-name "Client Display Name" \
  --ga4-property-id GA4_PROPERTY_ID \
  --ga4-measurement-id GA4_MEASUREMENT_ID 2>&1
```

→ **BƯỚC 4**.

---

## BƯỚC 2 — Chọn profile (nếu nhiều)

Nếu chỉ 1 profile → chọn tự động.

Nếu nhiều profiles → AskUserQuestion với options = tên các profiles (sắp xếp default lên đầu, hiển thị `_source` để user biết từ đâu).

---

## BƯỚC 3 — Đề xuất re-run với last_run (nếu có)

Nếu `last_run` trong output BƯỚC 1 không rỗng:

AskUserQuestion: *"Tạo lại report với cấu hình lần trước ({client} — {date_preset})?"*
- **Same** → skip sang **BƯỚC 4** với cùng date_range
- **Customize** → tiếp tục **BƯỚC 4** với chọn date mới

---

## BƯỚC 4 — Chọn date range

AskUserQuestion:
- Last 7 days
- **Last 30 days** (default)
- Last 90 days
- Custom (nhập tay)

Custom → AskUserQuestion 2 lần: từ-đến (format YYYY-MM-DD).

---

## BƯỚC 5 — Fetch + generate

```bash
cd ~/.claude/skills/cro-report && .venv/bin/python scripts/main.py generate \
  --profile PROFILE_NAME \
  --date-range last_30_days \
  --open 2>&1
```

(Custom range thay bằng `--start 2026-04-01 --end 2026-04-30`)

Hiển thị progress message ngắn: *"🔄 Đang fetch CRO data từ GA4 ({client_name}, {date_range})..."*

Parse JSON output:

```json
{
  "ok": true,
  "report_path": "/Users/.../reports/elitedental-20260517-1430.html",
  "file_url": "file:///Users/.../reports/elitedental-20260517-1430.html",
  "opened": true,
  "summary": {
    "total_sessions": 25172,
    "total_users": 22893,
    "total_conversions": 19,
    "total_failed_attempts": 0,
    "total_interactions": 0,
    "total_attempts": 19,
    "site_conversion_rate_pct": 0.08,
    "attempt_conversion_rate_pct": 100.0,
    "avg_session_ms": 193501,
    "avg_elapsed_ms": 0,
    "avg_pages_visited": 2.4
  },
  "warnings": []
}
```

Hiển thị cho user:

```
✓ Report đã tạo: ~/.claude/skills/cro-report/reports/elitedental-20260517-1430.html
  (mở trong browser)

Tóm tắt 30 ngày qua:
  Sessions:         25,172  |  Users: 22,893
  Conversions:      19      |  Site CR: 0.08%
  Failures:         0       |  Avg session time: 3m 13s
```

Nếu `summary.total_conversions == 0`:
```
⚠ Chưa có data CRO trong khoảng này. Đảm bảo:
  1. GTM container đã Publish (chứ không chỉ Save version)
  2. Engine snippet đã được paste vào source code website
  3. Đã có ít nhất 1 form submission thực sau khi publish
  4. Custom dimensions cro_* đã register trong GA4 Admin

  Bạn có muốn fetch khoảng dài hơn (90 days) không?
```

Nếu `warnings` có item (vd custom dim chưa register) → hiển thị warning rõ ràng cho user, kèm hướng dẫn fix (vd: chạy `/cro-setup` lại để register dim).

---

## BƯỚC 6 (nâng cao, optional) — Deploy auto-refresh lên server

> **Yêu cầu:** SSH access đến VPS/server riêng, `rsync` trên máy local, server có Python 3.10+ và web server (nginx/apache). Người dùng không có server → bỏ qua bước này, dùng file local là đủ.

Khi user hỏi *"có thể xem report online + tự update không"* → giới thiệu subcommand `deploy`. Skill SSH lên server, copy mình + OAuth credentials, cài cron để chạy `generate` theo schedule. Viewer chỉ cần reload URL.

**Yêu cầu trước khi deploy:**
- SSH host alias đã setup (vd `fsi`) — test bằng `ssh fsi echo ok`
- Server có `python3 >= 3.10` và `rsync`
- Webroot directory (server có quyền ghi)
- Đã chạy `generate` ít nhất 1 lần local (để có credentials refresh token)

**AskUserQuestion:**
- SSH host: (default `fsi`)
- Webroot: (vd `/var/www/btt.com.vn/cro-reports`)
- Public URL prefix: (vd `https://btt.com.vn/cro-reports`)
- Cron schedule: (default `0 */6 * * *` = mỗi 6h, options: `0 * * * *` mỗi giờ, `0 8 * * *` 8h sáng hàng ngày)
- Date range: (default last_30_days)

**Dry-run trước:**

```bash
cd ~/.claude/skills/cro-report && .venv/bin/python scripts/main.py deploy \
  --profile PROFILE_NAME \
  --ssh-host SSH_HOST \
  --webroot REMOTE_WEBROOT \
  --public-url PUBLIC_URL \
  --cron "CRON_SCHEDULE" \
  --date-range DATE_RANGE \
  --dry-run 2>&1
```

Hiển thị plan cho user xác nhận. Nếu OK → bỏ `--dry-run` chạy thật.

**Output thành công:**

```json
{
  "ok": true,
  "plan": {
    "public_url": "https://btt.com.vn/cro-reports/gentis-com-vn.html",
    "cron_schedule": "0 */6 * * *",
    ...
  },
  "steps": [...all steps with ok:true...]
}
```

Cho user: *"✓ Đã deploy. URL: {public_url}. Cron chạy mỗi {schedule}. Log trên server: ~/cro-report-server/cron.log"*

**Update lại deploy** (đổi schedule, đổi date_range, push code mới): chạy lại `deploy` cùng `--ssh-host` + `--webroot` + `--report-name` (nếu khác default) → idempotent, replace cron entry cũ.

**Xoá auto-refresh:** SSH vào server, `crontab -e` xoá dòng có comment `# cro-report:{report_name}`, rồi `rm -rf ~/cro-report-server` (nếu muốn dọn).

---

## Re-run & quản lý

```bash
# List profiles (merged cro-setup + standalone)
cd ~/.claude/skills/cro-report && .venv/bin/python manage_accounts.py list

# Show profile
.venv/bin/python manage_accounts.py show --name elitedental

# Switch default
.venv/bin/python manage_accounts.py default --name elitedental

# Remove standalone profile (không xoá được cro-setup profile từ đây)
.venv/bin/python manage_accounts.py remove --name elitedental

# Re-discover GA4 properties cho standalone profile
.venv/bin/python scripts/setup_flow.py discover --name elitedental
```

---

## Xử lý lỗi

| Lỗi | Fix |
|-----|-----|
| `Python 3.10+ required` | Cài Python từ python.org hoặc brew/apt |
| `OAuth client not configured` | Nếu có cro-setup → reuse OAuth của cro-setup. Nếu standalone → **BƯỚC 1b** |
| `Google Analytics Data API has not been used` (SERVICE_DISABLED) | Bật **Google Analytics Data API** trong GCP project (link `Activate:` có sẵn trong warning). Lưu ý: cro-setup chỉ bật Admin API — cro-report cần thêm Data API |
| `Permission denied` khi list GA4 | Account chưa được cấp quyền Viewer/Editor trên GA4 property |
| `INVALID_ARGUMENT: customEvent:cro_*` trong warnings | Custom dimensions chưa register trong GA4 Admin → chạy `/cro-setup` rồi `/cro-setup apply` lại |
| Browser không tự mở | Skill in `file_url` ra console — user copy/paste vào browser tự mở |
| `Token expired` lặp đi lặp lại | Xoá `credentials/{profile}.json` và setup lại (BƯỚC 1c) |

---

## Caveats (skill KHÔNG làm gì)

- ✅ **Deploy auto-refresh** — có (BƯỚC 6, server-side cron)
- ✅ **Filter date** trong browser — có (chỉ trong khoảng snapshot đã fetch, vd snapshot 90 days → filter được mọi sub-range)
- ❌ Không **real-time** — data refresh theo cron schedule (ko phải mỗi request). Default 6h
- ❌ Không **extend** date range trong browser — nếu snapshot là 30 days, không filter ra ngoài range đó. Phải re-run skill với date_range dài hơn
- ❌ Không **password-protect** file — báo cáo public với ai mở được file
- ❌ Không **A/B test analysis** (defer khi engine có data variant)

Skill **CHỈ** đọc GA4 data và sinh HTML report. Không sửa GA4/GTM (đó là việc của `/cro-setup`).
