"""Instant, rule-based scan of a contract: red-flag wording and key facts.

No AI is involved, so the result is immediate and always the same for the same
document. It spots wording, not meaning, so treat it as a checklist of where to
look, not as a verdict.
"""
import re

# (label, severity, plain-language reason, regex)
FLAGS = [
    ("Automatic renewal", "high",
     "The contract may renew by itself. Look for how far ahead you must give notice to stop it.",
     r"auto(?:matic(?:ally)?)?[\s-]*renew\w*|renews?\s+automatically"),
    ("Liability and indemnity", "high",
     "Who pays when something goes wrong. One-sided wording here can be very costly.",
     r"\bindemnif\w*|\bhold\s+harmless\b|\bliabilit\w*"),
    ("Penalties and fines", "high",
     "Money you may owe for breaking a rule, missing a deadline or paying late.",
     r"\bpenalt(?:y|ies)\b|\bfines?\b|liquidated\s+damages|late\s+fees?|forfeit\w*"),
    ("Non-compete and exclusivity", "high",
     "Limits on working with other people or companies, during and after the contract.",
     r"non-?compet\w*|\bexclusiv\w*|non-?solicit\w*"),
    ("One-sided changes", "high",
     "Wording that lets one side change terms or act without asking the other.",
     r"sole\s+discretion|without\s+(?:prior\s+)?(?:notice|consent)|\bunilateral\w*"),
    ("Termination", "medium",
     "Who can end the contract, how, and what happens afterwards.",
     r"\bterminat\w*"),
    ("Payment terms", "medium",
     "How much is paid, when, and what happens if it is late.",
     r"\bpayment\w*|\binvoice\w*|\bpayable\b"),
    ("Intellectual property", "medium",
     "Who owns the work, ideas or materials created under the contract.",
     r"intellectual\s+property|\bcopyright\w*|work\s+made\s+for\s+hire|\bassigns?\b"),
    ("Disputes and governing law", "medium",
     "Which law applies and where disagreements are settled.",
     r"\barbitrat\w*|governing\s+law|\bjurisdiction\b|\bvenue\b"),
    ("Confidentiality", "info",
     "What must be kept secret, and for how long.",
     r"\bconfidential\w*|trade\s+secrets?|non-?disclosure"),
]
SEVERITY_ORDER = {"high": 0, "medium": 1, "info": 2}

_MONTH = (r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|June?|July?|Aug(?:ust)?|"
          r"Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)")
FACT_PATTERNS = {
    "money": (re.compile(
        r"(?:\u20b9|Rs\.?|INR|USD|EUR|GBP|[$\u20ac\u00a3])\s?\d[\d,]*(?:\.\d+)?"
        r"(?:\s?(?:lakhs?|crores?|million|billion|thousand))?"
        r"|\b\d[\d,]*(?:\.\d+)?\s?(?:dollars|rupees|euros)\b"), 0),
    "periods": (re.compile(
        r"\b\d{1,3}\)?\s?(?:calendar\s|business\s|working\s)?(?:days?|weeks?|months?|years?)\b", re.I), 0),
    "dates": (re.compile(
        rf"\b{_MONTH}\.?\s\d{{1,2}}(?:st|nd|rd|th)?,?\s\d{{4}}\b"
        rf"|\b\d{{1,2}}(?:st|nd|rd|th)?\s(?:of\s)?{_MONTH}\.?,?\s\d{{4}}\b"
        r"|\b\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}\b|\b\d{4}-\d{2}-\d{2}\b", re.I), 0),
}
MAX_SNIPPETS = 3
MAX_FACTS = 8


def _flat(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def _snippet(flat: str, m: re.Match, before: int = 90, after: int = 120):
    """Return (before, match, after) text around a match, snapped to word edges."""
    s = max(0, m.start() - before)
    e = min(len(flat), m.end() + after)
    if s > 0:
        s = flat.rfind(" ", 0, s) + 1
    idx = flat.find(" ", e)
    e = idx if idx != -1 else len(flat)
    pre = ("\u2026" if s > 0 else "") + flat[s:m.start()]
    post = flat[m.end():e] + ("\u2026" if e < len(flat) else "")
    return pre, m.group(0), post


def scan_flags(pages: list[dict]) -> list[dict]:
    compiled = [(label, sev, why, re.compile(rx, re.I)) for label, sev, why, rx in FLAGS]
    findings = []
    for label, sev, why, rx in compiled:
        hits, count, found_pages = [], 0, set()
        for p in pages:
            flat = _flat(p["text"])
            for m in rx.finditer(flat):
                count += 1
                found_pages.add(p["page"])
                if len(hits) < MAX_SNIPPETS:
                    pre, match, post = _snippet(flat, m)
                    hits.append({"page": p["page"], "before": pre, "match": match, "after": post})
        if count:
            findings.append({
                "label": label, "severity": sev, "why": why,
                "count": count, "pages": sorted(found_pages), "hits": hits,
            })
    findings.sort(key=lambda f: (SEVERITY_ORDER[f["severity"]], -f["count"]))
    return findings


def extract_facts(pages: list[dict]) -> dict[str, list[dict]]:
    facts = {}
    for kind, (rx, _) in FACT_PATTERNS.items():
        seen, items = set(), []
        for p in pages:
            for m in rx.finditer(_flat(p["text"])):
                text = m.group(0).replace(")", "").strip()
                key = text.lower()
                if key in seen:
                    continue
                seen.add(key)
                items.append({"text": text, "page": p["page"]})
        facts[kind] = items[:MAX_FACTS]
    return facts


def scan_document(pages: list[dict]) -> dict:
    return {"findings": scan_flags(pages), "facts": extract_facts(pages)}
