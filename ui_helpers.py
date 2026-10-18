"""Styling and HTML builders for the LegalLens Streamlit UI.

Design notes
- Palette: ink navy for text, a legal-highlighter yellow for evidence, and three
  risk colours used only for the verdict. Everything else stays quiet.
- Fonts: system stacks only, so the page makes no third-party requests
  (a "private" tool should not call out to a font CDN).
- Every piece of document or model text is HTML-escaped before it is injected.
- Generated HTML is kept on a single line: Streamlit's markdown parser ends an
  HTML block at the first blank line, which would break the layout.
"""
import html
import re

CSS = """<style>
:root{
  --ink:#17233A; --muted:#5B677D; --line:#D8DEE8; --paper:#F4F6F9; --surface:#FFFFFF;
  --mark:#FFE066;
  --low:#1E5E43;  --low-bg:#E6F3EC;
  --med:#8A5200;  --med-bg:#FBF0D9;
  --high:#8F1D17; --high-bg:#FBE6E3;
  --serif:"Palatino Linotype","Book Antiqua",Palatino,"Iowan Old Style",Georgia,serif;
}
.stApp{background:var(--paper);}
[data-testid="stMainBlockContainer"],.block-container{padding-top:2rem;max-width:1280px;}
footer{visibility:hidden;}
h1,h2,h3{font-family:var(--serif)!important;color:var(--ink);letter-spacing:-0.01em;}
[data-testid="stSidebar"]{border-right:1px solid var(--line);}

/* Hero */
.hero{padding:.25rem 0 1.1rem;}
.hero__title{font-family:var(--serif);font-size:2.7rem;line-height:1.05;font-weight:700;color:var(--ink);}
.hero__sub{color:var(--muted);font-size:1.05rem;max-width:44rem;margin-top:.45rem;}
.chips{display:flex;flex-wrap:wrap;gap:.5rem;margin:.9rem 0 .4rem;}
.chip{display:inline-flex;align-items:center;gap:.4rem;padding:.25rem .75rem;border:1px solid var(--line);
  background:var(--surface);border-radius:999px;font-size:.82rem;color:var(--ink);}
.dot{width:.5rem;height:.5rem;border-radius:50%;background:var(--low);}
.dot--off{background:var(--high);}

/* Empty state */
[data-testid="stFileUploaderDropzone"]{background:var(--surface);border:2px dashed #9AA7BC;border-radius:14px;padding:1.6rem;}
[data-testid="stFileUploaderDropzone"]:hover{border-color:var(--ink);}
.steps{display:grid;grid-template-columns:repeat(3,1fr);margin-top:2.2rem;border-top:1px solid var(--line);}
.step{padding:1.3rem 1.5rem 0 0;}
.step + .step{padding-left:1.5rem;border-left:1px solid var(--line);}
.step__n{font-family:var(--serif);font-size:2.4rem;line-height:1;color:var(--ink);}
.step__t{font-weight:700;color:var(--ink);margin-top:.45rem;}
.step__d{color:var(--muted);font-size:.95rem;margin:.2rem 0 0;}
@media (max-width:760px){
  .steps{grid-template-columns:1fr;}
  .step + .step{border-left:0;padding-left:0;border-top:1px solid var(--line);margin-top:1rem;}
}

/* Document viewer */
.doc{max-height:640px;overflow-y:auto;background:var(--surface);border:1px solid var(--line);border-radius:10px;}
.doc-page + .doc-page{border-top:1px solid var(--line);}
.doc-page__label{position:sticky;top:0;background:#EEF1F6;color:var(--muted);font-size:.8rem;font-weight:600;
  padding:.35rem 1rem;border-bottom:1px solid var(--line);}
.doc-page__text{font-family:var(--serif);font-size:1rem;line-height:1.65;color:var(--ink);padding:1rem 1.25rem;}
.doc mark{background:var(--mark);color:inherit;padding:.05em .1em;border-radius:2px;}

/* Verdict */
.verdict{display:flex;align-items:center;gap:1.1rem;padding:1rem 1.25rem;border-radius:6px;border-left:6px solid;margin:.4rem 0 1rem;}
.verdict--low{background:var(--low-bg);border-color:var(--low);color:var(--low);}
.verdict--medium{background:var(--med-bg);border-color:var(--med);color:var(--med);}
.verdict--high{background:var(--high-bg);border-color:var(--high);color:var(--high);}
.verdict__label{font-family:var(--serif);font-size:1.55rem;font-weight:700;line-height:1.1;}
.verdict__why{color:var(--ink);font-size:.95rem;margin-top:.2rem;}
.meter{display:flex;align-items:flex-end;gap:4px;}
.meter i{display:block;width:10px;border-radius:2px;background:currentColor;opacity:.2;}
.meter i:nth-child(1){height:14px;} .meter i:nth-child(2){height:22px;} .meter i:nth-child(3){height:30px;}
.meter i.on{opacity:1;}

/* Evidence */
.evidence{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:1rem 1.25rem;margin:1rem 0;}
.evidence--bad{border:1px dashed var(--high);}
.evidence__head{display:flex;justify-content:space-between;align-items:center;gap:.75rem;flex-wrap:wrap;margin-bottom:.5rem;}
.evidence__title{font-weight:700;color:var(--ink);}
.evidence__quote{font-family:var(--serif);font-size:1.08rem;line-height:1.75;color:var(--ink);margin:.35rem 0;}
.evidence__quote span{background:linear-gradient(transparent 50%,var(--mark) 50%);
  -webkit-box-decoration-break:clone;box-decoration-break:clone;}
.evidence--bad .evidence__quote span{background:none;color:var(--muted);}
.badge{font-size:.8rem;font-weight:600;padding:.15rem .65rem;border-radius:999px;}
.badge--ok{background:var(--low-bg);color:var(--low);}
.badge--bad{background:var(--high-bg);color:var(--high);}
.badge--neutral{background:#EEF1F6;color:var(--muted);}

/* Quick scan */
.flag{background:var(--surface);border:1px solid var(--line);border-left:5px solid #8C97AB;border-radius:8px;padding:.8rem 1rem;margin:.6rem 0;}
.flag--high{border-left-color:var(--high);}
.flag--medium{border-left-color:var(--med);}
.flag__head{display:flex;align-items:center;gap:.6rem;flex-wrap:wrap;}
.flag__title{font-family:var(--serif);font-weight:700;font-size:1.1rem;color:var(--ink);}
.flag__meta{color:var(--muted);font-size:.82rem;margin-left:auto;}
.flag__why{color:var(--muted);font-size:.92rem;margin:.25rem 0 .4rem;}
.flag__snip{font-family:var(--serif);font-size:.95rem;line-height:1.55;color:var(--ink);margin:.35rem 0 0;padding-left:.7rem;border-left:2px solid var(--mark);}
.flag__snip mark{background:var(--mark);color:inherit;padding:0 .1em;border-radius:2px;}
.sev--high{background:var(--high-bg);color:var(--high);}
.sev--medium{background:var(--med-bg);color:var(--med);}
.sev--info{background:#EEF1F6;color:var(--muted);}
.facts__row{display:flex;flex-wrap:wrap;gap:.4rem;align-items:center;margin:.55rem 0;}
.facts__label{font-weight:700;color:var(--ink);min-width:6.5rem;font-size:.9rem;}

/* Law library notice */
.lawnote{background:var(--surface);border:1px solid var(--line);border-left:5px solid var(--ink);border-radius:8px;
  padding:.6rem 1rem;margin:.4rem 0 .8rem;color:var(--muted);font-size:.88rem;}
.lawnote b{color:var(--ink);}

/* Controls */
.stButton>button{border-radius:8px;font-weight:600;}
</style>"""

LEVELS = {"LOW": (1, "low", "Low risk"), "MEDIUM": (2, "medium", "Medium risk"), "HIGH": (3, "high", "High risk")}
STATUS_TEXT = {
    "ready": "Local model ready",
    "offline": "Ollama is not running",
    "missing": "Model not installed",
}
QUOTE_RE = re.compile(r'["\u201c]([^"\u201d]{10,}?)["\u201d]')
SECTION_RE = re.compile(r"^#{2,4}[^\n]*?(Analysis|Risk Level|Relevant Clause)[^\n]*\n", re.I | re.M)


# --------------------------------------------------------------------------- #
# Escaping
# --------------------------------------------------------------------------- #
def esc(text) -> str:
    """Escape text for safe injection into HTML (also neutralises $ and newlines)."""
    return html.escape(str(text)).replace("$", "&#36;").replace("\n", "<br>")


def md_safe(text: str) -> str:
    """Stop Streamlit treating $...$ (common in contracts) as LaTeX."""
    return text.replace("$", "\\$")


# --------------------------------------------------------------------------- #
# Parsing the model's answer
# --------------------------------------------------------------------------- #
def parse_answer(answer: str):
    """Split the model output into {'analysis', 'risk level', 'relevant clause'} or None."""
    matches = list(SECTION_RE.finditer(answer))
    sections = {}
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(answer)
        sections[m.group(1).lower()] = answer[m.end():end].strip()
    needed = {"analysis", "risk level", "relevant clause"}
    return sections if needed <= sections.keys() else None


def parse_risk(text: str):
    """'HIGH - reason' -> ('HIGH', 'reason'); (None, text) if no level is found."""
    m = re.search(r"\b(LOW|MEDIUM|HIGH)\b", text, re.I)
    if not m:
        return None, text.strip()
    return m.group(1).upper(), text[m.end():].lstrip(" -\u2013\u2014:*").strip()


def clause_quotes(clause: str) -> list[str]:
    quotes = [q.strip() for q in QUOTE_RE.findall(clause)]
    return quotes or ([clause.strip()] if clause.strip() else [])


def highlight_fragments(quotes: list[str]) -> list[str]:
    frags = []
    for q in quotes:
        for f in re.split(r"\.\.\.|\u2026", q):
            f = f.strip(" .,;:\"'\u201c\u201d")
            if len(f) >= 10:
                frags.append(f)
    return frags


# --------------------------------------------------------------------------- #
# HTML builders
# --------------------------------------------------------------------------- #
def hero_html(status: str, model: str) -> str:
    dot = "dot" if status == "ready" else "dot dot--off"
    label = STATUS_TEXT.get(status, "Status unknown")
    suffix = f" ({esc(model)})" if status == "ready" else ""
    return (
        '<div class="hero"><div class="hero__title">LegalLens</div>'
        '<div class="hero__sub">Ask a question about a contract and see the exact clause behind the answer. '
        "Everything runs on this computer.</div>"
        f'<div class="chips"><span class="chip"><span class="{dot}"></span>{label}{suffix}</span>'
        '<span class="chip">Not legal advice</span></div></div>'
    )


def steps_html() -> str:
    steps = [
        ("1", "Upload", "Drop in a contract as a PDF. It is read on this computer and never sent anywhere."),
        ("2", "Ask", "Type a question, or leave it blank for a full triage of risks, deadlines and penalties."),
        ("3", "Check the quote",
         "Every answer quotes a clause. LegalLens confirms the wording really appears in your PDF and highlights it."),
    ]
    items = "".join(
        f'<div class="step"><div class="step__n">{n}</div><div class="step__t">{t}</div><p class="step__d">{d}</p></div>'
        for n, t, d in steps
    )
    return f'<div class="steps">{items}</div>'


def law_banner_html(kind_label: str, note: str) -> str:
    """Notice shown above a document that came from the law library."""
    return f'<div class="lawnote"><b>{esc(kind_label)} from the law library.</b> {esc(note)}</div>'


def chips_html(*labels: str) -> str:
    return '<div class="chips">' + "".join(f'<span class="chip">{esc(l)}</span>' for l in labels) + "</div>"


def verdict_html(level: str, why: str) -> str:
    n, cls, label = LEVELS[level]
    bars = "".join(f'<i class="{"on" if i < n else ""}"></i>' for i in range(3))
    return (
        f'<div class="verdict verdict--{cls}"><div class="meter">{bars}</div>'
        f'<div><div class="verdict__label">{label}</div><div class="verdict__why">{esc(why)}</div></div></div>'
    )


def evidence_html(quotes: list[str], grounded, pages: list[int]) -> str:
    if grounded is True:
        where = f"page{'s' if len(pages) > 1 else ''} {', '.join(map(str, pages))}" if pages else "the PDF"
        badge = f'<span class="badge badge--ok">\u2713 Verified on {where}</span>'
    elif grounded is False:
        badge = '<span class="badge badge--bad">Not found word for word in the PDF</span>'
    else:
        badge = '<span class="badge badge--neutral">Could not be checked</span>'
    cls = "evidence evidence--bad" if grounded is False else "evidence"
    body = "".join(f'<p class="evidence__quote"><span>{esc(q)}</span></p>' for q in quotes)
    return (
        f'<div class="{cls}"><div class="evidence__head">'
        f'<span class="evidence__title">Quoted clause</span>{badge}</div>{body}</div>'
    )


def highlight_text(text: str, fragments: list[str]) -> str:
    """Escape `text` and wrap any occurrence of the fragments in <mark>."""
    spans = []
    for frag in fragments:
        words = frag.split()
        if not words:
            continue
        pattern = r"\s+".join(re.escape(w) for w in words)
        spans += [m.span() for m in re.finditer(pattern, text, re.I)]
    out, last = [], 0
    for start, end in sorted(spans):
        if start < last:  # overlapping match
            continue
        out.append(esc(text[last:start]))
        out.append(f"<mark>{esc(text[start:end])}</mark>")
        last = end
    out.append(esc(text[last:]))
    return "".join(out)


def document_html(pages: list[dict], selected, fragments: list[str]) -> str:
    parts = []
    for p in pages:
        if selected != "All pages" and p["page"] != selected:
            continue
        body = highlight_text(p["text"], fragments) if p["text"] else "<i>No readable text on this page.</i>"
        parts.append(
            f'<div class="doc-page"><div class="doc-page__label">Page {p["page"]}</div>'
            f'<div class="doc-page__text">{body}</div></div>'
        )
    return f'<div class="doc">{"".join(parts)}</div>'


PRIORITY = {"high": "Look closely", "medium": "Check", "info": "Note"}
FACT_TITLES = {"money": "Money", "periods": "Time periods", "dates": "Dates"}


def scan_html(findings: list[dict]) -> str:
    cards = []
    for f in findings:
        shown = ", ".join(map(str, f["pages"][:6])) + ("\u2026" if len(f["pages"]) > 6 else "")
        meta = f"{f['count']} mention{'s' if f['count'] != 1 else ''}, page{'s' if len(f['pages']) != 1 else ''} {shown}"
        snips = "".join(
            f'<p class="flag__snip">{esc(h["before"])}<mark>{esc(h["match"])}</mark>{esc(h["after"])}</p>'
            for h in f["hits"][:2]
        )
        cards.append(
            f'<div class="flag flag--{f["severity"]}"><div class="flag__head">'
            f'<span class="flag__title">{esc(f["label"])}</span>'
            f'<span class="badge sev--{f["severity"]}">{PRIORITY[f["severity"]]}</span>'
            f'<span class="flag__meta">{esc(meta)}</span></div>'
            f'<div class="flag__why">{esc(f["why"])}</div>{snips}</div>'
        )
    return "".join(cards)


def facts_html(facts: dict) -> str:
    rows = []
    for kind, title in FACT_TITLES.items():
        items = facts.get(kind, [])
        if items:
            chips = "".join(f'<span class="chip">{esc(i["text"])} (page {i["page"]})</span>' for i in items)
            rows.append(f'<div class="facts__row"><span class="facts__label">{title}</span>{chips}</div>')
    return "".join(rows)
