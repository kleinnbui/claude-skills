#!/usr/bin/env python3
"""Crawl và đo 15 chỉ số + ma trận mật độ cụm từ.

Áp dụng CÙNG MỘT cách đo cho mọi trang trong tập. Đo mình một kiểu, đo đối thủ kiểu khác
thì bảng so sánh vô giá trị.

blocked bắt buộc có. Model phải nêu số trang đo được thực tế trong báo cáo.
headings bắt buộc có — dùng để tìm gap SERP.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import unicodedata
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse

import requests
from lxml import html as lxml_html

sys.path.insert(0, str(Path.home() / ".claude" / "skills" / "seo-doctor" / "scripts"))
from common import emit, fail, log  # noqa: E402

UA = "Mozilla/5.0 (compatible; seo-gap/1.0; +phan-tich-khoang-cach)"
TIMEOUT = 25
DROP_TAGS = ["nav", "header", "footer", "aside", "script", "style", "noscript", "form"]
DROP_CLASS_TOKENS = {"menu", "nav", "navbar", "navigation", "footer", "sidebar", "breadcrumb",
                     "breadcrumbs", "related", "comment", "comments", "widget", "banner",
                     "popup", "modal", "cookie", "cookies", "topbar", "megamenu"}


def norm(text: str) -> str:
    text = unicodedata.normalize("NFC", text or "")
    return re.sub(r"\s+", " ", text).strip().lower()


def _words(node) -> int:
    return len(re.findall(r"\w+", node.text_content(), flags=re.UNICODE))


def main_content(doc):
    """Nội dung chính = phần bài viết, loại menu, chân trang, thanh bên, khối liên quan.

    Hai lớp bảo vệ chống cắt nhầm — đã gặp thật: một trang 41.558 từ bị cắt còn 686 (2%)
    vì có div class chứa chuỗi "banner", xoá cả cây con chứa bài viết.
    1. Khớp class theo TOKEN, không khớp chuỗi con.
    2. Nếu sau khi lọc còn dưới 30% số từ ban đầu thì trả lại bản chỉ bỏ thẻ khung.
    """
    before = _words(doc)
    for tag in DROP_TAGS:
        for node in doc.xpath(f"//{tag}"):
            if node.getparent() is not None:
                node.getparent().remove(node)
    skeleton = _words(doc)

    import copy
    trimmed = copy.deepcopy(doc)
    for node in trimmed.xpath("//*[@class]"):
        tokens = set(re.split(r"[\s_-]+", (node.get("class") or "").lower()))
        if tokens & DROP_CLASS_TOKENS and node.getparent() is not None:
            node.getparent().remove(node)

    base = trimmed if (skeleton and _words(trimmed) >= skeleton * 0.3) else doc
    for xp in ["//article", "//main", "//*[@id='content']", "//*[contains(@class,'entry-content')]",
               "//*[contains(@class,'post-content')]", "//*[contains(@class,'article-content')]"]:
        got = base.xpath(xp)
        if got and _words(got[0]) >= skeleton * 0.3:
            return got[0]
    return base


def count_term(text: str, term: str) -> int:
    t = norm(term)
    if not t:
        return 0
    return len(re.findall(re.escape(t), text))


def measure(url: str, session: requests.Session, terms: list[str], role: str,
            rendered: dict[str, Path] | None = None) -> dict:
    """rendered: map URL -> file HTML đã chạy JS. Dùng cho trang render bằng JavaScript.

    Cùng một hàm đo cho cả HTML thuần và HTML đã render — nguyên tắc ở metrics.md mục 4:
    đo mình một kiểu, đo đối thủ kiểu khác thì bảng so sánh vô giá trị.
    """
    def words_of(html_text: str) -> int:
        try:
            doc = lxml_html.fromstring(html_text)
        except Exception:
            return 0
        return len(re.findall(r"\w+", main_content(doc).text_content(), flags=re.UNICODE))

    # Lấy bản NHIỀU NỘI DUNG HƠN giữa HTML thuần và HTML đã render.
    # Render có thể bị chặn headless và trả về trang rỗng, trong khi HTML thuần lại đầy đủ —
    # ưu tiên mù quáng bản render sẽ làm mất đối thủ đo được.
    cand: list[tuple[str, str, float, str]] = []
    from_file = rendered.get(url) if rendered else None
    if from_file:
        try:
            rt = Path(from_file).read_text(encoding="utf-8", errors="ignore")
            cand.append(("rendered", rt, round(len(rt.encode("utf-8")) / 1024, 1), url))
        except OSError:
            pass
    try:
        r = session.get(url, timeout=TIMEOUT, allow_redirects=True)
        r.raise_for_status()
        cand.append(("raw_html", r.text, round(len(r.content) / 1024, 1), r.url))
    except requests.RequestException as exc:
        if not cand:
            return {"url": url, "role": role, "_blocked": str(exc)}
    src, text, html_kb, final_url = max(cand, key=lambda c: words_of(c[1]))
    from_file = src == "rendered"

    class _R:
        pass
    r = _R()
    r.text, r.url = text, final_url
    try:
        full = lxml_html.fromstring(text)
    except Exception as exc:
        return {"url": url, "role": role, "_blocked": f"không phân tích được HTML: {exc}"}

    title = (full.xpath("//title/text()") or [None])[0]
    desc = (full.xpath("//meta[@name='description']/@content") or [None])[0]
    h1_nodes = full.xpath("//h1")
    h1 = h1_nodes[0].text_content().strip() if h1_nodes else None
    date_modified = None
    for xp in ["//meta[@property='article:modified_time']/@content",
               "//meta[@itemprop='dateModified']/@content",
               "//time[@itemprop='dateModified']/@datetime"]:
        got = full.xpath(xp)
        if got:
            date_modified = got[0]
            break

    schema_declared: list[str] = []
    schema_faq_questions = 0
    for node in full.xpath("//script[@type='application/ld+json']/text()"):
        try:
            payload = json.loads(node)
        except json.JSONDecodeError:
            continue
        for item in (payload if isinstance(payload, list) else [payload]):
            if not isinstance(item, dict):
                continue
            t = item.get("@type")
            if t:
                schema_declared.extend(t if isinstance(t, list) else [t])
            if item.get("@type") == "FAQPage":
                schema_faq_questions += len(item.get("mainEntity") or [])
            if not date_modified and item.get("dateModified"):
                date_modified = item["dateModified"]

    host = urlparse(r.url).netloc.lower().removeprefix("www.")
    internal = [a for a in full.xpath("//a/@href")
                if urlparse(a).netloc.lower().removeprefix("www.") in ("", host)]
    body_lower = r.text.lower()
    conversion = {
        "form": bool(full.xpath("//form")),
        "hotline": bool(re.search(r"tel:|hotline|\b0\d{9}\b", body_lower)),
        "cta": bool(re.search(r"báo giá|tư vấn|đăng ký|liên hệ|nhận ưu đãi", body_lower)),
    }

    content = main_content(full)
    text = norm(content.text_content())
    words = len(re.findall(r"\w+", text, flags=re.UNICODE))
    imgs = content.xpath(".//img")
    lazy = [i for i in imgs if i.get("loading") == "lazy" or i.get("data-src") or i.get("data-lazy-src")]
    srcset = [i for i in imgs if i.get("srcset")]
    webp = [i for i in imgs
            if re.search(r"\.(webp|avif)(\?|$)", (i.get("src") or "") + (i.get("data-src") or ""), re.I)]

    h2 = content.xpath(".//h2")
    h3 = content.xpath(".//h3")
    headings = ([{"level": 2, "text": n.text_content().strip()} for n in h2]
                + [{"level": 3, "text": n.text_content().strip()} for n in h3])

    faq_rendered = bool(full.xpath(
        "//*[contains(translate(@class,'FAQ','faq'),'faq')]"
        "//*[self::h2 or self::h3 or self::summary or self::dt]"))
    if schema_faq_questions and not faq_rendered:
        faq_status = "schema_only"
    elif faq_rendered:
        faq_status = "rendered"
    else:
        faq_status = "none"

    rendered_mismatch = []
    if faq_status == "schema_only":
        rendered_mismatch.append("FAQPage")

    # Trang render bằng JS: HTML nặng nhưng nội dung thuần gần như rỗng.
    # Không phát hiện thì chấm điểm vị thế sẽ luôn ra "Mạnh" vì đối thủ đo ra vài chục từ.
    # Trang render xong mà vẫn rỗng thì càng phải loại: đã cho cơ hội render mà nội dung
    # vẫn không có nghĩa là chặn headless hoặc nội dung nằm ngoài DOM thường.
    empty = words < 300 and html_kb > 80
    js_suspected = empty
    render_failed = empty and bool(from_file)
    return {
        "url": r.url, "role": role,
        "js_suspected": js_suspected,
        "render_failed": render_failed,
        "source": src,
        "word_count": words,
        "content_images": len(imgs),
        "lazy": len(lazy), "srcset": len(srcset), "webp": len(webp),
        "html_kb": html_kb,
        "h2": len(h2), "h3": len(h3),
        "faq": faq_status,
        "faq_schema_questions": schema_faq_questions,
        "date_modified": date_modified,
        "internal_links": len(internal),
        "conversion": conversion,
        "title": title, "description": desc, "h1": h1,
        "url_slug": urlparse(r.url).path,
        "sample_items": len([n for n in h3 if re.search(r"\d", n.text_content())]),
        "schema": {"declared": sorted(set(schema_declared)), "rendered_mismatch": rendered_mismatch},
        "headings": headings,
        "_text": text,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--own", required=True, help="URL trang đích của mình")
    ap.add_argument("--competitors", help="File JSON từ fetch_serp.py, hoặc danh sách URL cách nhau dấu phẩy")
    ap.add_argument("--terms", required=True, help="Cụm cần đếm, cách nhau dấu phẩy. BẮT BUỘC gồm biến thể đảo trật tự")
    ap.add_argument("--cluster-urls", help="URL cùng chủ đề trên domain mình, cách nhau dấu phẩy hoặc file .txt")
    ap.add_argument("--main-term", help="Cụm chính, dùng cho bảng cluster. Mặc định lấy cụm đầu tiên")
    ap.add_argument("--rate", type=float, default=2.0)
    ap.add_argument("--rendered-dir", help="Thư mục chứa HTML đã render + index.json, "
                                           "cho trang render bằng JavaScript")
    ap.add_argument("--out")
    args = ap.parse_args()

    terms = [t.strip() for t in args.terms.split(",") if t.strip()]
    if not terms:
        fail("Danh sách cụm cần đếm rỗng. Bắt buộc gồm cả biến thể đảo trật tự của từ khóa mục tiêu.")
    main_term = args.main_term or terms[0]

    comp_urls: list[str] = []
    if args.competitors:
        p = Path(args.competitors).expanduser()
        if p.exists():
            data = json.loads(p.read_text(encoding="utf-8"))
            comp_urls = [c["url"] for c in data.get("competitors", []) if c.get("url")]
            if not comp_urls:
                fail("File đối thủ không có URL nào. fetch_serp.py cần SERP chứa URL đầy đủ, "
                     "không chỉ tên domain.")
        else:
            comp_urls = [u.strip() for u in args.competitors.split(",") if u.strip()]

    cluster_urls: list[str] = []
    if args.cluster_urls:
        p = Path(args.cluster_urls).expanduser()
        cluster_urls = ([ln.strip() for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
                        if p.exists() else
                        [u.strip() for u in args.cluster_urls.split(",") if u.strip()])

    rendered: dict[str, Path] = {}
    if args.rendered_dir:
        rd = Path(args.rendered_dir).expanduser()
        idx = rd / "index.json"
        if not idx.exists():
            fail(f"Không tìm thấy {idx}. Thư mục render phải có index.json do render.js sinh ra.")
        for it in json.loads(idx.read_text(encoding="utf-8")):
            if it.get("file"):
                rendered[it["url"]] = rd / it["file"]
        log(f"Có {len(rendered)} trang đã render sẵn, sẽ đo từ HTML sau JS")

    session = requests.Session()
    session.headers["User-Agent"] = UA
    delay = 1.0 / args.rate if args.rate > 0 else 0

    pages, blocked = [], []
    targets = [(args.own, "own")] + [(u, "competitor") for u in comp_urls] \
        + [(u, "cluster") for u in cluster_urls]

    for i, (url, role) in enumerate(targets, 1):
        m = measure(url, session, terms, role, rendered)
        if m.get("_blocked"):
            blocked.append({"url": url, "role": role, "reason": m["_blocked"]})
        else:
            pages.append(m)
        log(f"  [{i}/{len(targets)}] {role}: {url}")
        time.sleep(delay)

    if not any(p["role"] == "own" for p in pages):
        fail("Không crawl được trang đích của mình. Kiểm tra URL hoặc site có chặn crawler không.",
             blocked=blocked)

    measurable = [p for p in pages if not p["js_suspected"]]
    js_pages = [p for p in pages if p["js_suspected"]]

    term_matrix: dict[str, dict[str, int]] = {}
    for term in terms:
        row = {}
        for p in measurable:
            if p["role"] == "cluster":
                continue
            key = "own" if p["role"] == "own" else urlparse(p["url"]).netloc.lower().removeprefix("www.")
            row[key] = count_term(p["_text"], term)
        term_matrix[term] = row

    cluster = []
    for p in pages:
        if p["role"] not in ("own", "cluster"):
            continue
        cluster.append({
            "url": p["url"],
            "role_declared": "pillar" if p["role"] == "own" else "con",
            "word_count": p["word_count"],
            "main_term_count": count_term(p["_text"], main_term),
            "title": p["title"],
        })

    signals = []
    if len(cluster) > 1:
        pillar = cluster[0]
        for c in cluster[1:]:
            hits = []
            if pillar["word_count"] and c["word_count"] >= pillar["word_count"] * 0.8:
                hits.append("trang con dày ngang pillar (>=80% số từ)")
            if pillar["main_term_count"] and c["main_term_count"] >= pillar["main_term_count"] * 0.5:
                hits.append("trang con nhồi cụm chính nặng (>=50% mật độ pillar)")
            if c["title"] and pillar["title"] and norm(main_term) in norm(c["title"]) \
                    and norm(main_term) in norm(pillar["title"]):
                hits.append("title trùng cụm chính")
            if hits:
                signals.append({"url": c["url"], "signals": hits})

    for p in pages:
        p.pop("_text", None)

    own_page = next(p for p in pages if p["role"] == "own")
    competitors_measured = sum(1 for p in measurable if p["role"] == "competitor")
    competitors_js = sum(1 for p in js_pages if p["role"] == "competitor")

    if own_page["js_suspected"]:
        fail("Trang đích của mình render bằng JavaScript, HTML thuần gần như rỗng "
             f"({own_page['word_count']} từ trên {own_page['html_kb']}KB). Mọi chỉ số nội dung "
             "sẽ sai. Dùng Chrome MCP mở trang, lấy HTML sau khi render, rồi đo lại.",
             blocked=blocked)

    scoring_ready = competitors_measured >= 3

    emit({
        "crawl_date": time.strftime("%Y-%m-%d"),
        "own_url": own_page["url"],
        "main_term": main_term,
        "terms": terms,
        "competitors_measured": competitors_measured,
        "competitors_blocked": sum(1 for b in blocked if b["role"] == "competitor"),
        "competitors_js_rendered": competitors_js,
        "js_rendered_urls": [p["url"] for p in js_pages],
        "scoring_ready": scoring_ready,
        "scoring_note": (None if scoring_ready else
                         f"CHƯA ĐỦ ĐIỀU KIỆN CHẤM ĐIỂM VỊ THẾ: chỉ đo được {competitors_measured} "
                         f"đối thủ (cần tối thiểu 3). {competitors_js} trang render bằng JS nên "
                         f"HTML thuần rỗng, {sum(1 for b in blocked if b['role']=='competitor')} "
                         f"trang bị chặn. KHÔNG được chấm vị thế trên tập này — sẽ luôn ra 'Mạnh' "
                         f"vì đối thủ đo ra vài chục từ. Lấy HTML sau render bằng Chrome MCP "
                         f"cho các URL trong js_rendered_urls, hoặc đổi sang đối thủ khác."),
        "pages": pages,
        "term_matrix": term_matrix,
        "cluster": cluster,
        "cluster_signals": signals,
        "cluster_verdict": ("Có dấu hiệu nhiều trang nội bộ tranh nhau — chạy phân vai lại"
                            if signals else
                            "Không có dấu hiệu cluster tranh nhau" if len(cluster) > 1 else
                            "Chỉ có một trang cùng chủ đề, không xét cluster"),
        "blocked": blocked,
        "blocked_note": ("Trang bị chặn crawl phải được nêu rõ trong báo cáo. "
                         "Trên nửa số đối thủ bị chặn thì hỏi người dùng có tiếp tục với tập nhỏ hơn không."),
        "rendered_count": sum(1 for p in pages if p.get("source") == "rendered"),
        "render_failed_urls": [p["url"] for p in js_pages if p.get("render_failed")],
        "measurement_note": ("Nội dung chính = phần bài viết, đã loại menu, chân trang, thanh bên, "
                             "khối liên quan. Cùng một cách đo áp dụng cho mọi trang trong tập."),
    }, args.out)


if __name__ == "__main__":
    main()
