"""The local law library: PDFs fetched from Open India Law (see fetch_open_india_law.py).

Files live in datasets/open_india_law/<kind>/ where <kind> is legislation,
regulations or judgments. The sub-folder tells LegalLens what kind of document
it is looking at, so the model is told it is reading a statute, not a contract.

This module has no heavy imports, so the tests and the fetch script can use it.
"""
from pathlib import Path

LIBRARY_DIR = Path(__file__).parent / "datasets" / "open_india_law"

# sub-folder name -> document type used by ai_agent.analyze_legal_text
FOLDER_KINDS = {"legislation": "legislation", "regulations": "regulation", "judgments": "judgment"}
KIND_LABEL = {
    "contract": "Contract",
    "legislation": "Act",
    "regulation": "Regulation",
    "judgment": "Judgment",
}
ATTRIBUTION = (
    "Source: Open India Law by Vaquill AI (CC BY 4.0), snapshot v2026.08. "
    "This is an archive as of the snapshot date, not current law, and not legal advice."
)


def doc_kind_for(path: Path, root: Path = LIBRARY_DIR) -> str:
    """Document type for a file inside the library. Files outside it are contracts."""
    try:
        rel = Path(path).resolve().relative_to(Path(root).resolve())
    except ValueError:
        return "contract"
    if len(rel.parts) > 1:
        return FOLDER_KINDS.get(rel.parts[0], "legislation")
    return "legislation"  # a PDF dropped straight into the library folder


def _label(path: Path, kind: str) -> str:
    name = path.stem.replace("_", " ").strip()
    if len(name) > 60:
        name = name[:57] + "..."
    return f"{KIND_LABEL[kind]}: {name}"


def list_library(root: Path = LIBRARY_DIR) -> list[dict]:
    """Every PDF in the library as {"label", "path", "kind"}, sorted by label."""
    root = Path(root)
    if not root.exists():
        return []
    items = []
    for p in root.rglob("*.pdf"):
        kind = doc_kind_for(p, root)
        items.append({"label": _label(p, kind), "path": p, "kind": kind})
    items.sort(key=lambda i: i["label"].lower())
    # Two files can share a label; keep the picker unambiguous
    seen: dict[str, int] = {}
    for item in items:
        n = seen.get(item["label"], 0)
        seen[item["label"]] = n + 1
        if n:
            item["label"] = f"{item['label']} ({n + 1})"
    return items
