# -*- encoding: utf-8 -*-
from typing import Dict, Optional

from document_service.builder import build_document_bytes, suggest_filename
from document_service.intent import detect_intent
from document_service.registry import get_disclaimer, get_type_by_id
from document_service.regulation_fetcher import (
    fetch_regulations,
    format_regulation_excerpts,
    format_source_list,
    regulations_support_type,
)
from document_service.rule_engine import (
    build_reasoning_chain,
    evaluate_readiness,
    get_missing_required,
    merge_slots,
)


def analyze_document_request(
    user_text: str,
    form_slots: Optional[Dict[str, str]] = None,
    forced_type_id: Optional[str] = None,
) -> Dict:
    """
    Neuro-symbolic analysis without generating the file.
    """
    form_slots = form_slots or {}
    intent = detect_intent(user_text or "")

    type_id = forced_type_id or intent.get("document_type_id", "unknown")
    if type_id == "unknown":
        return {
            "status": "unsupported",
            "message": (
                "未能识别您要办理的文书类型。"
                "请说明具体事项（如休学、缓考、请假、免考、复学等），"
                "或从下拉列表中直接选择文书类型。"
            ),
            "document_type_id": "unknown",
            "slots": {},
            "reasoning_chain": [],
            "regulation_excerpts": "",
            "regulation_sources": [],
            "missing_labels": [],
            "brief_summary": intent.get("brief_summary", ""),
        }

    doc_type = get_type_by_id(type_id)
    if not doc_type:
        return {
            "status": "unsupported",
            "message": "文书类型配置不存在。",
            "document_type_id": type_id,
            "slots": {},
            "reasoning_chain": [],
            "regulation_excerpts": "",
            "regulation_sources": [],
            "missing_labels": [],
        }

    slots = merge_slots(intent.get("slots", {}), form_slots)
    regulation_docs = fetch_regulations(doc_type)
    regulation_supported = regulations_support_type(doc_type, regulation_docs)
    regulation_excerpts = format_regulation_excerpts(regulation_docs)
    regulation_sources = format_source_list(regulation_docs)

    status, issues = evaluate_readiness(type_id, slots, regulation_supported)
    missing_labels = issues if status == "incomplete" else []

    match_method = intent.get("match_method", "manual")
    if forced_type_id:
        match_method = "manual_select"

    reasoning_chain = build_reasoning_chain(
        doc_type,
        match_method,
        regulation_supported,
        regulation_sources,
        slots,
        get_missing_required(doc_type, slots),
    )

    message = ""
    if status == "unsupported":
        message = issues[0] if issues else "制度依据不足，无法生成文书。"
    elif status == "incomplete":
        message = f"请补充必填项：{', '.join(missing_labels)}"
    else:
        message = "信息已齐全，可生成文书草稿。"

    return {
        "status": status,
        "message": message,
        "document_type_id": type_id,
        "document_title": doc_type.get("title", ""),
        "slots": slots,
        "slot_labels": doc_type.get("slot_labels", {}),
        "required_slots": doc_type.get("required_slots", []),
        "optional_slots": doc_type.get("optional_slots", []),
        "reasoning_chain": reasoning_chain,
        "regulation_excerpts": regulation_excerpts,
        "regulation_sources": regulation_sources,
        "regulation_docs": regulation_docs,
        "missing_labels": missing_labels,
        "brief_summary": intent.get("brief_summary", ""),
        "disclaimer": get_disclaimer(),
        "default_attachments": doc_type.get("default_attachments", []),
    }


def generate_document_bytes(analysis: Dict) -> Optional[Dict]:
    if analysis.get("status") != "ready":
        return None

    type_id = analysis.get("document_type_id")
    doc_type = get_type_by_id(type_id)
    if not doc_type:
        return None

    slots = analysis.get("slots", {})
    content = build_document_bytes(doc_type, slots)
    filename = suggest_filename(doc_type, slots.get("student_name", ""))
    return {
        "bytes": content,
        "filename": filename,
        "document_title": doc_type.get("title", ""),
    }
