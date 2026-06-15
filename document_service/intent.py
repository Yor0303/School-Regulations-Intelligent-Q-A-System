# -*- encoding: utf-8 -*-
import json
import re
from typing import Dict, List, Optional

from document_service.registry import get_document_types, match_type_by_keywords


INTENT_PROMPT = """你是上海大学办事文书意图识别助手。根据用户描述，判断需要生成哪一种办事文书，并抽取已知信息。

可选文书类型（document_type_id）：
- deferred_exam：缓考申请说明
- suspension_study：休学申请陈述书
- leave_absence：请假申请说明（事假/病假/不能上课）
- exam_exemption：免考/免修申请说明
- return_to_study：复学申请陈述书
- unknown：无法判断或与校规办事无关

用户描述：
{user_text}

请只返回 JSON，不要其他文字：
{{
  "document_type_id": "类型 id 或 unknown",
  "slots": {{
    "student_name": "姓名或空字符串",
    "student_id": "学号或空",
    "college": "学院或空",
    "major": "专业或空",
    "course_name": "课程名或空",
    "exam_date": "考试日期或空",
    "reason": "原因说明或空",
    "start_date": "开始日期或空",
    "end_date": "结束日期或空",
    "leave_start": "请假开始或空",
    "leave_end": "请假结束或空",
    "return_date": "复学日期或空",
    "contact": "联系方式或空",
    "phone": "手机或空"
  }},
  "brief_summary": "一句话概括用户诉求"
}}"""


def _parse_json(text: str) -> Optional[Dict]:
    if not text:
        return None
    text = text.strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if m:
        text = m.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        text = text[start : end + 1]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _get_llm():
    from graph_engine import _get_llm as get_llm

    return get_llm()


def detect_intent_with_llm(user_text: str) -> Optional[Dict]:
    try:
        llm = _get_llm()
        raw = llm(INTENT_PROMPT.format(user_text=user_text.strip()))
        parsed = _parse_json(raw)
        if parsed and isinstance(parsed, dict):
            return parsed
    except Exception:
        pass
    return None


def detect_intent(user_text: str) -> Dict:
    """Neural: LLM intent + slots; fallback keyword match."""
    result = {
        "document_type_id": "unknown",
        "slots": {},
        "brief_summary": "",
        "match_method": "none",
    }

    llm_result = detect_intent_with_llm(user_text)
    if llm_result:
        type_id = llm_result.get("document_type_id", "unknown")
        valid_ids = {t["id"] for t in get_document_types()}
        if type_id in valid_ids:
            result["document_type_id"] = type_id
            result["match_method"] = "llm"
        elif type_id == "unknown":
            keyword_match = match_type_by_keywords(user_text)
            if keyword_match:
                result["document_type_id"] = keyword_match["id"]
                result["match_method"] = "keyword_fallback"
        slots = llm_result.get("slots") or {}
        if isinstance(slots, dict):
            result["slots"] = {
                k: str(v).strip()
                for k, v in slots.items()
                if v and str(v).strip()
            }
        result["brief_summary"] = str(llm_result.get("brief_summary", "")).strip()
        if result["document_type_id"] != "unknown":
            return result

    keyword_match = match_type_by_keywords(user_text)
    if keyword_match:
        result["document_type_id"] = keyword_match["id"]
        result["match_method"] = "keyword"
        result["brief_summary"] = user_text.strip()[:120]
        return result

    return result
