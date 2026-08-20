#!/usr/bin/env python3
"""Sinh báo cáo HTML từ kết quả phân tích khoảng cách.

output_type quyết định render phần đề xuất theo outline (A) hay phân vai cluster (B).
--summary sinh trang tổng hợp từ nhiều file JSON.
Mỗi bảng render kèm chỗ cho câu đọc bảng; thiếu thì cảnh báo ra stderr.
"""
from __future__ import annotations

import argparse
import html
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path.home() / ".claude" / "skills" / "seo-doctor" / "scripts"))
from common import emit, fail, log, slugify  # noqa: E402

TEMPLATE = Path(__file__).resolve().parent.parent / "templates" / "report.html"

SEVERITY_LABEL = {"nghiem_trong": "NGHIÊM TRỌNG", "cao": "TÁC ĐỘNG CAO",
                  "trung_binh": "TÁC ĐỘNG TRUNG BÌNH", "thap": "TÁC ĐỘNG THẤP"}
SEVERITY_ORDER = {"nghiem_trong": 0, "cao": 1, "trung_binh": 2, "thap": 3}
POSITION_LABEL = {"manh": "Mạnh", "ngang": "Ngang", "yeu": "Yếu", "hon_hop": "Hỗn hợp"}
LABEL_CLASS = {"GIỮ": "t-keep", "SỬA": "t-fix", "MỚI": "t-new",
               "GAP SERP": "t-gap", "BRAND": "t-brand"}


def esc(v) -> str:
    return html.escape("" if v is None else str(v))


def table(headers: list[str], rows: list[list], reading: str | None = None, name: str = "") -> str:
    if not rows:
        return '<p class="muted">Không có dữ liệu cho mục này.</p>'
    if not reading:
        log(f"CẢNH BÁO: bảng '{name or headers[0]}' thiếu câu đọc bảng. "
            f"Không để bảng đứng trần.")
    head = "".join(f"<th>{esc(h)}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{esc(c)}</td>" for c in r) + "</tr>" for r in rows)
    out = f'<div class="tblwrap"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'
    if reading:
        out += f'<p class="reading">{esc(reading)}</p>'
    return out


def section(num: str, title: str, body: str) -> str:
    return f'<section class="h2block"><h2><span class="si">{esc(num)}</span>{esc(title)}</h2>{body}</section>'


def render_matrix(matrix: dict, own_key: str = "own") -> str:
    if not matrix:
        return '<p class="muted">Chưa có ma trận mật độ.</p>'
    domains = []
    for row in matrix.values():
        for k in row:
            if k not in domains:
                domains.append(k)
    domains = [own_key] + [d for d in domains if d != own_key]
    rows = [[term] + [row.get(d, 0) for d in domains] for term, row in matrix.items()]
    return table(["Cụm"] + ["mình" if d == own_key else d for d in domains], rows,
                 reading=None, name="ma trận mật độ")


def build_body(d: dict) -> str:
    out = []
    otype = d.get("output_type", "A")

    kws = "".join(f'<span class="kw">{esc(k)}</span>' for k in d.get("keywords", []))
    highs = "".join(
        f'<div class="kpi"><div class="k">{esc(h.get("label"))}</div>'
        f'<div class="v">{esc(h.get("value"))}</div>'
        f'<div class="n">{esc(h.get("note"))}</div></div>'
        for h in d.get("highlights", []))
    out.append(f"""<section class="h2block intro">
      <p class="scope">Trang đích <code>{esc(d.get('target_url'))}</code>, so với
      {esc(d.get('competitors_measured'))} URL đang chiếm top
      {f"({esc(d.get('competitors_blocked'))} trang bị chặn crawl)" if d.get('competitors_blocked') else ""}.
      Số liệu lấy từ crawl HTML thô ngày {esc(d.get('crawl_date'))}, không phải ước lượng.</p>
      <div class="kws">{kws}</div>
      <div class="kpis">{highs}</div></section>""")

    strengths = "".join(
        f'<div class="card"><div class="ihead"><span class="iname">{esc(s.get("title"))}</span></div>'
        f'<div class="ibody"><p><b>{esc(s.get("own"))}</b></p><p>{esc(s.get("comparison"))}</p></div></div>'
        for s in d.get("strengths", []))
    if not d.get("strengths"):
        log("CẢNH BÁO: thiếu mục điểm mạnh. Đây là lỗi nghiêm trọng — "
            "không xác định được thế mạnh thì không kết luận được nên viết lại hay chỉ tối ưu.")

    issues = sorted(d.get("issues", []), key=lambda i: SEVERITY_ORDER.get(i.get("severity"), 9))
    issue_html = "".join(f"""
      <div class="issue">
        <div class="sev {esc(i.get('severity'))}">{esc(SEVERITY_LABEL.get(i.get('severity'), i.get('severity')))}</div>
        <h3>{esc(i.get('title'))}</h3>
        <p>{esc(i.get('own'))}</p>
        <p class="cmp">{esc(i.get('comparison'))}</p>
        <p class="why">{esc(i.get('why'))}</p>
        {f'<pre class="ev">{esc(i.get("evidence_block"))}</pre>' if i.get("evidence_block") else ""}
        {'<p class="tpl">Lỗi cấp template — nên xử lý một lần cho toàn site.</p>' if i.get("template_level") else ""}
      </div>""" for i in issues)

    out.append(section("1", "Hiện trạng trang",
                       f'<h3 class="sub">Điểm mạnh đang có</h3>{strengths}'
                       f'<h3 class="sub">{len(issues)} vấn đề, xếp theo mức tác động</h3>{issue_html}'))

    cl = d.get("cluster") or {}
    if cl.get("pages"):
        sig = "".join(f"<li>{esc(s.get('url'))}: {esc(', '.join(s.get('signals', [])))}</li>"
                      for s in cl.get("signals", []))
        out.append(section("2", "Vấn đề trọng tâm: nhiều trang tranh nhau một từ khóa",
            table(["URL", "Vai khai báo", "Số từ", "Mật độ cụm chính", "Vấn đề"],
                  [[p.get("url"), p.get("role_declared"), p.get("word_count"),
                    p.get("main_term_count"), p.get("issue")] for p in cl["pages"]],
                  reading=cl.get("reading"), name="cluster")
            + (f'<h3 class="sub">Dấu hiệu xác nhận</h3><ul>{sig}</ul>' if sig else "")
            + f'<h3 class="sub">Phân vai lại</h3>'
            + table(["Trang", "Vai mới", "Việc cụ thể"],
                    [[r.get("url"), r.get("new_role"), r.get("task")] for r in cl.get("reassignment", [])],
                    reading=cl.get("reassignment_note"), name="phân vai")
            + f'<h3 class="sub">Kế hoạch nối link</h3>'
            + table(["Trang nguồn", "Trang đích", "Anchor", "Vị trí đặt"],
                    [[l.get("from"), l.get("to"), l.get("anchor"), l.get("placement")]
                     for l in cl.get("link_plan", [])], reading=None, name="nối link")
            + f'<p class="verdict">{esc(cl.get("verdict"))}</p>'))

    serp = d.get("serp_table", [])
    out.append(section("3", "So sánh các trang trong SERP",
        table(["Trang", "Từ", "Ảnh ND", "Lazy", "srcset", "H2/H3", "FAQ", "HTML", "Cập nhật"],
              [[r.get("label"), r.get("word_count"), r.get("content_images"), r.get("lazy"),
                r.get("srcset"), f"{r.get('h2')}/{r.get('h3')}", r.get("faq"),
                f"{r.get('html_kb')}KB", r.get("date_modified")] for r in serp],
              reading=d.get("serp_reading"), name="bảng chỉ số")
        + '<h3 class="sub">Mật độ từ khóa</h3>'
        + render_matrix(d.get("term_matrix", {}))
        + (f'<p class="reading">{esc(d.get("matrix_reading"))}</p>' if d.get("matrix_reading") else "")))

    out.append(section("4", "Mổ xẻ từng đối thủ và chỗ chen vào", "".join(f"""
      <div class="rival">
        <div class="rh"><span class="rname">{esc(c.get('domain'))}</span>
          <span class="rstat">{esc(c.get('stat'))}</span></div>
        <p><b>Mạnh:</b> {esc(c.get('strong'))}</p>
        <p><b>Yếu:</b> {esc(c.get('weak'))}</p>
        <p class="entry"><b>Chỗ chen vào:</b> {esc(c.get('entry_point'))}</p>
      </div>""" for c in d.get("competitor_breakdown", []))))

    meta = d.get("meta_layer", [])
    out.append(section("5", "Lớp meta",
        table(["Thành phần", "Hiện tại", "Đề xuất"],
              [[m.get("field"), m.get("current"), m.get("proposed")] for m in meta],
              reading=d.get("meta_reading"), name="lớp meta")))

    n = 6
    if otype == "A":
        ol = d.get("outline", {})
        tg = ol.get("targets", {})
        sec_html = []
        for s in ol.get("sections", []):
            h3s = "".join(f"""
              <div class="h3item"><div class="name">{esc(h.get('title'))}
                <span class="tag {LABEL_CLASS.get(h.get('label'), '')}">{esc(h.get('label'))}</span></div>
                <ul>{''.join(f'<li>{esc(p)}</li>' for p in h.get('points', []))}</ul>
                {f"<p class='meta'>Ảnh: {esc(h.get('media'))}</p>" if h.get("media") else ""}
                {f"<p class='why'>{esc(h.get('reason'))}</p>" if h.get("reason") else ""}
              </div>""" for h in s.get("h3", []))
            sec_html.append(f"""<div class="card">
              <div class="ihead"><span class="iname">{esc(s.get('title'))}</span>
                <span class="meta">{esc(s.get('length'))} · {len(s.get('h3', []))} H3 · {esc(s.get('media'))}</span></div>
              <div class="ibody">{h3s}</div></div>""")
        intro = ol.get("intro", {})
        out.append(section(str(n), "Outline chi tiết", f"""
          <p class="legend">GIỮ giữ nội dung cũ · SỬA làm sâu hơn · MỚI chưa có trên trang ·
             GAP SERP không đối thủ top 3 nào có · BRAND chèn giải pháp của mình</p>
          {table(["Mục tiêu", "Hiện tại", "Đích"],
                 [[k, v.get("current"), v.get("target")] for k, v in tg.items()],
                 reading=None, name="mục tiêu")}
          <div class="card"><div class="ihead"><span class="iname">Mở bài</span>
            <span class="meta">{esc(intro.get('length'))}</span></div>
            <div class="ibody"><ul>{''.join(f'<li>{esc(x)}</li>' for x in intro.get('points', []))}</ul></div></div>
          {''.join(sec_html)}"""))
        n += 1
    else:
        add = d.get("targeted_additions", [])
        out.append(section(str(n), "Bổ sung có mục tiêu",
            table(["Nhóm việc", "Căn cứ số liệu", "Việc cụ thể"],
                  [[a.get("group"), a.get("evidence"), a.get("task")] for a in add],
                  reading=d.get("additions_reading"), name="bổ sung")))
        n += 1

    out.append(section(str(n), "Bộ FAQ hiển thị thật",
        table(["Câu hỏi", "Trả lời", "Nguồn"],
              [[f.get("q"), f.get("a"), f.get("source")] for f in d.get("faq", [])],
              reading="FAQ phải render ra HTML rồi mới khai schema. "
                      "Khai schema mà không có nội dung thật là lỗi. "
                      "Câu trả lời dưới đây là bản nháp để biên tập lại theo giọng thương hiệu; "
                      "chỗ đánh dấu [Cần cập nhật đơn giá] phải thay bằng số thật trước khi đăng.",
              name="FAQ")))
    n += 1

    ip = d.get("image_plan", {})
    out.append(section(str(n), "Kế hoạch ảnh và tối ưu tải", f"""
      <p>Mục tiêu: {esc(ip.get('target_count'))} ảnh (hiện {esc(ip.get('current_count'))}).</p>
      <p>Quy ước alt: {esc(ip.get('alt_convention'))}</p>
      {table(["Yêu cầu kỹ thuật", "Hiện tại", "Đích", "Căn cứ"],
             [[r.get("item"), r.get("current"), r.get("target"), r.get("basis")]
              for r in ip.get("requirements", [])], reading=None, name="ảnh")}
      {table(["Ảnh cần vẽ mới", "Đặt ở mục"],
             [[x.get("what"), x.get("where")] for x in ip.get("new_assets", [])],
             reading=None, name="ảnh vẽ mới")}"""))
    n += 1

    out.append(section(str(n), "Structured data cần sửa",
        table(["Schema", "Trạng thái", "Việc cần làm"],
              [[s.get("type"), s.get("status"), s.get("action")] for s in d.get("schema_fixes", [])],
              reading=d.get("schema_reading"), name="schema")))
    n += 1

    phases = "".join(f"""
      <div class="card"><div class="ihead"><span class="iname">Đợt {esc(p.get('phase'))}</span>
        <span class="meta">{esc(p.get('title'))}</span></div>
      <div class="ibody">{table(["Việc", "Người làm", "Thời gian", "Cách kiểm tra"],
             [[t.get("task"), t.get("owner"), t.get("effort"), t.get("verify")]
              for t in p.get("tasks", [])], reading=None, name=f"đợt {p.get('phase')}")}</div></div>"""
        for p in d.get("checklist", []))
    out.append(section(str(n), "Checklist triển khai theo đợt", phases))
    n += 1

    if d.get("before_after"):
        out.append(section(str(n), "Đối chiếu trước và sau",
            table(["Khoảng cách", "Hiện tại", "Sau khi làm xong"],
                  [[b.get("gap"), b.get("before"), b.get("after")] for b in d["before_after"]],
                  reading=d.get("before_after_reading"), name="trước sau")))
    return "".join(out)


def build_summary(items: list[dict]) -> str:
    rows = [[f'{i.get("cluster_name")}', i.get("target_url"),
             POSITION_LABEL.get(i.get("position_verdict"), i.get("position_verdict")),
             i.get("output_type"), i.get("main_blocker"),
             (i.get("feasibility") or {}).get("verdict"), i.get("effort"), i.get("priority_rank")]
            for i in sorted(items, key=lambda x: x.get("priority_rank", 99))]
    tpl_errors = sorted({e for i in items for e in i.get("template_level_errors", [])})
    body = section("1", "So sánh các cụm", table(
        ["Cụm", "Trang đích", "Vị thế", "Đầu ra", "Rào cản chính", "Khả năng lên top", "Công sức", "Thứ tự"],
        rows, reading="Thứ tự đề nghị xếp theo khả năng lên top trước, rồi công sức thấp trước. "
                      "Cụm không khả thi xếp cuối.", name="tổng hợp"))
    if tpl_errors:
        body += section("2", "Lỗi cấp template xuất hiện ở nhiều cụm",
                        "<ul>" + "".join(f"<li>{esc(e)}</li>" for e in tpl_errors) + "</ul>"
                        + '<p class="reading">Đây là việc nên làm một lần cho toàn site, '
                          'thay vì làm riêng từng cụm.</p>')
    return body


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", required=True, help="File JSON, hoặc nhiều file cách nhau dấu phẩy khi dùng --summary")
    ap.add_argument("--out-dir", default="~/html")
    ap.add_argument("--summary", action="store_true")
    args = ap.parse_args()

    out_dir = Path(args.out_dir).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)
    if not TEMPLATE.exists():
        fail(f"Không tìm thấy template: {TEMPLATE}")
    tpl = TEMPLATE.read_text(encoding="utf-8")

    paths = [Path(p.strip()).expanduser() for p in args.input.split(",") if p.strip()]
    missing = [str(p) for p in paths if not p.exists()]
    if missing:
        fail(f"Không tìm thấy file: {', '.join(missing)}")
    items = [json.loads(p.read_text(encoding="utf-8")) for p in paths]

    written = []
    if args.summary:
        domain = items[0].get("domain", "site")
        stamp = items[0].get("date") or date.today().isoformat()
        page = (tpl.replace("{{TITLE}}", esc(f"Phân tích khoảng cách — {domain}"))
                   .replace("{{SUBTITLE}}", esc(f"Tổng hợp {len(items)} cụm từ khóa"))
                   .replace("{{DATE}}", esc(stamp))
                   .replace("{{BODY}}", build_summary(items)))
        p = out_dir / f"seo-gap-{domain}-tong-hop-{stamp.replace('-', '')}.html"
        p.write_text(page, encoding="utf-8")
        written.append(str(p))
    else:
        for d in items:
            domain = d.get("domain", "site")
            stamp = d.get("date") or date.today().isoformat()
            slug = slugify(d.get("cluster_name", "cum"))
            page = (tpl.replace("{{TITLE}}", esc(f"{d.get('cluster_name')} — {domain}"))
                       .replace("{{SUBTITLE}}", esc(
                           f"Vị thế {POSITION_LABEL.get(d.get('position_verdict'), '')} · "
                           f"Đầu ra {d.get('output_type')}"))
                       .replace("{{DATE}}", esc(stamp))
                       .replace("{{BODY}}", build_body(d)))
            p = out_dir / f"seo-gap-{domain}-{slug}-{stamp.replace('-', '')}.html"
            p.write_text(page, encoding="utf-8")
            written.append(str(p))

    emit({"reports": written, "count": len(written)})


if __name__ == "__main__":
    main()
