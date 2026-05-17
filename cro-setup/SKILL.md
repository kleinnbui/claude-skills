---
name: cro-setup
description: Tự động cài đặt CRO measurement (14 GTM Data Layer Variables + 2 GTM tags + 1 trigger + 10 GA4 Custom Dimensions + 3 GA4 Custom Metrics + 1 Key Event) qua GTM API + GA4 Admin API. User chỉ cần OAuth Google, chọn container/property, trả lời wizard, KHÔNG click thủ công. Mirror 1:1 với cro-wizard.html v2.6. Multi-profile, zero Terminal copy-paste, save-version-only (không auto publish).
dependencies: google-analytics-admin>=0.22.0, google-api-python-client>=2.100.0, google-auth>=2.23.0, google-auth-oauthlib>=1.1.0
---

# /cro-setup — CRO Measurement Auto-Installer

Tự động tạo 14 DLV + 1 trigger + 2 tags trên GTM và 10 Custom Dimensions + 3 Custom Metrics + 1 Key Event trên GA4 trong vài giây. Yêu cầu Claude Code (CLI / desktop). Không hoạt động trong Claude.ai web chat.

---

## BƯỚC 0 — Bootstrap (chạy tự động, trong suốt với user)

Kiểm tra Python venv (scripts được ship sẵn trong file .skill, chỉ cần setup venv lần đầu):

```bash
test -f ~/.claude/skills/cro-setup/.venv/bin/python && echo "READY" || echo "NEED_SETUP"
```

Nếu `NEED_SETUP` → in trước cho user biết, rồi chạy tự động (không cần hỏi):

> ⏳ Setup môi trường Python lần đầu (cài 4 package Google API, ~30s)...

```bash
bash ~/.claude/skills/cro-setup/install.sh 2>&1 | tail -5
```

Tạo accounts.json trống nếu chưa có:

```bash
test -f ~/.claude/skills/cro-setup/accounts.json || echo '{"default":null,"profiles":{}}' > ~/.claude/skills/cro-setup/accounts.json
```

---

## BƯỚC 1 — List profiles

```bash
cd ~/.claude/skills/cro-setup && .venv/bin/python manage_accounts.py list 2>&1
```

Parse output:
- Có **"OAuth client: NOT CONFIGURED"** **VÀ** **"No profiles yet"** → **Bước 1a** (welcome) rồi **Bước 1b**
- Có **"OAuth client: NOT CONFIGURED"** (đã có profile) → **Bước 1b**
- **No profiles yet** (đã có OAuth client) → thẳng **Bước 3b** (thêm mới)
- Có profiles → **Bước 2**

---

## BƯỚC 1a — Welcome (chỉ hiện lần đầu tiên user dùng skill)

Hiển thị nguyên văn cho user:

> 👋 **Chào! `/cro-setup` sẽ giúp bạn cài full CRO measurement (GTM + GA4) trong ~5 phút.**
>
> **Bạn cần:**
> - Google account có quyền **Edit GTM container** + **Edit GA4 property**
> - File `client_secret.json` từ Google Cloud Console (mình sẽ hướng dẫn tạo nếu chưa có)
>
> **Toàn bộ quá trình:**
> 1. **Setup OAuth client** (1 lần duy nhất, dùng chung cho mọi site sau này) — ~3 phút
> 2. **Login Google + chọn GTM container + GA4 property** — ~1 phút
> 3. **Trả lời wizard** (forms, conversions, A/B tests) — ~3–5 phút
> 4. **Preview + Apply** → tạo GTM version (**KHÔNG auto publish** — bạn tự QA + Publish) — ~30s
>
> Bắt đầu nhé. Đi sang setup OAuth client trước.

Rồi sang **Bước 1b**.

---

## BƯỚC 1b — Setup OAuth Client (1 lần duy nhất, admin)

Hiển thị cho user:

> **Cần tạo OAuth Client ID trên Google Cloud Console (1 lần duy nhất):**
>
> 1. Mở https://console.cloud.google.com/
> 2. Tạo project mới hoặc chọn project có sẵn
> 3. **APIs & Services → Library** — bật 2 API:
>    - **Tag Manager API**
>    - **Google Analytics Admin API**
> 4. **APIs & Services → Credentials → Create Credentials → OAuth Client ID**
>    - Application type: **Desktop app**
>    - Tên: tuỳ ý (vd: "CRO Setup")
>    - Download file JSON → lưu vào `~/Downloads/client_secret.json`
> 5. **OAuth consent screen → Test users** → thêm email Google sẽ dùng để cài đặt

AskUserQuestion: *"Bạn muốn cung cấp file client_secret.json theo cách nào?"* với 3 options:

1. **"Tôi có path file trên máy"** (Recommended — an toàn nhất, không lộ secret vào conversation log)
2. **"Tôi sẽ attach file vào chat"**
3. **"Tôi sẽ paste nội dung JSON"**

### Case 1 — Path file
Hỏi đường dẫn (mặc định `~/Downloads/client_secret.json`), rồi:
```bash
cd ~/.claude/skills/cro-setup && .venv/bin/python manage_accounts.py set-oauth-client PATH 2>&1
```

### Case 2 + 3 — Attach hoặc Paste JSON
Khi đã có nội dung JSON trong context (từ file attach hoặc user paste):

1. **Validate JSON**: parse được + chứa key `installed` hoặc `web` + trong đó có `client_id` và `client_secret`. Nếu fail → báo user + hỏi lại.
2. **Write trực tiếp vào file đích** (giữ nguyên format đầy đủ với `auth_uri`, `token_uri`...):
   ```
   Write tool → ~/.claude/skills/cro-setup/oauth_client.json
   ```
3. **chmod 600**:
   ```bash
   chmod 600 ~/.claude/skills/cro-setup/oauth_client.json
   ```
4. **Update accounts.json** — set `oauth_client: "oauth_client.json"`. Dùng Python one-liner để merge an toàn:
   ```bash
   cd ~/.claude/skills/cro-setup && .venv/bin/python -c "import json; from pathlib import Path; p=Path('accounts.json'); d=json.loads(p.read_text()) if p.exists() else {'default':None,'profiles':{}}; d['oauth_client']='oauth_client.json'; p.write_text(json.dumps(d,indent=2,ensure_ascii=False))"
   ```
5. **Cảnh báo bảo mật** cho user:
   > ⚠️ `client_secret` đã được lưu trong conversation history. Cân nhắc gõ `/clear` sau khi setup xong nếu session này có thể bị share.
6. **Verify** bằng cách chạy lại list:
   ```bash
   cd ~/.claude/skills/cro-setup && .venv/bin/python manage_accounts.py list 2>&1 | head -3
   ```
   Phải thấy `OAuth client: OK`.

Quay lại **Bước 1**.

---

## BƯỚC 2 — Chọn profile

Dùng AskUserQuestion với options = tên các profiles + option cuối **"Thêm site mới"**.

- Profile có sẵn → lưu PROFILE_NAME → **Bước 4** (skip OAuth)
- "Thêm site mới" → **Bước 3b**

---

## BƯỚC 3b — Thêm site mới (OAuth + chọn GTM/GA4)

**3b-1.** AskUserQuestion: *"Đặt slug cho site này (vd: elitedental, myblog — không dấu cách, không tiếng Việt có dấu)"*

**3b-2.** Tạo OAuth URL:

```bash
cd ~/.claude/skills/cro-setup && .venv/bin/python scripts/setup_flow.py auth-url --name PROFILE_NAME 2>&1
```

Parse JSON, lấy `auth_url`. Hiển thị:

> **Đăng nhập Google:**
> 1. Click link: [auth_url]
> 2. Đăng nhập bằng Google account có quyền **Edit GTM container** + **Edit GA4 property**
> 3. Sau khi đăng nhập, browser sẽ báo lỗi **"This site can't be reached"** — đó là bình thường
> 4. **Copy toàn bộ URL** từ address bar (bắt đầu bằng `http://localhost:8765/...`)
> 5. Paste URL đó vào đây

AskUserQuestion: *"Paste URL từ address bar:"* (user nhập vào "Other").

**3b-3.** Hoàn tất OAuth + discover. In status trước khi chạy:

> ⏳ Đang xác thực và quét GTM containers + GA4 properties bạn có quyền (~5–15s)...

```bash
cd ~/.claude/skills/cro-setup && .venv/bin/python scripts/setup_flow.py auth-complete --name PROFILE_NAME --redirect-url "URL_USER_PASTE" 2>&1
```

Parse JSON: lấy `gtm_containers` (mỗi item có `account_id`, `account_name`, `container_id`, `container_name`, `public_id`) và `ga4_properties` (mỗi item có `id`, `display_name`, `measurement_id`).

**3b-4.** Chọn GTM container (AskUserQuestion):
- 1 container → chọn tự động
- Nhiều → max 4 options format: *"Container Name (GTM-XXXXXXX) — Account Name"*

Lưu `GTM_ACCOUNT_ID`, `GTM_CONTAINER_ID`, `GTM_PUBLIC_ID`.

**3b-5.** List workspaces:

```bash
cd ~/.claude/skills/cro-setup && .venv/bin/python scripts/setup_flow.py workspaces --name PROFILE_NAME --account-id GTM_ACCOUNT_ID --container-id GTM_CONTAINER_ID 2>&1
```

Chọn workspace tên "Default Workspace" mặc định, hoặc AskUserQuestion nếu có nhiều. Lưu `GTM_WORKSPACE_ID`.

**3b-6.** Chọn GA4 property (AskUserQuestion):
- 1 property → chọn tự động
- Nhiều → max 4 options format: *"Display Name (ID: 123) — G-XXXXXXXXXX"*

Lưu `GA4_PROPERTY_ID`, `GA4_MEASUREMENT_ID`. Nếu property không có web data stream (measurement_id rỗng), hỏi user nhập tay (vd `G-ABC123XYZ`).

**3b-7.** Lưu profile:

```bash
cd ~/.claude/skills/cro-setup && .venv/bin/python scripts/setup_flow.py save \
  --name PROFILE_NAME \
  --client-name "Client Display Name" \
  --gtm-account-id GTM_ACCOUNT_ID \
  --gtm-container-id GTM_CONTAINER_ID \
  --gtm-public-id GTM_PUBLIC_ID \
  --gtm-workspace-id GTM_WORKSPACE_ID \
  --ga4-property-id GA4_PROPERTY_ID \
  --ga4-measurement-id GA4_MEASUREMENT_ID 2>&1
```

→ **Bước 4**.

---

## BƯỚC 4 — Wizard Q&A (config CRO)

Đầu tiên kiểm tra config có sẵn cho profile:

```bash
ls ~/.claude/skills/cro-setup/configs/*.json 2>/dev/null
```

**Nếu có file matching profile** → AskUserQuestion với 4 options:

1. **"Dùng config có sẵn → Preview & Apply"** → load file đó → **Bước 5**
2. **"Sửa config (thêm/xóa form, other conversion...)"** → **Bước 4-edit**
3. **"Chỉ cập nhật engine (fix bug, tính năng mới)"** → apply engine-only → **Bước 6-engine**
4. **"Tạo config mới từ đầu"** → full wizard bên dưới

**Nếu không có config** → tạo mới, đi qua **5 step**:

---

### BƯỚC 4-edit — Sửa config có sẵn

Load và hiển thị JSON hiện tại cho user xem (in ra dạng readable). AskUserQuestion: *"Muốn sửa phần nào?"*:
- **"Forms"** → chạy lại Step 2 (forms wizard), **replace** toàn bộ mảng `forms` trong config cũ
- **"Other conversions"** → chạy lại Step 3, replace mảng `others`
- **"A/B Tests"** → chạy lại Step 4, replace mảng `abTests`
- **"Project info (tên client)"** → hỏi lại tên, update `project.clientName`

Sau khi sửa → save config lại (cùng filename) → **Bước 5**.

---

### BƯỚC 6-engine — Engine-only update (không qua wizard)

Dùng khi engine.py đã thay đổi (fix debug flag, tính năng mới...) nhưng config forms/others không đổi.

```bash
cd ~/.claude/skills/cro-setup && .venv/bin/python scripts/main.py apply --profile PROFILE_NAME --config CONFIG_FILE --engine-only 2>&1
```

Chỉ update tag `[CRO] Journey Tracker`, tạo version mới. Hiển thị kết quả như **Bước 6** rồi dừng.

---

### Step 1 — Project info

Hỏi user (text input): *"Tên client/site này là gì? (vd: Elite Dental)"*

Lưu vào in-memory JSON:
```json
{
  "version": "1.0",
  "project": {"clientName": "...", "gtmContainerId": "GTM_PUBLIC_ID", "ga4PropertyId": "GA4_PROPERTY_ID"},
  "forms": [], "others": [], "abTests": []
}
```

### Step 2 — Forms (lặp)

AskUserQuestion: *"Site có form lead-gen không? (form liên hệ, đăng ký, đặt hàng...)"* (yes/no/skip).

Nếu có, lặp với mỗi form:

a. **Tên form** (text input, snake_case): pattern `^[a-z][a-z0-9_]{1,40}$`. Vd: `footer_form`, `popup_main`.

b. **Trigger type** (AskUserQuestion, 4 options):
   - `dom_change` — Element thông báo thành công xuất hiện sau submit (mặc định, dùng nhiều nhất)
   - `cf7_class` — WordPress Contact Form 7 (auto detect `.wpcf7-mail-sent-ok`)
   - `thank_you_url` — Redirect sang thank-you page
   - `button_click` — Click button đo lường ngay (không cần success element)
   - `form_submit` — Form submit event (vanilla)

c. Các field bổ sung tùy `triggerType`:
   - **dom_change/button_click/form_submit**: hỏi `formSelector` (CSS selector của form, vd `#contact-form`), `successSelector` (vd `.success-msg`), optional `validationErrorSelector` (default `.error-text:not(:empty)`), optional `timeout` (default 15000), optional `successGlobal` (true nếu success element ngoài form scope).
   - **cf7_class**: hỏi `formSelector` (vd `.wpcf7-form`). CF7 defaults: success class `wpcf7-mail-sent-ok`, fail classes `wpcf7-mail-sent-ng,wpcf7-validation-errors,wpcf7-spam-blocked`, response selector `.wpcf7-response-output` — chỉ hỏi nếu user muốn override.
   - **thank_you_url**: hỏi `thankYouPath` (vd `/thank-you`) hoặc/và `thankYouParam` (vd `submissionGuid`). Cần ít nhất 1.
     - **HubSpot embed**: nếu form dùng `hbspt.forms.create()`, hỏi thêm `hubspotFormId` (UUID từ HubSpot, vd `a8ad54d4-...`). Engine sẽ detect submit qua `hsFormCallback` postMessage thay vì DOM event. Bắt buộc khi ≥2 form HubSpot share cùng thank-you URL.
     - **Validation**: Nếu user paste URL có `?` (vd `/thank-you?submissionGuid=`), tách thành `thankYouPath=/thank-you` và `thankYouParam=submissionGuid` — `save-config` cũng tự động tách.
     - **Auto requireAttempt**: Nếu ≥2 forms dùng chung `thankYouPath`, `save-config` tự động set `requireAttempt: true` cho tất cả và báo trong `warnings[]`. Không cần hỏi user.

d. AskUserQuestion: *"Thêm form nữa?"*. Loop tới khi user dừng.

### Step 3 — Other conversions (lặp)

AskUserQuestion: *"Có sự kiện khác cần đo (gọi điện, Zalo/Messenger, button CTA, view thank-you page...)?"*.

Nếu có, lặp:

a. **Tên** (snake_case): vd `phone_click`, `zalo_click`.
b. **Trigger type** (6 options):
   - `url_contains` — Link có href chứa pattern (vd `tel:`, `mailto:`, `zalo.me`)
   - `text_contains` — Element có text chứa pattern (vd `Chat Zalo`, `Messenger`)
   - `click_class` — Click element có class chứa pattern (vd `cta-buy`)
   - `page_url_contains` — Page-view khi URL chứa pattern (vd `/cam-on`)
   - `data_attribute` — Click element có data-* attribute khớp (vd `data-test-id=chat-send-button`)
   - `hubspot_chat` — HubSpot Chat widget, detect qua `HubSpotConversations.on('conversationStarted')`. **Không cần pattern.**
c. **Pattern**: text user nhập. Bỏ qua nếu `hubspot_chat`.

Loop.

### Step 4 — A/B Tests (lặp, optional)

AskUserQuestion: *"Có muốn cài A/B test không?"* (yes/no, default no).

Nếu có, lặp:
- `testId` (snake_case, vd `footer_popup_v1`)
- `pages` (regex, default `.*`)
- `variants` (CSV ≥ 2, vd `control,variant_b`)
- `split` (CSV %, sum = 100, vd `50,50`)

### Step 5 — Hiển thị JSON config

In ra cho user xem (compact JSON, có thể trim phần engine), rồi AskUserQuestion: *"Lưu config + xem preview?"* (yes/no).

Lưu config qua stdin:

```bash
cd ~/.claude/skills/cro-setup && echo 'CONFIG_JSON' | .venv/bin/python scripts/main.py save-config --profile PROFILE_NAME 2>&1
```

→ **Bước 5**.

---

## BƯỚC 5 — Preview (dry-run)

In status trước khi chạy:

> ⏳ Đang kiểm tra trạng thái GTM workspace + GA4 property hiện tại (~5–10s)...

```bash
cd ~/.claude/skills/cro-setup && .venv/bin/python scripts/main.py preview --profile PROFILE_NAME --config configs/PROFILE-CLIENT.json 2>&1
```

Output JSON có `summary`, `gtm_plan`, `ga4_plan`, `gtm_url`, `engine_size_bytes`. **Không in raw JSON** — trình bày dạng bảng gọn:

```
GTM: https://tagmanager.google.com/#/container/accounts/.../workspaces/N
  14 Data Layer Variables    CREATE ×14
  1  Trigger                 CREATE ×1
  2  Tags                    CREATE ×2  (+ GA4 Config nếu chưa có)

GA4: properties/123
  10 Custom Dimensions       CREATE ×10
  3  Custom Metrics          CREATE ×3
  1  Key Event               CREATE ×1

Engine: ~25 KB
```

Nếu re-run (UPDATE/NO_OP > 0) → nêu rõ số NO_OP để user biết phần nào đã có sẵn.

AskUserQuestion: *"Apply ngay? (sẽ tạo GTM version nhưng KHÔNG publish — bạn phải tự QA và bấm Publish trong UI)"* (Apply / Cancel).

---

## BƯỚC 6 — Apply

In status trước khi chạy:

> ⏳ Đang tạo 14 DLV + 2 tags + 10 dimensions + 3 metrics + 1 key event + GTM version (~10–30s)...

```bash
cd ~/.claude/skills/cro-setup && .venv/bin/python scripts/main.py apply --profile PROFILE_NAME --config configs/PROFILE-CLIENT.json 2>&1
```

Parse JSON. Output có `gtm.gtm_url` — **in link clickable ngay**. Hiển thị:

```
APPLY DONE
GTM version: cro-setup YYYYMMDD-HHMM (ID: 42)
  N CREATE / M UPDATE / K NO_OP
  → https://tagmanager.google.com/#/container/accounts/.../workspaces/N

GA4: N dimensions, N metrics, N key event

BƯỚC TIẾP THEO:
  1. Click link GTM trên → Preview (Tag Assistant) → load trang test → submit form thật
  2. Kiểm tra DataLayer tab: thấy event conversion_success → QA pass
  3. Submit → Publish container thủ công
  4. GA4 → DebugView → submit với ?gtm_debug=1 → verify cro_* params
  5. Đợi 24-48h → GA4 Reports → Events → conversion_success
```

Nếu `compiler_error: true` → cảnh báo user, hiển thị `sync_status` để debug.

Nếu output có `warnings[]` từ `save-config` (vd auto requireAttempt, thankYouPath tách) → hiển thị warnings trước khi apply để user biết.

---

## Re-run & quản lý

```bash
# List
cd ~/.claude/skills/cro-setup && .venv/bin/python manage_accounts.py list

# Show profile
.venv/bin/python manage_accounts.py show --name elitedental

# Switch default
.venv/bin/python manage_accounts.py default --name elitedental

# Remove (xóa profile + token)
.venv/bin/python manage_accounts.py remove --name elitedental

# Re-discover GTM/GA4 cho profile
.venv/bin/python scripts/setup_flow.py discover --name elitedental
```

Re-run `/cro-setup` với profile có sẵn → tự skip OAuth, hỏi config (có thể dùng config cũ trong `configs/`).

---

## Xử lý lỗi

| Lỗi | Fix |
|-----|-----|
| `OAuth client not configured` | **Bước 1b** |
| `Permission denied` khi list GTM | Account chưa được invite vào GTM container (cần quyền Edit hoặc Publish) |
| `Insufficient permissions` GA4 | Account cần role Editor/Administrator trên GA4 property |
| API not enabled | GCP → APIs & Services → bật Tag Manager API + Google Analytics Admin API |
| `compiler_error: true` ở apply | GTM container có tag/trigger reference invalid → check `sync_status.mergeConflict` |
| Một dimension có cùng displayName nhưng khác parameterName | Skill skip (NO_OP). User cần xóa thủ công trong GA4 Admin trước nếu muốn re-create |
| GA4 property không có web data stream → measurement_id rỗng | Hỏi user nhập tay `G-XXXXXXXXXX` |

---

## Caveats (skill KHÔNG làm gì)

- ❌ Inject GTM container snippet (`<script>...gtm.start...</script>`) vào website — user tự dán
- ❌ Publish GTM container — user tự QA Preview rồi bấm Publish
- ❌ Inject page-level `dataLayer.push()` cho `user_type`, `page_category` vào website code
- ❌ Cài Consent Mode banner
- ❌ Setup sGTM hosting

Skill **CHỈ** tạo GTM artifacts + GA4 admin definitions. Phần engine code đã được embed vào `[CRO] Journey Tracker` tag — sau khi user paste GTM snippet lên site và publish container, engine sẽ chạy.
