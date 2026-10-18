"""Build downloadable reports (Markdown and printable HTML) from a LegalLens session."""
from datetime import datetime

from ui_helpers import clause_quotes, esc, parse_answer, parse_risk

DISCLAIMER = "LegalLens is an AI triage aid, not legal advice. Have a qualified lawyer check anything important."
PRIORITY = {"high": "Look closely", "medium": "Check", "info": "Note"}
RISK_LABEL = {"LOW": "Low risk", "MEDIUM": "Medium risk", "HIGH": "High risk"}
FACT_TITLES = {"money": "Money", "periods": "Time periods", "dates": "Dates"}


def summarize(result: dict) -> dict:
    """Flatten an analysis result into plain fields for reports."""
    base = {"level": None, "why": "", "analysis": "", "quotes": [], "grounded": None, "pages": []}
    if result["kind"] == "not_found":
        return {**base, "analysis": "The document does not seem to answer this question."}
    sections = parse_answer(result["answer"])
    if sections is None:
        return {**base, "analysis": result["answer"]}
    level, why = parse_risk(sections["risk level"])
    return {
        "level": level, "why": why, "analysis": sections["analysis"],
        "quotes": clause_quotes(sections["relevant clause"]),
        "grounded": result["grounded"], "pages": result["quote_pages"],
    }


def _verification(s: dict) -> str:
    if s["grounded"] is True:
        pg = ", ".join(map(str, s["pages"]))
        return f"Verified in the PDF (page {pg})" if pg else "Verified in the PDF"
    if s["grounded"] is False:
        return "NOT found word for word in the PDF. Treat this answer as unverified"
    return "Not checked"


def _entries(history: list[dict]):
    return [h for h in history if h["result"]["kind"] in ("ok", "not_found")]


def _now() -> str:
    return datetime.now().strftime("%d %b %Y, %H:%M")


# --------------------------------------------------------------------------- #
def build_markdown_report(
    filename: str, page_count: int, scan: dict, history: list[dict], model: str, source_note: str | None = None
) -> str:
    out = [
        "# LegalLens report", "",
        f"- **Document:** {filename}",
        f"- **Pages:** {page_count}",
        f"- **Generated:** {_now()}",
        f"- **Model:** {model}", "",
        f"> {DISCLAIMER}", "",
    ]
    if source_note:
        out += [f"> {source_note}", ""]
    out += ["## Quick scan", ""]
    findings = scan["findings"]
    if findings:
        out += ["| Topic | Priority | Mentions | Pages |", "|---|---|---|---|"]
        for f in findings:
            pages = ", ".join(map(str, f["pages"]))
            out.append(f"| {f['label']} | {PRIORITY[f['severity']]} | {f['count']} | {pages} |")
    else:
        out.append("No common red-flag wording found.")

    for kind, title in FACT_TITLES.items():
        items = scan["facts"].get(kind, [])
        if items:
            out += ["", f"**{title}:** " + "; ".join(f"{i['text']} (page {i['page']})" for i in items)]

    entries = _entries(history)
    out += ["", "## Questions and answers", ""]
    if not entries:
        out.append("No questions were asked in this session.")
    for n, h in enumerate(entries, start=1):
        s = summarize(h["result"])
        out += [f"### {n}. {h['question']}", ""]
        if s["level"]:
            out += [f"**Risk:** {RISK_LABEL[s['level']]}. {s['why']}", ""]
        out += [s["analysis"], ""]
        for q in s["quotes"]:
            out += [f"> {q}", ""]
        if s["quotes"]:
            out += [f"*Quote check: {_verification(s)}.*", ""]
    return "\n".join(out).rstrip() + "\n"


# --------------------------------------------------------------------------- #
_HTML_CSS = """
body{font-family:Georgia,"Palatino Linotype",serif;color:#17233A;max-width:820px;margin:2rem auto;padding:0 1.2rem;line-height:1.6}
h1{margin-bottom:.2rem} h2{margin-top:2rem;border-bottom:1px solid #D8DEE8;padding-bottom:.3rem}
.meta{color:#5B677D;font-family:system-ui,sans-serif;font-size:.9rem}
.note{background:#F4F6F9;border-left:4px solid #17233A;padding:.6rem 1rem;font-family:system-ui,sans-serif;font-size:.9rem}
table{border-collapse:collapse;width:100%;font-family:system-ui,sans-serif;font-size:.9rem}
th,td{border:1px solid #D8DEE8;padding:.4rem .6rem;text-align:left} th{background:#F4F6F9}
.qa{margin:1.4rem 0;padding-bottom:1rem;border-bottom:1px solid #D8DEE8}
.risk{display:inline-block;padding:.15rem .7rem;border-radius:4px;font-family:system-ui,sans-serif;font-weight:700;font-size:.85rem}
.risk-LOW{background:#E6F3EC;color:#1E5E43}.risk-MEDIUM{background:#FBF0D9;color:#8A5200}.risk-HIGH{background:#FBE6E3;color:#8F1D17}
blockquote{margin:.6rem 0;padding:.2rem .9rem;border-left:4px solid #FFE066;font-style:italic}
.check{font-family:system-ui,sans-serif;font-size:.85rem;color:#5B677D}
@media print{body{margin:0}.qa{page-break-inside:avoid}}
"""


def build_html_report(
    filename: str, page_count: int, scan: dict, history: list[dict], model: str, source_note: str | None = None
) -> str:
    parts = [
        f"<h1>LegalLens report</h1><p class='meta'>{esc(filename)}, {page_count} pages. "
        f"Generated {esc(_now())} with {esc(model)}.</p>",
        f"<p class='note'>{esc(DISCLAIMER)}</p>",
    ]
    if source_note:
        parts.append(f"<p class='note'>{esc(source_note)}</p>")
    parts.append("<h2>Quick scan</h2>")
    findings = scan["findings"]
    if findings:
        rows = "".join(
            f"<tr><td>{esc(f['label'])}</td><td>{PRIORITY[f['severity']]}</td><td>{f['count']}</td>"
            f"<td>{esc(', '.join(map(str, f['pages'])))}</td></tr>"
            for f in findings
        )
        parts.append(f"<table><tr><th>Topic</th><th>Priority</th><th>Mentions</th><th>Pages</th></tr>{rows}</table>")
    else:
        parts.append("<p>No common red-flag wording found.</p>")

    for kind, title in FACT_TITLES.items():
        items = scan["facts"].get(kind, [])
        if items:
            joined = "; ".join(f"{i['text']} (page {i['page']})" for i in items)
            parts.append(f"<p><strong>{title}:</strong> {esc(joined)}</p>")

    parts.append("<h2>Questions and answers</h2>")
    entries = _entries(history)
    if not entries:
        parts.append("<p>No questions were asked in this session.</p>")
    for n, h in enumerate(entries, start=1):
        s = summarize(h["result"])
        block = [f"<div class='qa'><h3>{n}. {esc(h['question'])}</h3>"]
        if s["level"]:
            block.append(f"<p><span class='risk risk-{s['level']}'>{RISK_LABEL[s['level']]}</span> {esc(s['why'])}</p>")
        block.append(f"<p>{esc(s['analysis'])}</p>")
        block += [f"<blockquote>{esc(q)}</blockquote>" for q in s["quotes"]]
        if s["quotes"]:
            block.append(f"<p class='check'>Quote check: {esc(_verification(s))}.</p>")
        block.append("</div>")
        parts.append("".join(block))

    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>LegalLens report</title><style>{_HTML_CSS}</style></head><body>"
        + "".join(parts) + "</body></html>"
    )
