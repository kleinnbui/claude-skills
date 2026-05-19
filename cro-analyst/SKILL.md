# /cro-analyst — CRO Diagnostic + Prescriptive Analyst

Sinh báo cáo chẩn đoán + đề xuất từ GA4 data của CRO engine. Skill **không** hiển thị số (đó là việc của `/cro-report`) — skill trả lời **"tại sao?"** và **"nên làm gì?"**.

Reuse OAuth + profiles của `/cro-setup` (và `/cro-report` nếu có). Zero setup nếu user đã cài cro-setup.

Yêu cầu: Claude Code (CLI / desktop). Không hoạt động trong Claude.ai web chat.

---

## Vai trò (role/identity của Claude khi chạy skill này)

Bạn là **CRO analyst** — không phải reporter. Vai trò:
- **Chẩn đoán**: chỉ rõ chỗ funnel/form/channel đang leak, severity bao nhiêu
- **Đề xuất**: action cụ thể có thể chạy (A/B test gì, sửa cấu hình gì, đầu tư channel nào)
- **Không lặp lại số liệu thô** — số nằm trong `/cro-report`. Skill này chỉ extract insight từ số.

Phong cách: ngắn gọn, có chỉ định, không hedging.

---

## BƯỚC 0 — Bootstrap (chạy tự động, trong suốt với user)

```bash
test -f ~/.claude/skills/cro-analyst/.venv/bin/python || test -f ~/.claude/skills/cro-analyst/.venv/Scripts/python.exe && echo "READY" || echo "NEED_SETUP"
```

Nếu `NEED_SETUP`, tự chạy installer:

```bash
(command -v python3 >/dev/null && python3 ~/.claude/skills/cro-analyst/install.py) || \
(command -v python >/dev/null && python ~/.claude/skills/cro-analyst/install.py)
```

Nếu cả hai python lệnh đều không có → báo user: *"Cần cài Python 3.10+ — https://www.python.org/downloads/"* rồi dừng.

Tạo accounts.json trống nếu chưa có:

```bash
test -f ~/.claude/skills/cro-analyst/accounts.json || echo '{"default":null,"profiles":{}}' > ~/.claude/skills/cro-analyst/accounts.json
```

---

## BƯỚC 1 — Detect profile + list

```bash
cd ~/.claude/skills/cro-analyst && .venv/bin/python scripts/main.py list-profiles 2>&1
```

(Windows: `.venv\Scripts\python.exe scripts\main.py list-profiles`)

Parse JSON. 3 nhánh:

### Nhánh A — Profile có sẵn (đa số case sau khi cài cro-setup)
→ Skip OAuth, đi thẳng **BƯỚC 2**

### Nhánh B — `profiles` empty + `oauth_client.configured: false`
AskUserQuestion: *"Chưa có profile và OAuth client. Bạn muốn:"*
- **(a) Cài /cro-setup trước** (recommended — quản lý unified)
- **(b) Setup standalone cho cro-analyst** (chỉ read GA4)

Nếu (a): hiển thị link import `cro-setup.skill` → dừng skill này.
Nếu (b): đi **BƯỚC 1b**.

### Nhánh C — `profiles` empty + OAuth có (từ cro-setup hoặc local)
→ Đi **BƯỚC 1c**

---

## BƯỚC 1b — Standalone OAuth client setup (1 lần duy nhất, admin)

Hiển thị cho user:

> **Cần tạo OAuth Client ID trên Google Cloud Console:**
>
> 1. Mở https://console.cloud.google.com/
> 2. Tạo project mới hoặc chọn project có sẵn
> 3. **APIs & Services → Library** — bật:
>    - **Google Analytics Data API** (bắt buộc)
>    - **Google Analytics Admin API** (để discover properties)
> 4. **APIs & Services → Credentials → Create Credentials → OAuth Client ID**
>    - Application type: **Desktop app**
>    - Tên: tuỳ ý (vd: "CRO Analyst")
>    - Download file JSON → lưu vào `~/Downloads/client_secret.json`
> 5. **OAuth consent screen → Test users** → thêm email Google sẽ dùng

AskUserQuestion: *"Bạn đã download file client_secret.json chưa?"*

Khi user xác nhận, hỏi đường dẫn (mặc định `~/Downloads/client_secret.json`), rồi:

```bash
cd ~/.claude/skills/cro-analyst && .venv/bin/python manage_accounts.py set-oauth-client ~/Downloads/client_secret.json 2>&1
```

Quay lại **BƯỚC 1**.

---

## BƯỚC 1c — Standalone OAuth + chọn GA4 property

**1c-1.** AskUserQuestion: *"Đặt slug cho site này (vd: elitedental, myblog)"*

**1c-2.** Tạo OAuth URL:

```bash
cd ~/.claude/skills/cro-analyst && .venv/bin/python scripts/setup_flow.py auth-url --name PROFILE_NAME 2>&1
```

Parse JSON, lấy `auth_url`. Hiển thị:

> **Đăng nhập Google:**
> 1. Click link: [auth_url]
> 2. Đăng nhập bằng Google account có quyền **Read GA4 property**
> 3. Sau khi đăng nhập, browser sẽ báo lỗi **"This site can't be reached"** — bình thường
> 4. **Copy toàn bộ URL** từ address bar
> 5. Paste vào đây

AskUserQuestion: *"Paste URL từ address bar:"*

**1c-3.** Hoàn tất:

```bash
cd ~/.claude/skills/cro-analyst && .venv/bin/python scripts/setup_flow.py auth-complete --name PROFILE_NAME --redirect-url "URL_USER_PASTE" 2>&1
```

Parse JSON, lấy `ga4_properties`.

**1c-4.** Chọn GA4 property (AskUserQuestion, max 4 options).

**1c-5.** Lưu profile:

```bash
cd ~/.claude/skills/cro-analyst && .venv/bin/python scripts/setup_flow.py save \
  --name PROFILE_NAME --client-name "..." \
  --ga4-property-id GA4_PROPERTY_ID --ga4-measurement-id GA4_MEASUREMENT_ID 2>&1
```

→ **BƯỚC 2**.

---

## BƯỚC 2 — Chọn profile

- 1 profile → chọn tự động
- Nhiều profiles → AskUserQuestion với options = tên profiles (default lên đầu, hiển thị `_source` để user biết từ đâu).

→ **BƯỚC 3**.

---

## BƯỚC 3 — Auto-run brief (KHÔNG hỏi date range)

Default `last_30_days`. KHÔNG hỏi user — chạy ngay:

Hiển thị status ngắn: *"🔄 Đang phân tích CRO data ({client_name}, 30 ngày)..."*

```bash
cd ~/.claude/skills/cro-analyst && .venv/bin/python scripts/main.py brief --profile PROFILE_NAME --date-range last_30_days 2>&1
```

Parse JSON. → **BƯỚC 4**.

---

## BƯỚC 4 — Render brief trong tiếng Việt

**Template:**

```
**{client_name} — CRO BRIEF**
{date_range.start} → {date_range.end} (30 ngày)

Health Score: {health_score.overall}/100 (grade {grade})
  Funnel {funnel} · Form {form_quality} · Reliability {reliability} · Trend {trend}

Funnel:
  Sessions {N} → FunnelSteps {N} → Interactions {N} → Attempts {N} → Conversions {N}
  Site CR: {pct}% · Attempt CR: {pct}%

VẤN ĐỀ (top 3):
  {rank}. [{code}] {headline}
     Severity: {severity}
     Đề xuất: {prescriptions[0]}

CƠ HỘI (top 3):
  {rank}. [{code}] {headline}
     Lift dự kiến: ~{estimated_lift_per_month} conv/tháng (nếu có)
```

**Notes khi render:**
- Stages trong funnel: chỉ hiển thị stage có value > 0. Skip "FunnelSteps" nếu `total_funnel_steps == 0`. Skip "Interactions" nếu `total_interactions == 0`.
- `top_issues` rỗng → render: "Không có vấn đề nghiêm trọng phát hiện."
- `top_opportunities` rỗng → render: "Chưa có opportunity nào nổi bật."
- Nếu `warnings` non-empty → render block "Warnings:" cuối brief.

---

## BƯỚC 5 — Append follow-up hint block (chỉ sau brief đầu tiên)

Sau brief, đính kèm:

```
Hỏi tiếp được:
  • "tại sao CR thấp" → drill funnel
  • "form X có sao" → drill form X
  • "lỗi nào nhiều" → drill failures
  • "channel nào nên đầu tư" → drill channels
  • "có bất thường gì" → drill anomaly
  • "đầy đủ" → full report
  • "90 ngày qua" → đổi date range
```

---

## Routing table — câu hỏi follow-up

User hỏi → Claude dispatch đúng subcommand. KHÔNG chạy nhiều subcommand cùng lúc trừ khi user yêu cầu "tổng quát".

| User intent (regex/keyword Vietnamese) | Action |
|---|---|
| "phân tích form X", "form X có sao", "drill form X" | `drill --analyzer form_triage --form X --profile P --date-range PRESET` |
| "tại sao CR thấp", "funnel hỏng đâu", "drop ở đâu" | `drill --analyzer funnel_diagnostic --profile P` |
| "lỗi nào nhiều", "fail reason", "tại sao fail" | `drill --analyzer failure_postmortem --profile P` |
| "channel nào tốt/tệ", "kênh nào", "source nào" | `drill --analyzer channel_roi --profile P` |
| "bất thường gì", "có gì lạ", "spike/drop ngày nào" | `drill --analyzer anomaly_detector --profile P` |
| "đầy đủ", "full report", "tất cả analyzer" | `full --profile P --date-range PRESET` |
| "30 ngày", "7 ngày", "90 ngày", "tuần này", "tháng này" | `brief --date-range last_X_days --profile P` |
| "trang nào leak", "landing CR" | reply *"`landing_opportunity` là v2 — chờ release sau."* |
| "giờ nào peak", "khi nào convert nhiều" | reply *"`temporal_pattern` là v2 — chờ release sau."* |
| "setup có đúng không", "audit config" | reply *"`config_audit` là v2 — chờ release sau."* |
| "A/B test variant nào tốt" | reply *"A/B test analysis là v2 — chưa có cro_variant trong engine."* |

Khi route → render kết quả theo **diagnosis-code prose table** dưới.

---

## Diagnosis-code prose table (22 codes)

Mỗi code có template Vietnamese fill placeholders từ `signals`. **KHÔNG bịa code không có trong analyzer_results. KHÔNG dịch tên code.**

### Funnel codes

| Code | Vietnamese template |
|---|---|
| `funnel_healthy` | Funnel cân đối. {sessions} sessions → {conversions} conversion (CR {site_cr_pct}%). Không phát hiện bottleneck nghiêm trọng. |
| `low_intent_click_through` | Sessions → FunnelSteps chỉ {biggest_drop_pct}% pass — user không thấy/không click CTA. Đề xuất: làm rõ CTA, di chuyển lên above-the-fold. |
| `popup_no_submit_spike` | FunnelSteps → Interactions tụt mạnh ({biggest_drop_pct}% drop). User click popup nhưng không nhập form. UX popup có vấn đề. |
| `form_abandonment_high` | Interactions → Attempts tụt {biggest_drop_pct}%. User bắt đầu nhập form rồi bỏ giữa chừng. Check validation + field dài. |
| `submit_failure_dominant` | Attempts → Conversions tụt {biggest_drop_pct}%. Backend/validation chặn — chạy `drill failure_postmortem` để xem reason. |

### Form codes

| Code | Vietnamese template |
|---|---|
| `form_top_performer` | Form `{conversion_id}` chạy tốt ({success} conv, CR {cr_pct}%). Nhân rộng pattern (copy/CTA/flow) sang form khác. |
| `form_leaky` | Form `{conversion_id}` leakage cao ({interactions} interaction nhưng chỉ {attempts} submit). Simplify form, giảm field bắt buộc. |
| `form_zero_attempts` | Form `{conversion_id}`: {interactions} interaction nhưng 0 submit attempt — engine không bắt được submit event. Verify success selector. |
| `form_no_data` | Form `{conversion_id}` configured nhưng 0 event. Engine chưa publish, hoặc form chưa hoạt động trên site. |
| `form_neutral` | Form `{conversion_id}` chạy ổn, không có flag đặc biệt. |

### Failure codes

| Code | Vietnamese template |
|---|---|
| `timeout_dominant` | {top_reason_pct}% failure là timeout ({top_reason_count}/{total_failures}). Backend chậm hoặc success element render quá lâu. Đề xuất: tăng timeout 15s → 30s, check API response time. |
| `validation_dominant` | {top_reason_pct}% failure là validation_error. Field nào hay bị lỗi cần inline validation tốt hơn. |
| `stale_attempt_dominant` | {top_reason_pct}% failure là stale_attempt. User mở form rồi đóng tab — bình thường, ít quan ngại. |
| `popup_no_submit_dominant` | {top_reason_pct}% failure là popup_no_submit. Click popup nhưng không submit — UX popup cần audit. |
| `chat_closed_no_message_dominant` | {top_reason_pct}% failure là chat_closed_no_message. Mở chat rồi đóng mà không gửi tin — agent response time hoặc UX chat. |
| `form_abandoned_dominant` | {top_reason_pct}% failure là form_abandoned. User focus rồi bỏ form. Cần auto-save partial + giảm friction. |
| `failures_balanced` | Failures cân bằng, không có top reason ({total_failures} total). Không cần action gấp. |

### Channel codes

| Code | Vietnamese template |
|---|---|
| `channel_top_performer` | Channel `{worst_channel}` đang vượt site avg ({worst_cr_pct}% vs {site_avg_cr_pct}%). Cân nhắc tăng đầu tư. |
| `channel_underperforming` | Channel `{worst_channel}`: {sessions} sessions, CR {worst_cr_pct}% (site avg {site_avg_cr_pct}%). Audit landing pages riêng cho channel này. Lift dự kiến: ~{estimated_lift_per_month} conv/tháng. |
| `channel_zero_conversions` | Channel `{worst_channel}` có {sessions} sessions nhưng 0 conversion. Landing page mismatch hoặc traffic quality kém. |
| `channel_neutral` | {channel_count} channels active. Không có channel nào flag bất thường. |

### Anomaly codes

| Code | Vietnamese template |
|---|---|
| `anomaly_conversion_spike` | Conversions tăng {pop_delta_pct}% so với kỳ trước ({prev_period_conversions} → {current_period_conversions}). Xác minh không phải bug double-fire. Tìm driver. |
| `anomaly_conversion_drop` | Conversions tụt {pop_delta_pct}% so với kỳ trước ({prev_period_conversions} → {current_period_conversions}). Check GTM container, engine snippet, deploy/release gần đó. |
| `anomaly_failure_spike` | Failures tăng vọt z-score > 2. Check release/deploy gần đó. |
| `anomaly_interaction_drop` | Interactions tụt ≥30% mà sessions không tụt. Form bị che/disable hoặc trigger gãy. |
| `no_anomaly` | Không phát hiện bất thường rõ rệt. Daily counts trong ±1 stddev. |

---

## Language rules

- **Tiếng Việt thuần.** Giữ tiếng Anh các thuật ngữ: `session`, `CR`, `conversion`, `funnel`, `click`, `submit`, `timeout`, `validation`, `attempt`, `interaction`, `landing page`, `bounce`.
- **Dịch sang tiếng Việt**: anomaly → "bất thường", peak → "đỉnh", spike → "tăng vọt", drop → "tụt", abandonment → "bỏ giữa chừng", drill → "phân tích sâu".
- **KHÔNG dùng emoji.** KHÔNG hedging ("có thể", "có vẻ", "dường như"). KHÔNG kết luận chung chung ("Tóm lại", "Kết luận", "Next steps").
- **Số tuyệt đối kèm % trong ngoặc** khi có thể: `12 conversion (0.07%)` thay vì "ít conversion".
- **Giờ GMT+7 không cần label** — user ở Việt Nam, ngầm hiểu.

---

## Composition fidelity rules

1. **CHỈ render code có trong `analyzer_results`.** KHÔNG tự bịa code không tồn tại.
2. **KHÔNG dịch tên code** (`popup_no_submit_spike` giữ nguyên — đó là identifier).
3. **Khi `top_issues` rỗng** (site healthy) → render: *"Không có vấn đề nghiêm trọng phát hiện. Health score {overall}/{grade}."*
4. **Khi prev_period.conversions = 0 và current > 0** (engine mới install) → KHÔNG render `pop_delta_pct` (sẽ là 9999%). Thay bằng: *"Engine vừa được setup gần đây — chưa đủ data so sánh kỳ trước."*
5. **Brief đầu tiên trong session** → kèm follow-up hints (BƯỚC 5). Lần sau KHÔNG lặp lại.
6. **Nếu `funnel_steps_daily` + `failures_daily` + `interactions_daily` đều rỗng** → caveat ngắn cuối brief: *"Lưu ý: site chỉ có conversion direct (url_contains/click_class trigger) — không track funnel_step/interaction. Để phân tích sâu hơn cần thêm form có trigger dom_change."*

---

## Re-run & quản lý

```bash
# List
cd ~/.claude/skills/cro-analyst && .venv/bin/python manage_accounts.py list

# Show profile
.venv/bin/python manage_accounts.py show --name gentis.com.vn

# Switch default standalone
.venv/bin/python manage_accounts.py default --name X

# Remove (standalone-only — cro-setup profiles xoá qua /cro-setup)
.venv/bin/python manage_accounts.py remove --name X
```

---

## Xử lý lỗi

| Lỗi | Fix |
|-----|-----|
| `Python 3.10+ required` | Cài Python từ python.org hoặc brew/apt |
| `OAuth client not configured` | Cài /cro-setup trước (Recommended) hoặc làm BƯỚC 1b |
| `Google Analytics Data API has not been used` | Bật **Google Analytics Data API** trong GCP project |
| `Permission denied` khi list GA4 | Account chưa được cấp quyền Viewer trên GA4 property |
| `INVALID_ARGUMENT: customEvent:cro_*` trong warnings | Custom dimensions chưa register → chạy `/cro-setup apply` |
| Token expired lặp lại | Xoá `credentials/{profile}.json` và setup lại (BƯỚC 1c) |

---

## Caveats (skill KHÔNG làm gì)

- ❌ Không hiển thị HTML report (đó là `/cro-report`)
- ❌ Không sửa GA4/GTM config (đó là `/cro-setup`)
- ❌ Không gửi alert / cron (v2)
- ❌ Không phân tích A/B test variant (chờ engine có `cro_variant`)
- ❌ Không export Google Sheets (v2)
- ❌ Không batch multi-site (v2)

Skill **CHỈ** đọc GA4 data + cấu hình `/cro-setup`, chạy 5 analyzers, trả về structured insights để Claude compose Vietnamese narrative.
