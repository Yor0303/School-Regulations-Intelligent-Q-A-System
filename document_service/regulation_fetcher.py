# -*- encoding: utf-8 -*-
from typing import Any, Dict, List

from knowledge_base import KnowledgeBaseService


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return " ".join(str(v) for v in value)
    return str(value)


def _doc_key(doc: Dict) -> tuple:
    text = _as_text(doc.get("text", ""))
    return (
        doc.get("file_name"),
        doc.get("page_no"),
        text[:80],
    )


def fetch_regulations(doc_type: Dict, top_k: int = 4) -> List[Dict]:
    queries = doc_type.get("regulation_queries") or [doc_type.get("title", "")]
    service = KnowledgeBaseService()
    seen = set()
    results: List[Dict] = []

    for query in queries:
        docs = service.query_documents(query, top_k=top_k)
        for doc in docs:
            key = _doc_key(doc)
            if key in seen:
                continue
            seen.add(key)
            results.append(doc)

    if len(results) < top_k:
        title_query = doc_type.get("title", "")
        extra = service.query_documents(title_query, top_k=top_k)
        for doc in extra:
            key = _doc_key(doc)
            if key not in seen:
                seen.add(key)
                results.append(doc)

    return results[:top_k]


def regulations_support_type(doc_type: Dict, regulation_docs: List[Dict]) -> bool:
    """Symbolic: corpus must mention at least one regulation signal."""
    signals = doc_type.get("regulation_signals") or []
    if not signals:
        return bool(regulation_docs)

    combined = " ".join(
        piece
        for doc in regulation_docs
        for piece in [
            _as_text(doc.get("text", "")),
            _as_text(doc.get("file_name", "")),
            _as_text(doc.get("section_title")),
            _as_text(doc.get("source_label", "")),
        ]
    )
    return any(signal in combined for signal in signals)


def format_regulation_excerpts(docs: List[Dict], max_chars: int = 600) -> str:
    if not docs:
        return "未检索到相关制度原文。"
    parts = []
    for idx, doc in enumerate(docs, start=1):
        label = _as_text(doc.get("source_label", doc.get("file_name", "")))
        text = _as_text(doc.get("text", "")).strip()
        if len(text) > max_chars:
            text = text[:max_chars] + "…"
        parts.append(f"{idx}. {label}\n{text}")
    return "\n\n".join(parts)


def format_source_list(docs: List[Dict]) -> List[str]:
    labels = []
    for doc in docs:
        label = _as_text(doc.get("source_label", doc.get("file_name", "")))
        if label and label not in labels:
            labels.append(label)
    return labels
