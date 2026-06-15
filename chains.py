# -*- encoding: utf-8 -*-
import importlib
import re
from typing import Dict, List, Optional

from knowledge_base import KnowledgeBaseService
from knowledge_base.memory import ConversationMemory
from rapid_rag.utils import read_yaml
from graph_engine import get_graph_context_for_query
from ollama_env import filter_ollama_client_kwargs


CONFIG_PATH = "rapid_rag/config.yaml"


def get_kb_service() -> KnowledgeBaseService:
    return KnowledgeBaseService(CONFIG_PATH)


def get_llm():
    config = read_yaml(CONFIG_PATH)
    llm_module = importlib.import_module("rapid_rag.llm")
    llm_params: Dict[str, Dict] = config.get("LLM_API", {})

    if "Ollama" in llm_params:
        return getattr(llm_module, "Ollama")(
            **filter_ollama_client_kwargs(llm_params["Ollama"])
        )

    llm_name, params = next(iter(llm_params.items()))
    return getattr(llm_module, llm_name)(**params)


def build_context(docs: List[Dict]) -> str:
    if not docs:
        return ""

    parts = []
    for index, doc in enumerate(docs, start=1):
        source = doc.get("source_label", doc.get("file_name", "unknown"))
        text = doc.get("text", "")
        parts.append(f"[Source {index}] {source}\nContent: {text}")
    return "\n\n".join(parts)


def filter_relevant_docs(query: str, docs: List[Dict], max_docs: int = 2) -> List[Dict]:
    keywords = extract_query_keywords(query)
    if not keywords:
        return docs[:max_docs]

    scored = []
    for index, doc in enumerate(docs):
        text = doc.get("text", "")
        file_name = doc.get("file_name", "")
        section_title = doc.get("section_title", "") or ""

        score = 0.0

        # 关键词密度
        for kw in keywords:
            count = text.count(kw)
            if count > 0:
                score += 1.0 + min(count - 1, 3) * 0.3

        # 标题命中
        if section_title:
            for kw in keywords:
                if kw in section_title:
                    score += 2.0

        # 文件名命中
        for kw in keywords:
            if kw in file_name:
                score += 3.0

        # 操作类查询加分
        if any(w in query for w in ["怎么", "如何", "怎样", "下载", "打印", "操作"]):
            howto_terms = ["步骤", "操作", "方法", "流程", "系统", "平台", "登录", "点击", "选择", "下载", "打印", "pdf"]
            for t in howto_terms:
                if t in text:
                    score += 0.5

        # 违纪类查询加分
        if any(w in query for w in ["处分", "违纪", "违规", "作弊", "处罚", "后果"]):
            consequence_terms = ["处分", "处理", "无效", "零分", "取消", "不得", "禁止", "警告", "记过"]
            for t in consequence_terms:
                if t in text:
                    score += 0.5

        scored.append((score, -index, doc))

    scored.sort(reverse=True)
    selected = [item[2] for item in scored if item[0] > 0]
    if not selected:
        return docs[:max_docs]
    return selected[:max_docs]


def extract_query_keywords(query: str) -> List[str]:
    query = query.strip()
    if not query:
        return []

    try:
        import jieba
        words = jieba.lcut(query)
    except ModuleNotFoundError:
        words = re.split(r"[，。！？、\s]+", query)

    stop_words = {
        "怎么办", "如何", "怎么", "是否", "可以", "需要", "如果", "什么",
        "那", "吗", "呢", "吧", "的", "了", "是", "在", "和", "有",
        "我", "要", "想", "请问", "一下", "这个", "那个",
    }

    keywords = [w for w in words if len(w) >= 2 and w not in stop_words]

    expansions = {
        "成绩": ["成绩单", "成绩证明", "绩点", "平均绩点"],
        "打印": ["下载", "导出"],
        "下载": ["打印", "导出"],
        "考试": ["考核", "期末", "补考", "缓考"],
        "违纪": ["作弊", "处分", "违规"],
        "作弊": ["违纪", "违规", "处分"],
        "宿舍": ["住宿", "寝室", "公寓"],
        "奖学金": ["评奖", "评优", "奖励"],
        "学分": ["课程", "修读", "选修"],
        "转专业": ["专业", "转入", "转出"],
        "实习": ["实践", "实训"],
        "缓考": ["延期", "考试", "申请"],
        "补考": ["重修", "未通过", "不及格"],
        "重修": ["补考", "不及格", "未通过"],
        "处分": ["警告", "记过", "留校察看", "开除"],
    }

    expanded = list(keywords)
    for kw in keywords:
        if kw in expansions:
            expanded.extend(expansions[kw])

    seen = set()
    result = []
    for kw in expanded:
        if kw not in seen:
            seen.add(kw)
            result.append(kw)
    return result


def build_qa_prompt(query: str, context: str, history_text: str = "", graph_context: str = "") -> str:
    history_block = history_text.strip() or "No prior conversation."

    graph_block = ""
    if graph_context:
        graph_block = (
            "\n\nStructured rule-graph relationships (for reference):\n"
            f"{graph_context}\n"
        )

    return (
        "You are a university policy consultation assistant.\n"
        "IMPORTANT: All responses MUST be written in Simplified Chinese.\n"
        "Do not use English headings such as Conclusion, Basis, Sources.\n"
        "Use Chinese headings instead.\n"
        "Answer strictly based on the uploaded school policy documents.\n"
        'If the documents do not clearly support an answer, reply with "No clear supporting rule was found in the uploaded documents."\n\n'
        "Only use the most relevant rules. Ignore weakly related excerpts.\n"
        "Do not turn a rule about high GPA benefits into advice for low GPA recovery.\n"
        "If the documents mention score handling or makeup exams but do not mention GPA recovery directly, say that clearly.\n"
        "When the structured rule-graph relationships are provided, use them to understand the logical connections between rules, but always ground your final answer in the reference documents.\n"
        "Use a calm, formal consultation tone.\n"
        "Do not mention source numbers such as [Source 1] or [Source 2] in the answer.\n"
        "Do not invent policies, procedures, or conclusions that are not supported by the documents.\n\n"
        f"Conversation history:\n{history_block}\n"
        f"{graph_block}\n"
        f"Current user question:\n{query}\n\n"
        f"Reference documents:\n{context}\n\n"
        "Answer format:\n"
        "1. 结论：给出简洁、直接的回答。\n"
        "2. 依据：用通俗语言解释相关规定。\n"
        "3. 补充说明：如果文档信息不足，请说明当前文档只提供了哪些相关规则。\n"
    )


def generate_answer(prompt: str) -> str:
    llm = get_llm()
    try:
        response = llm(prompt, history=None)
    except RuntimeError as exc:
        return str(exc)
    if not response:
        return (
            "Relevant policy excerpts were found, but a final answer could not be generated."
        )
    return response


def normalize_answer_headings(answer: str) -> str:
    replacements = {
        "Conclusion:": "结论：",
        "Conclusion：": "结论：",
        "Basis:": "依据：",
        "Basis：": "依据：",
        "Sources:": "来源：",
        "Sources：": "来源：",
        "Source:": "来源：",
        "Source：": "来源：",
        "If the documents are not sufficient": "补充说明",
        "No clear supporting rule was found in the uploaded documents.": "未在已上传文档中找到明确依据。",
    }
    normalized = answer
    for old, new in replacements.items():
        normalized = normalized.replace(old, new)
    return normalized


def unique_source_labels(docs: List[Dict]) -> List[str]:
    labels = []
    for doc in docs:
        source_label = doc.get("source_label", doc.get("file_name", "unknown"))
        if source_label not in labels:
            labels.append(source_label)
    return labels


def format_sources(docs: List[Dict]) -> str:
    source_labels = unique_source_labels(docs)
    if not source_labels:
        return "来源：无"

    lines = ["来源："]
    for index, source_label in enumerate(source_labels, start=1):
        lines.append(f"{index}. {source_label}")
    return "\n".join(lines)


def format_final_answer(answer: str, docs: List[Dict]) -> str:
    clean_answer = normalize_answer_headings(answer.strip())
    source_block = format_sources(docs)
    if clean_answer.endswith(source_block):
        return clean_answer
    return f"{clean_answer}\n\n{source_block}"


def answer_question(
    query: str,
    memory: Optional[ConversationMemory] = None,
    top_k: int = 3,
) -> Dict:
    kb_service = get_kb_service()
    docs = kb_service.query_documents(query, top_k=top_k)
    if not docs:
        answer = "No clear supporting rule was found in the uploaded documents."
        if memory is not None:
            memory.add_user_message(query)
            memory.add_assistant_message(answer)
        return {"answer": answer, "sources": [], "context": ""}

    history_text = memory.format_history() if memory is not None else ""
    filtered_docs = filter_relevant_docs(query, docs, max_docs=min(top_k, 2))
    context = build_context(filtered_docs)

    graph_context = ""
    try:
        graph_context = get_graph_context_for_query(query, max_items=3)
    except Exception:
        pass

    prompt = build_qa_prompt(query, context, history_text, graph_context)
    answer = generate_answer(prompt)
    final_answer = format_final_answer(answer, filtered_docs)

    if memory is not None:
        memory.add_user_message(query)
        memory.add_assistant_message(final_answer)

    return {
        "answer": final_answer,
        "sources": filtered_docs,
        "context": context,
    }
