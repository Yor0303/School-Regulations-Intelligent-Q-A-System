# -*- encoding: utf-8 -*-
import importlib
import re
from typing import Dict, List, Optional

from knowledge_base import KnowledgeBaseService
from knowledge_base.memory import ConversationMemory
from rapid_rag.utils import read_yaml


CONFIG_PATH = "rapid_rag/config.yaml"


def get_kb_service() -> KnowledgeBaseService:
    return KnowledgeBaseService(CONFIG_PATH)


def get_llm():
    config = read_yaml(CONFIG_PATH)
    llm_module = importlib.import_module("rapid_rag.llm")
    llm_params: Dict[str, Dict] = config.get("LLM_API", {})

    if "Ollama" in llm_params:
        return getattr(llm_module, "Ollama")(**llm_params["Ollama"])

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
    scored = []
    for index, doc in enumerate(docs):
        text = doc.get("text", "")
        source = doc.get("source_label", "")
        score = 0
        for keyword in keywords:
            if keyword in text:
                score += 3
            if keyword in source:
                score += 1
        if any(term in query for term in ["怎么办", "如何", "怎么"]):
            if any(term in text for term in ["补考", "重修", "未通过", "成绩", "处理"]):
                score += 3
        scored.append((score, -index, doc))

    scored.sort(reverse=True)
    selected = [item[2] for item in scored if item[0] > 0]
    if not selected:
        return docs[:max_docs]
    return selected[:max_docs]


def extract_query_keywords(query: str) -> List[str]:
    parts = re.split(r"[，。！？、\s]+", query)
    keywords = []
    stop_words = {"怎么办", "如何", "怎么", "是否", "可以", "需要", "如果", "什么", "那"}
    for part in parts:
        token = part.strip()
        if len(token) < 2 or token in stop_words:
            continue
        keywords.append(token)

    domain_terms = ["绩点", "补考", "重修", "成绩", "学分", "挂科", "不及格", "未通过"]
    for term in domain_terms:
        if term in query and term not in keywords:
            keywords.append(term)
    return keywords


def build_qa_prompt(query: str, context: str, history_text: str = "") -> str:
    history_block = history_text.strip() or "No prior conversation."
    return (
        "You are a university policy consultation assistant.\n"
        "Answer strictly based on the uploaded school policy documents.\n"
        'If the documents do not clearly support an answer, reply with "No clear supporting rule was found in the uploaded documents."\n\n'
        "Only use the most relevant rules. Ignore weakly related excerpts.\n"
        "Do not turn a rule about high GPA benefits into advice for low GPA recovery.\n"
        "If the documents mention score handling or makeup exams but do not mention GPA recovery directly, say that clearly.\n"
        "Use a calm, formal consultation tone.\n"
        "Do not mention source numbers such as [Source 1] or [Source 2] in the answer.\n"
        "Do not invent policies, procedures, or conclusions that are not supported by the documents.\n\n"
        f"Conversation history:\n{history_block}\n\n"
        f"Current user question:\n{query}\n\n"
        f"Reference documents:\n{context}\n\n"
        "Answer format:\n"
        "1. Conclusion: give a concise direct answer.\n"
        "2. Basis: explain the relevant rules in plain language.\n"
        "3. If the documents are not sufficient, explicitly state that the current documents only mention related handling rules.\n"
    )


def generate_answer(prompt: str) -> str:
    llm = get_llm()
    response = llm(prompt, history=None)
    if not response:
        return (
            "Relevant policy excerpts were found, but a final answer could not be generated."
        )
    return response


def format_sources(docs: List[Dict]) -> str:
    if not docs:
        return "Sources: none"

    lines = ["Sources:"]
    for index, doc in enumerate(docs, start=1):
        source_label = doc.get("source_label", doc.get("file_name", "unknown"))
        lines.append(f"{index}. {source_label}")
    return "\n".join(lines)


def format_final_answer(answer: str, docs: List[Dict]) -> str:
    clean_answer = answer.strip()
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
    prompt = build_qa_prompt(query, context, history_text)
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
