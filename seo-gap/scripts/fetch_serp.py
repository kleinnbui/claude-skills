#!/usr/bin/env python3
"""Dựng tập đối thủ cho một cụm từ khóa.

Nguồn ưu tiên: file check top có SERP đầy đủ > Chrome MCP tra trực tiếp > Ahrefs MCP.
Script này xử lý nguồn 1. Nguồn 2 và 3 do tầng trên gọi rồi truyền vào qua --serp-json.

excluded bắt buộc có, không được im lặng loại bỏ.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path.home() / ".claude" / "skills" / "seo-doctor" / "scripts"))
from common import emit, fail, log  # noqa: E402

EXCLUDE_PATTERNS = {
    "dien_dan": ["forum", "diendan", "voz.vn", "otofun", "webtretho", "tinhte.vn"],
    "mang_xa_hoi": ["facebook.com", "tiktok.com", "instagram.com", "twitter.com", "x.com",
                    "linkedin.com", "pinterest.com", "threads.net"],
    "san_thuong_mai": ["shopee.vn", "lazada.vn", "tiki.vn", "sendo.vn", "amazon.", "alibaba."],
    "video": ["youtube.com", "youtu.be", "vimeo.com"],
    "bach_khoa": ["wikipedia.org", "wikimedia.org"],
}

DOMAIN_TYPES = {
    "nha_san_xuat_vat_lieu": [],
    "cong_ty_xay_dung": [],
    "kien_truc": [],
    "trang_tong_hop": [],
    "san": [],
}


def domain_of(url: str) -> str:
    return url.split("//")[-1].split("/")[0].lower().removeprefix("www.")


def classify_exclusion(dom: str) -> str | None:
    """Khớp theo domain chính xác hoặc subdomain, KHÔNG khớp chuỗi con.

    Khớp chuỗi con gây loại nhầm: "duraflex.com.vn" chứa "x.com" nên bị coi là mạng xã hội.
    Đã gặp thật khi chạy trên dữ liệu vlxd.
    """
    for reason, patterns in EXCLUDE_PATTERNS.items():
        for pat in patterns:
            pat = pat.rstrip(".")
            if dom == pat or dom.endswith("." + pat) or dom.startswith(pat + "."):
                return reason
    return None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--keywords", required=True, help="Danh sách từ khóa mục tiêu, cách nhau dấu phẩy")
    ap.add_argument("--rank-file", help="Output JSON của parse_rank.py (seo-doctor)")
    ap.add_argument("--serp-json", help="SERP do Chrome MCP hoặc Ahrefs MCP lấy, dạng {kw: [{position, url}]}")
    ap.add_argument("--own-domain", required=True)
    ap.add_argument("--region", default="Google Vietnam")
    ap.add_argument("--max-competitors", type=int, default=8)
    ap.add_argument("--crawl-date")
    ap.add_argument("--out")
    args = ap.parse_args()

    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]
    if not keywords:
        fail("Danh sách từ khóa rỗng.")

    serp: dict[str, list[dict]] = {}
    source = None
    crawl_date = args.crawl_date

    if args.serp_json:
        raw = json.loads(Path(args.serp_json).expanduser().read_text(encoding="utf-8"))
        serp = raw.get("serp", raw)
        source = raw.get("source", "chrome_mcp")
        crawl_date = crawl_date or raw.get("crawl_date")
    elif args.rank_file:
        raw = json.loads(Path(args.rank_file).expanduser().read_text(encoding="utf-8"))
        if not raw.get("serp"):
            fail("File check top không chứa SERP đối thủ, chỉ có vị trí của web mình. "
                 "Không dựng được tập đối thủ. Cần file có top 10 đầy đủ mọi domain, "
                 "hoặc dùng Chrome MCP tra SERP thật rồi truyền qua --serp-json.",
                 tool=raw.get("tool"))
        latest = (raw.get("dates") or [None])[-1]
        for kw, snaps in raw["serp"].items():
            if kw in keywords or not keywords:
                serp[kw] = snaps.get(latest, [])
        source = "rank_file"
        crawl_date = crawl_date or latest
    else:
        fail("Cần một trong hai: --rank-file (file check top có SERP) "
             "hoặc --serp-json (SERP do Chrome MCP lấy).")

    missing = [k for k in keywords if k not in serp]
    if missing:
        log(f"CẢNH BÁO: không có dữ liệu SERP cho {len(missing)} từ khóa: {', '.join(missing[:5])}")

    own = args.own_domain.lower().removeprefix("www.")
    stats: dict[str, dict] = defaultdict(
        lambda: {"positions": {}, "top3_count": 0, "appears_for": 0, "url": None})
    excluded: list[dict] = []
    seen_excluded: set[str] = set()

    for kw, entries in serp.items():
        for e in entries or []:
            url = e.get("url") or e.get("domain") or ""
            dom = domain_of(url) if "//" in url else str(e.get("domain", url)).lower().removeprefix("www.")
            if not dom or dom == own:
                continue
            reason = classify_exclusion(dom)
            if reason:
                if dom not in seen_excluded:
                    excluded.append({"domain": dom, "reason": reason})
                    seen_excluded.add(dom)
                continue
            pos = e.get("position")
            s = stats[dom]
            s["positions"][kw] = pos
            s["appears_for"] += 1
            s["url"] = s["url"] or (url if "//" in url else None)
            if pos and int(pos) <= 3:
                s["top3_count"] += 1

    ranked = sorted(stats.items(), key=lambda kv: (-kv[1]["top3_count"], -kv[1]["appears_for"]))
    kept = ranked[:args.max_competitors]

    trimmed = None
    if len(ranked) > args.max_competitors:
        trimmed = {"from": len(ranked), "to": args.max_competitors,
                   "criteria": "top3_count giảm dần, rồi appears_for giảm dần"}
        log(f"Đã cắt tập đối thủ từ {len(ranked)} xuống {args.max_competitors}")

    own_positions = {}
    for kw, entries in serp.items():
        for e in entries or []:
            url = e.get("url") or e.get("domain") or ""
            dom = domain_of(url) if "//" in url else str(e.get("domain", url)).lower().removeprefix("www.")
            if dom == own:
                own_positions[kw] = e.get("position")

    emit({
        "keywords": keywords,
        "keywords_without_serp": missing,
        "source": source,
        "crawl_date": crawl_date,
        "region": args.region,
        "own_domain": own,
        "own_positions": own_positions,
        "competitors": [
            {"domain": d, "url": s["url"], "domain_type": None,
             "positions": s["positions"], "top3_count": s["top3_count"],
             "appears_for": s["appears_for"]}
            for d, s in kept],
        "excluded": excluded,
        "excluded_note": ("Diễn đàn, mạng xã hội, sàn, video, bách khoa bị loại khỏi bảng đo vì "
                          "khác loại nội dung nên so số từ và số ảnh không có nghĩa. "
                          "Tỷ lệ loại này cao trong top 10 là phát hiện riêng, nêu ở phần gap."),
        "trimmed": trimmed,
        "domain_type_note": ("domain_type để null. Model phân loại thủ công theo danh mục: "
                             + ", ".join(DOMAIN_TYPES)),
    }, args.out)


if __name__ == "__main__":
    main()
