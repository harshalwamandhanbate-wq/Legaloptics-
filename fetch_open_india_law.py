"""Stream a few documents from Open India Law and save each as a PDF for LegalLens.

The PDFs go to datasets/open_india_law/<kind>/ (kind = legislation, regulations or
judgments). LegalLens lists everything in that folder under "Law library" in the
sidebar, and tells the model whether it is reading an Act, a regulation or a judgment.

One-time setup:
    pip install datasets fpdf2
    huggingface-cli login          # and accept the conditions on the dataset page

Examples (run from the LegalLens folder):

    # 3 Central Acts whose title contains "Contract"
    python fetch_open_india_law.py --kind legislation --title-contains "Contract" --limit 3

    # 3 SEBI regulations
    python fetch_open_india_law.py --kind regulations --file in_sebi_regulations.parquet --limit 3

    # 3 Kerala High Court judgments (chunks are re-joined per case)
    python fetch_open_india_law.py --kind judgments --file in_kerala_judgments.parquet --limit 3

Data: Open India Law by Vaquill AI, CC BY 4.0, snapshot v2026.08. It is a
point-in-time archive, not current law and not legal advice. Keep the output
folder out of Git and credit the source if you publish results.

Field names are taken from the dataset card (legislation: act_id, title,
section_number, section_title, text, source_url; judgments: case_id,
chunk_index). If a field is missing for another file, the script prints the
column names it saw so you can adjust the key lists below.
"""
import argparse
import re
import sys
from pathlib import Path

from library import ATTRIBUTION, LIBRARY_DIR

DOC_KEYS = ["act_id", "instrument_id", "regulation_id", "doc_id", "case_id", "source_url"]
TEXT_KEYS = ["text", "content", "chunk_text"]

REPLACEMENTS = {
    "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"', "\u2013": "-", "\u2014": "-",
    "\u2026": "...", "\u20b9": "Rs.", "\u00a0": " ", "\u2022": "-", "\u2212": "-",
}


def first(row: dict, keys: list[str], default=None):
    for k in keys:
        if row.get(k) not in (None, ""):
            return row[k]
    return default


def pdf_safe(text: str) -> str:
    """The built-in PDF fonts only cover Latin-1, so swap common symbols and drop the rest."""
    for old, new in REPLACEMENTS.items():
        text = text.replace(old, new)
    text = text.encode("latin-1", "replace").decode("latin-1")
    return re.sub(r"(\S{70})(?=\S)", r"\1 ", text)  # break very long tokens so lines can wrap


def slug(text: str, n: int = 50) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_")[:n] or "document"


# --------------------------------------------------------------------------- #
def open_stream(kind: str, data_file: str | None):
    from datasets import load_dataset

    try:
        if data_file:
            return load_dataset("vaquill/open-india-law", data_files=data_file, split="train", streaming=True)
        return load_dataset("vaquill/open-india-law", kind, split="train", streaming=True)
    except Exception as e:  # noqa: BLE001 - show a helpful hint for the usual causes
        sys.exit(
            f"Could not open the dataset: {e}\n\n"
            "Check that you ran `huggingface-cli login`, accepted the conditions on\n"
            "https://huggingface.co/datasets/vaquill/open-india-law and that the --file name exists."
        )


def collect(rows, kind: str, limit: int, title_contains: str | None, max_rows: int) -> dict:
    """Group consecutive rows into documents. Stops once `limit` documents are complete.

    Assumes the rows of one document sit next to each other. The script warns if that is wrong.
    """
    docs: dict[str, dict] = {}
    current = None
    scanned = 0
    warned_cols = False

    for row in rows:
        scanned += 1
        if scanned > max_rows:
            print(f"Stopped after scanning {max_rows:,} rows (raise --max-rows to look further).")
            break
        if not warned_cols:
            print("Columns seen:", ", ".join(sorted(row.keys())))
            warned_cols = True

        title = str(row.get("title") or "")
        if title_contains and title_contains.lower() not in title.lower():
            if current is not None and len(docs) >= limit:
                break
            continue

        key = str(first(row, DOC_KEYS, default=title or f"row{scanned}"))
        if key not in docs:
            if len(docs) >= limit:
                break  # a new document appeared after we already have enough complete ones
            docs[key] = {"title": title or key, "source_url": row.get("source_url") or "", "rows": []}
        elif key != current:
            print(f"Warning: rows for {key} are not contiguous; the document may be partial.")
        current = key
        docs[key]["rows"].append(row)

    return docs


def document_text(doc: dict, kind: str) -> str:
    rows = doc["rows"]
    if kind == "judgments":
        rows = sorted(rows, key=lambda r: r.get("chunk_index") or 0)
    parts = []
    for r in rows:
        body = str(first(r, TEXT_KEYS, default="")).strip()
        if not body:
            continue
        head = " ".join(str(x) for x in (
            f"Section {r['section_number']}." if r.get("section_number") else "",
            r.get("section_title") or "",
        ) if x).strip()
        parts.append(f"{head}\n{body}" if head else body)
    return "\n\n".join(parts)


def write_pdf(path: Path, title: str, source_url: str, body: str) -> None:
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.multi_cell(0, 7, pdf_safe(title), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "I", 8)
    meta = ATTRIBUTION + (f" Original: {source_url}" if source_url else "")
    pdf.multi_cell(0, 4, pdf_safe(meta), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    pdf.set_font("Helvetica", "", 10)
    for para in body.split("\n"):
        if para.strip():
            pdf.multi_cell(0, 5, pdf_safe(para), new_x="LMARGIN", new_y="NEXT")
        else:
            pdf.ln(2)
    path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(path))


def main():
    ap = argparse.ArgumentParser(description="Save Open India Law documents as PDFs.")
    ap.add_argument("--kind", choices=["legislation", "regulations", "judgments"], required=True)
    ap.add_argument("--file", help="Parquet file name, e.g. in_sebi_regulations.parquet (needed for judgments)")
    ap.add_argument("--title-contains", help="Only keep documents whose title contains this text")
    ap.add_argument("--limit", type=int, default=3, help="How many documents to save (default 3)")
    ap.add_argument("--max-rows", type=int, default=300_000, help="Give up after scanning this many rows")
    ap.add_argument("--out", default=str(LIBRARY_DIR), help="Library folder (default: datasets/open_india_law)")
    args = ap.parse_args()

    if args.kind == "judgments" and not args.file:
        sys.exit("Judgments are split by court. Pass --file, for example in_kerala_judgments.parquet")

    rows = open_stream(args.kind, args.file)
    docs = collect(rows, args.kind, args.limit, args.title_contains, args.max_rows)
    if not docs:
        sys.exit("No matching documents found. Try a different --title-contains or a larger --max-rows.")

    out_dir = Path(args.out) / args.kind   # the sub-folder tells LegalLens the document type
    for key, doc in docs.items():
        body = document_text(doc, args.kind)
        if not body:
            print(f"Skipped {key}: no text field found.")
            continue
        path = out_dir / f"{slug(doc['title'])}_{slug(key, 20)}.pdf"
        write_pdf(path, doc["title"], doc["source_url"], body)
        print(f"Saved {path}  ({len(doc['rows'])} rows, {len(body):,} characters)")

    print("\nRestart or reload LegalLens and pick them under 'Law library' in the sidebar.")
    print("Long ones will show the 'only the most relevant excerpts' warning.")


if __name__ == "__main__":
    main()
