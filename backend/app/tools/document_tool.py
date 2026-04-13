from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

from pypdf import PdfReader


def _read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _read_pdf_file(path: Path) -> str:
    reader = PdfReader(str(path))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages)


def _score_snippets(content: str, query: str, max_snippets: int = 3) -> List[str]:
    chunks = [c.strip() for c in re.split(r"\n\s*\n", content) if c.strip()]
    if not chunks:
        return []

    query_terms = [t.lower() for t in re.findall(r"\w+", query) if len(t) > 2]
    scored: List[Tuple[float, str]] = []
    for chunk in chunks:
        words = [t.lower() for t in re.findall(r"\w+", chunk)]
        chunk_lc = chunk.lower()
        if not words:
            continue

        # Frequency-aware scoring gives preference to substantive chunks over titles.
        overlap_score = sum(words.count(term) for term in query_terms)
        coverage_score = len(set(query_terms).intersection(set(words))) * 1.5

        # Boost chunks that explicitly mention common file formats when asked about formats/docs.
        format_boost = 0.0
        if any(term in query_terms for term in {"format", "file", "document", "pdf", "txt", "md"}):
            if any(token in chunk_lc for token in {".pdf", ".txt", ".md", "pdf", "markdown", "text file"}):
                format_boost = 3.0

        length_bonus = min(len(chunk), 800) / 800.0
        score = overlap_score + coverage_score + format_boost + length_bonus
        scored.append((score, chunk[:600]))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [text for score, text in scored[:max_snippets] if score > 0] or [chunks[0][:600]]


def document_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    query = str(args.get("query", "")).strip()
    path_arg = str(args.get("path", "")).strip()
    docs_root = Path(args.get("docs_root", "./docs"))

    if path_arg:
        candidates = [Path(path_arg)]
    else:
        if not docs_root.exists():
            return {"error": f"docs root does not exist: {docs_root}"}
        candidates = [
            p
            for p in docs_root.rglob("*")
            if p.is_file() and p.suffix.lower() in {".txt", ".md", ".pdf"}
        ]

    if not candidates:
        return {"error": "No documents found"}

    docs = []
    for file_path in candidates[:10]:
        try:
            suffix = file_path.suffix.lower()
            if suffix == ".pdf":
                content = _read_pdf_file(file_path)
            else:
                content = _read_text_file(file_path)
            snippets = _score_snippets(content, query or file_path.name)
            docs.append({"path": str(file_path), "snippets": snippets})
        except Exception as exc:
            docs.append({"path": str(file_path), "error": str(exc)})

    return {"query": query, "documents": docs[:5]}
