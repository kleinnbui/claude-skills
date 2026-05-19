# /cro-analyst — CRO Diagnostic + Prescriptive Analyst

Lớp **chẩn đoán + đề xuất** trên top của `/cro-setup` (đo lường) và `/cro-report` (hiển thị).

- `/cro-setup` → đặt câu hỏi: "cài đặt thế nào?"
- `/cro-report` → đặt câu hỏi: "cái gì đã xảy ra?"
- `/cro-analyst` → đặt câu hỏi: **"tại sao?"** và **"nên làm gì?"**

---

## Tính năng v1 (MVP)

- **5 analyzers** chẩn đoán: funnel bottleneck, form triage, failure postmortem, channel ROI, anomaly detection
- **Health score 0-100** + grade A-F
- **Top 3 issues + Top 3 opportunities** mỗi brief
- **Natural-language Q&A**: hỏi tiếng Việt, skill route đúng analyzer
- **Reuse OAuth + profiles** của `/cro-setup` — zero setup nếu đã có

## Cài đặt

1. Tải file `dist/cro-analyst.skill` từ GitHub repo
2. Claude Code → **⚙ Settings → Skills → + Add skill** → chọn file
3. Skill xuất hiện → gõ `/cro-analyst` trong chat

Lần đầu tự cài Python venv (~30-60s). Nếu đã có `/cro-setup` thì skill auto-detect profile, KHÔNG cần OAuth lại.

## Yêu cầu

- Claude Code desktop/CLI (không hoạt động trên claude.ai web)
- Python 3.10+
- (Optional but recommended) `/cro-setup` đã cài để reuse profile

## Sử dụng

**Lần đầu:**
```
/cro-analyst
```
→ Skill tự fetch GA4 30 ngày gần nhất, chạy 5 analyzers, render brief tiếng Việt với health score + top 3 issues + top 3 opportunities + follow-up hints.

**Câu hỏi follow-up (tiếng Việt):**
```
> tại sao CR thấp                → drill funnel
> form popup_tu_van có sao        → drill form_triage --form popup_tu_van
> lỗi nào nhiều                   → drill failure_postmortem
> channel nào nên đầu tư           → drill channel_roi
> có bất thường gì không           → drill anomaly_detector
> đầy đủ                          → full report (all analyzers, all flagged codes)
> 90 ngày qua                     → brief --date-range last_90_days
```

## Defer to v2

- `landing_opportunity` analyzer (high-traffic + low-CR pages)
- `temporal_pattern` analyzer (peak hours, day-of-week)
- `config_audit` analyzer (so cấu hình `/cro-setup` vs GA4 thực tế)
- HTML insight report
- A/B test variant statistical analysis
- `--all-profiles` batch mode

---

## Architecture

```
cro-analyst/
├── SKILL.md                # State machine + Vietnamese composition guide
├── install.py              # Python venv bootstrap
├── manage_accounts.py      # Profile CRUD
├── requirements.txt
└── scripts/
    ├── auth.py             # OAuth (fallback chain: local → cro-setup)
    ├── config.py           # Merge cro-setup + standalone profiles
    ├── setup_flow.py       # Two-phase OAuth (no browser.open)
    ├── ga4_fetcher.py      # 16 GA4 queries
    ├── analyzers.py        # 5 pure functions + health score
    └── main.py             # CLI: list-profiles | brief | full | drill
```

`scripts/auth.py`, `config.py`, `setup_flow.py`, `ga4_fetcher.py` được copy verbatim từ `/cro-report`. Mỗi skill standalone — đồng bộ thủ công khi fetcher thay đổi.

## Subcommands

```bash
.venv/bin/python scripts/main.py list-profiles
.venv/bin/python scripts/main.py brief --profile P --date-range last_30_days
.venv/bin/python scripts/main.py full --profile P --date-range last_30_days
.venv/bin/python scripts/main.py drill --analyzer form_triage --form X --profile P
.venv/bin/python scripts/main.py drill --analyzer funnel_diagnostic --profile P
.venv/bin/python scripts/main.py drill --analyzer failure_postmortem --profile P
.venv/bin/python scripts/main.py drill --analyzer channel_roi --profile P
.venv/bin/python scripts/main.py drill --analyzer anomaly_detector --profile P
```
