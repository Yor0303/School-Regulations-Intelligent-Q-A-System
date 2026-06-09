# -*- encoding: utf-8 -*-
from typing import Dict, List, Optional

from knowledge_base import KnowledgeBaseService


VIOLATION_KEYWORDS = {
    "考试违纪": [
        "作弊", "小抄", "夹带", "代考", "替考", "考试违纪",
        "抄袭", "偷看", "传纸条", "传答案",
        "手机", "通讯设备", "电子设备", "智能手表",
        "考试看", "考场看", "考试期间使用",
    ],
    "课堂考勤违规": [
        "旷课", "缺课", "缺勤", "逃课",
        "迟到", "早退", "上课没去", "翘课",
        "代签到", "替签到", "替到", "代到",
    ],
    "宿舍管理违规": [
        "晚归", "夜不归宿", "违章电器", "宿舍违规",
        "宿舍打架", "私自换宿", "私自外宿",
        "热得快", "大功率电器", "电热毯",
        "私拉电线", "酗酒", "吸烟",
    ],
    "学术不端": [
        "抄袭", "剽窃", "论文造假", "学术不端",
        "数据造假", "伪造", "篡改", "代写",
        "买论文", "卖论文",
    ],
}

VIOLATION_TEMPLATES = {
    "考试违纪": "该行为可能构成考试违纪，相关课程成绩可能按零分或无效处理，并可能根据情节给予纪律处分。",
    "课堂考勤违规": "该行为可能构成课堂考勤违规，并可能影响课程考核资格或成绩记载。",
    "宿舍管理违规": "该行为可能构成宿舍管理违规，需结合宿舍管理规定进一步确认处理方式。",
    "学术不端": "该行为可能构成学术不端，需依据学校学术规范和管理制度进一步处理。",
    "未知": "当前行为描述未能直接匹配到明确违规类型，但可以参考相关制度条款进一步判断。",
}


# ---------------------------------------------------------------------------
#  Classification: keyword-first, LLM fallback
# ---------------------------------------------------------------------------

def detect_violation_type_by_keywords(text: str) -> str:
    """Fast keyword-based detection. Returns '未知' if no match."""
    for violation_type, keywords in VIOLATION_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return violation_type
    return "未知"


CLASSIFY_PROMPT = """你是上海大学校规合规分析助手。请判断以下学生行为属于哪一类违规：

可选类别：
- 考试违纪（考试中作弊、携带违禁物品、传递答案、代考替考等）
- 课堂考勤违规（旷课、迟到、早退、代签到、翘课等）
- 宿舍管理违规（晚归、违章电器、私自外宿、宿舍打架等）
- 学术不端（论文抄袭、数据造假、代写论文等）
- 未知（无法归类到以上任一类别）

学生行为描述：
{description}

请只回答类别名称，不要解释。例如："考试违纪" 或 "未知"。"""


def classify_with_llm(description: str) -> str:
    """Use LLM to classify the violation type semantically."""
    try:
        from graph_engine import _get_llm
        llm = _get_llm()
        prompt = CLASSIFY_PROMPT.format(description=description.strip())
        result = llm(prompt) or ""
        result = result.strip().strip('"').strip("'").strip("。").strip()

        valid_types = {"考试违纪", "课堂考勤违规", "宿舍管理违规", "学术不端", "未知"}
        for vtype in valid_types:
            if vtype in result:
                return vtype
        return "未知"
    except Exception:
        return "未知"


def detect_violation_type(text: str) -> str:
    """Hybrid classification: try keywords first, fall back to LLM."""
    keyword_match = detect_violation_type_by_keywords(text)
    if keyword_match != "未知":
        return keyword_match
    return classify_with_llm(text)


# ---------------------------------------------------------------------------
#  Retrieval
# ---------------------------------------------------------------------------

def build_violation_query(description: str, violation_type: str) -> str:
    if violation_type == "未知":
        return description

    query_terms = [violation_type, description]
    query_terms.extend(VIOLATION_KEYWORDS.get(violation_type, []))

    if violation_type == "考试违纪":
        query_terms.extend(["成绩处理", "零分", "无效", "纪律处分"])
    elif violation_type == "课堂考勤违规":
        query_terms.extend(["缺课", "考核资格", "成绩"])
    elif violation_type == "宿舍管理违规":
        query_terms.extend(["宿舍", "管理规定", "处理"])
    elif violation_type == "学术不端":
        query_terms.extend(["论文", "处理", "规范"])

    return " ".join(dict.fromkeys(query_terms))


def retrieve_violation_rules(description: str, top_k: int = 3, violation_type: Optional[str] = None) -> List[Dict]:
    if violation_type is None:
        violation_type = detect_violation_type(description)
    query_text = build_violation_query(description, violation_type)
    service = KnowledgeBaseService()
    return service.query_documents(query_text, top_k=top_k)


# ---------------------------------------------------------------------------
#  LLM-driven conclusion generation
# ---------------------------------------------------------------------------

CONCLUSION_PROMPT = """你是上海大学校规合规咨询助手。请基于检索到的校规原文，对学生行为做出合规判断。

学生行为描述：
{description}

初步判定违规类型：{violation_type}

检索到的相关校规原文：
{context}

请按以下格式给出回复（用简体中文，语气专业）：
1. 结论：明确说该行为是否构成违规、可能构成哪类违规；如果原文没有完全对应，请如实说明。
2. 依据：用通俗语言转述相关校规条款（不要逐字照搬，可以分点说明）。
3. 处理：依据校规说明可能的处理后果。
4. 建议：给学生 1-2 句合规建议。

不要在回复中出现 [Source X] 之类的引用标记。"""


def _build_violation_context(docs: List[Dict]) -> str:
    if not docs:
        return ""
    parts = []
    for index, doc in enumerate(docs, start=1):
        source = doc.get("source_label", doc.get("file_name", "unknown"))
        text = doc.get("text", "")
        parts.append(f"[Source {index}] {source}\n{text}")
    return "\n\n".join(parts)


def _generate_conclusion_with_llm(
    description: str,
    violation_type: str,
    docs: List[Dict],
) -> Optional[str]:
    if not docs:
        return None
    try:
        from graph_engine import _get_llm
        llm = _get_llm()
        context = _build_violation_context(docs)
        prompt = CONCLUSION_PROMPT.format(
            description=description.strip(),
            violation_type=violation_type,
            context=context,
        )
        result = llm(prompt) or ""
        return result.strip() if result.strip() else None
    except Exception:
        return None


# ---------------------------------------------------------------------------
#  Result builder
# ---------------------------------------------------------------------------

def build_violation_result(
    description: str, violation_type: str, docs: List[Dict]
) -> Dict:
    if not docs:
        return {
            "is_violation": False,
            "violation_type": violation_type,
            "conclusion": "未在当前制度文件中找到明确依据。",
            "basis": "当前上传的制度文件中暂无足够内容支持对该行为作出明确判断。",
            "sources": [],
            "context": "",
        }

    llm_conclusion = _generate_conclusion_with_llm(description, violation_type, docs)

    if llm_conclusion:
        # 用 LLM 生成的回答作为主结论
        first_source = docs[0].get("text", "")
        return {
            "is_violation": violation_type != "未知",
            "violation_type": violation_type,
            "conclusion": llm_conclusion,
            "basis": first_source,
            "sources": docs,
            "context": _build_violation_context(docs),
        }

    # LLM 不可用时退回到模板
    basis = docs[0].get("text", "")
    template_conclusion = VIOLATION_TEMPLATES.get(
        violation_type, VIOLATION_TEMPLATES["未知"]
    )
    return {
        "is_violation": violation_type != "未知",
        "violation_type": violation_type,
        "conclusion": template_conclusion,
        "basis": basis,
        "sources": docs,
        "context": _build_violation_context(docs),
    }


def judge_violation(description: str, top_k: int = 3) -> Dict:
    violation_type = detect_violation_type(description)
    docs = retrieve_violation_rules(description, top_k=top_k, violation_type=violation_type)
    return build_violation_result(description, violation_type, docs)
