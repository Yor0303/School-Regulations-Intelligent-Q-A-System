# -*- encoding: utf-8 -*-
from typing import Dict, List

from knowledge_base import KnowledgeBaseService


VIOLATION_KEYWORDS = {
    "考试违纪": ["作弊", "小抄", "夹带", "代考", "替考", "考试违纪"],
    "课堂考勤违规": ["旷课", "缺课", "缺勤", "逃课"],
    "宿舍管理违规": ["晚归", "夜不归宿", "违章电器", "宿舍违规"],
    "学术不端": ["抄袭", "剽窃", "论文造假", "学术不端"],
}

VIOLATION_TEMPLATES = {
    "考试违纪": "该行为可能构成考试违纪，相关课程成绩可能按零分或无效处理。",
    "课堂考勤违规": "该行为可能构成课堂考勤违规，并可能影响课程考核资格或成绩记载。",
    "宿舍管理违规": "该行为可能构成宿舍管理违规，需结合宿舍管理规定进一步确认处理方式。",
    "学术不端": "该行为可能构成学术不端，需依据学校学术规范和管理制度进一步处理。",
    "未知": "当前行为描述未能直接匹配到明确违规类型，但可以参考相关制度条款进一步判断。",
}


def detect_violation_type(text: str) -> str:
    for violation_type, keywords in VIOLATION_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return violation_type
    return "未知"


def build_violation_query(description: str, violation_type: str) -> str:
    if violation_type == "未知":
        return description

    query_terms = [violation_type, description]
    query_terms.extend(VIOLATION_KEYWORDS.get(violation_type, []))

    if violation_type == "考试违纪":
        query_terms.extend(["成绩处理", "零分", "无效"])
    elif violation_type == "课堂考勤违规":
        query_terms.extend(["缺课", "考核资格", "成绩"])
    elif violation_type == "宿舍管理违规":
        query_terms.extend(["宿舍", "管理规定", "处理"])
    elif violation_type == "学术不端":
        query_terms.extend(["论文", "处理", "规范"])

    return " ".join(dict.fromkeys(query_terms))


def retrieve_violation_rules(description: str, top_k: int = 3) -> List[Dict]:
    violation_type = detect_violation_type(description)
    query_text = build_violation_query(description, violation_type)
    service = KnowledgeBaseService()
    return service.query_documents(query_text, top_k=top_k)


def build_violation_context(docs: List[Dict]) -> str:
    if not docs:
        return ""

    parts = []
    for index, doc in enumerate(docs, start=1):
        source = doc.get("source_label", doc.get("file_name", "unknown"))
        text = doc.get("text", "")
        parts.append(f"[Source {index}] {source}\nContent: {text}")
    return "\n\n".join(parts)


def build_violation_result(
    description: str, violation_type: str, docs: List[Dict]
) -> Dict:
    context = build_violation_context(docs)
    if not docs:
        return {
            "is_violation": False,
            "violation_type": violation_type,
            "conclusion": "未在当前制度文件中找到明确依据。",
            "basis": "当前上传的制度文件中暂无足够内容支持对该行为作出明确判断。",
            "sources": [],
            "context": context,
        }

    basis = docs[0].get("text", "")
    conclusion = VIOLATION_TEMPLATES.get(violation_type, VIOLATION_TEMPLATES["未知"])
    return {
        "is_violation": violation_type != "未知",
        "violation_type": violation_type,
        "conclusion": conclusion,
        "basis": basis,
        "sources": docs,
        "context": context,
    }


def judge_violation(description: str, top_k: int = 3) -> Dict:
    violation_type = detect_violation_type(description)
    docs = retrieve_violation_rules(description, top_k=top_k)
    return build_violation_result(description, violation_type, docs)
