# -*- encoding: utf-8 -*-
from typing import Dict, List, Tuple

from document_service.registry import get_type_by_id


def merge_slots(
    detected_slots: Dict,
    form_slots: Dict,
) -> Dict[str, str]:
    merged: Dict[str, str] = {}
    for key, value in (detected_slots or {}).items():
        if value and str(value).strip():
            merged[key] = str(value).strip()
    for key, value in (form_slots or {}).items():
        if value and str(value).strip():
            merged[key] = str(value).strip()
    return merged


def get_missing_required(doc_type: Dict, slots: Dict[str, str]) -> List[str]:
    labels = doc_type.get("slot_labels") or {}
    missing = []
    for key in doc_type.get("required_slots", []):
        if not slots.get(key, "").strip():
            label = labels.get(key, key)
            missing.append(label)
    return missing


def build_reasoning_chain(
    doc_type: Dict,
    match_method: str,
    regulation_supported: bool,
    regulation_sources: List[str],
    slots: Dict[str, str],
    missing_labels: List[str],
) -> List[str]:
    chain = []
    chain.append(
        f"【符号·类型识别】文书类型：{doc_type.get('title', '')}（识别方式：{match_method}）"
    )
    if regulation_supported:
        chain.append(
            f"【符号·制度校验】知识库中存在与「{', '.join(doc_type.get('regulation_signals', []))}」相关的制度摘录，支持生成此类办事文书草稿。"
        )
    else:
        chain.append(
            "【符号·制度校验】未在已入库制度中找到足够依据，无法 responsibly 生成该文书。"
        )
    if regulation_sources:
        chain.append(
            "【检索·依据来源】"
            + "；".join(regulation_sources[:4])
        )
    if missing_labels:
        chain.append(
            f"【符号·字段校验】尚缺必填项：{', '.join(missing_labels)}"
        )
    else:
        chain.append("【符号·字段校验】必填信息已齐全，可装配文书模板。")
    attachments = doc_type.get("default_attachments") or []
    if attachments:
        chain.append(
            "【符号·材料清单】建议准备："
            + "；".join(attachments)
        )
    return chain


def evaluate_readiness(
    type_id: str,
    slots: Dict[str, str],
    regulation_supported: bool,
) -> Tuple[str, List[str]]:
    """
    Returns status: unsupported | incomplete | ready
    """
    doc_type = get_type_by_id(type_id)
    if not doc_type:
        return "unsupported", ["无法识别的文书类型。"]

    if not regulation_supported:
        return "unsupported", [
            f"当前知识库中未找到与「{doc_type.get('title', '')}」足够相关的制度条文，"
            "无法据此生成办事文书。建议先在「智能问答」中查询相关规定，或向学院/教务处确认。"
        ]

    missing = get_missing_required(doc_type, slots)
    if missing:
        return "incomplete", missing

    return "ready", []
