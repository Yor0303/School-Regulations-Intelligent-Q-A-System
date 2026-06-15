# -*- encoding: utf-8 -*-
import importlib
import json
import re
from pathlib import Path
from typing import Dict, List, Optional

import networkx as nx

try:
    from pyvis.network import Network as _PyVisNetwork
    _HAS_PYVIS = True
except ModuleNotFoundError:
    _HAS_PYVIS = False

GRAPH_DATA_PATH = Path("data/rule_graph/rule_graph.json")
DEFAULT_HTML_PATH = Path("rule_graph.html")
RECORD_PATH = Path("vector_db_data/handbook_chunks.json")


def load_graph_seed_data() -> List[Dict]:
    return [
        {
            "source": "学生",
            "relation": "可申请",
            "target": "缓考",
            "category": "考试管理",
            "evidence": "因病住院、急诊留院观察、直系亲属遭遇不可抗力事件或代表学校参加重大活动等情况，可以按规定申请缓考。",
            "source_label": "2025年本科生学生手册.pdf, page 84",
            "source_type": "role",
            "target_type": "action",
        },
        {
            "source": "缓考",
            "relation": "需要",
            "target": "证明材料",
            "category": "考试管理",
            "evidence": "申请缓考时应按要求提交相关证明材料，并在考试前提出申请。",
            "source_label": "2025年本科生学生手册.pdf, page 84",
            "source_type": "action",
            "target_type": "material",
        },
        {
            "source": "缓考申请",
            "relation": "由",
            "target": "教务部审核",
            "category": "考试管理",
            "evidence": "缓考申请需经教务部门审核同意，学生按规定时间参加缓考考试。",
            "source_label": "2025年本科生学生手册.pdf, page 84",
            "source_type": "action",
            "target_type": "rule",
        },
        {
            "source": "课程未通过",
            "relation": "可参加",
            "target": "补考",
            "category": "学习管理",
            "evidence": "课程成绩未通过时，应查询课程是否安排补考，并按学校规定参加补考或重新修读。",
            "source_label": "2025年本科生学生手册.pdf, page 83",
            "source_type": "result",
            "target_type": "action",
        },
        {
            "source": "课程未通过",
            "relation": "可选择",
            "target": "重新修读",
            "category": "学习管理",
            "evidence": "课程未通过或绩点不足时，可通过补考、重修等方式改善课程成绩。",
            "source_label": "2025年本科生学生手册.pdf, page 83",
            "source_type": "result",
            "target_type": "action",
        },
        {
            "source": "成绩",
            "relation": "影响",
            "target": "绩点",
            "category": "学习管理",
            "evidence": "课程成绩与绩点、平均绩点统计相关，重新修读课程的成绩会纳入平均绩点计算。",
            "source_label": "2025年本科生学生手册.pdf, page 83",
            "source_type": "rule",
            "target_type": "rule",
        },
        {
            "source": "绩点",
            "relation": "组成",
            "target": "平均绩点",
            "category": "学习管理",
            "evidence": "平均绩点反映课程成绩的综合情况，相关课程成绩会参与统计。",
            "source_label": "2025年本科生学生手册.pdf, page 83",
            "source_type": "rule",
            "target_type": "rule",
        },
        {
            "source": "学生",
            "relation": "可能发生",
            "target": "旷课",
            "category": "课堂考勤",
            "evidence": "学生应遵守课堂考勤要求，旷课等行为会影响课程学习和考核。",
            "source_label": "2025年本科生学生手册.pdf",
            "source_type": "role",
            "target_type": "action",
        },
        {
            "source": "旷课",
            "relation": "可能导致",
            "target": "不得参加期末考核",
            "category": "课堂考勤",
            "evidence": "课堂考勤违规达到规定情形时，可能影响课程考核资格。",
            "source_label": "2025年本科生学生手册.pdf",
            "source_type": "action",
            "target_type": "result",
        },
        {
            "source": "学生",
            "relation": "可能发生",
            "target": "缺考",
            "category": "考试管理",
            "evidence": "学生应按规定参加考试，未按规定参加考试可能被视为缺考。",
            "source_label": "2025年本科生学生手册.pdf",
            "source_type": "role",
            "target_type": "action",
        },
        {
            "source": "缺考",
            "relation": "记为",
            "target": "零分",
            "category": "考试管理",
            "evidence": "缺考课程成绩通常按学校考试管理规定处理。",
            "source_label": "2025年本科生学生手册.pdf",
            "source_type": "action",
            "target_type": "result",
        },
        {
            "source": "学生",
            "relation": "可能发生",
            "target": "考试违纪",
            "category": "违纪处分",
            "evidence": "考试过程中使用手机、查阅答案、替考等行为属于考试违纪或作弊相关情形。",
            "source_label": "2025年本科生学生手册.pdf",
            "source_type": "role",
            "target_type": "action",
        },
        {
            "source": "考试违纪",
            "relation": "可能导致",
            "target": "成绩无效",
            "category": "违纪处分",
            "evidence": "考试违纪或作弊行为可能导致考试成绩无效，并依据情节给予纪律处分。",
            "source_label": "2025年本科生学生手册.pdf",
            "source_type": "action",
            "target_type": "result",
        },
        {
            "source": "考试违纪",
            "relation": "可能给予",
            "target": "纪律处分",
            "category": "违纪处分",
            "evidence": "学生违反考试纪律的，学校可根据情节轻重给予相应纪律处分。",
            "source_label": "2025年本科生学生手册.pdf",
            "source_type": "action",
            "target_type": "result",
        },
        {
            "source": "宿舍违规用电",
            "relation": "可能给予",
            "target": "纪律处分",
            "category": "宿舍管理",
            "evidence": "学生社区住宿管理要求学生遵守用电安全规定，违规用电可能受到相应处理。",
            "source_label": "2025年本科生学生手册.pdf",
            "source_type": "action",
            "target_type": "result",
        },
    ]


# ---------------------------------------------------------------------------
#  LLM helpers
# ---------------------------------------------------------------------------

def _get_llm():
    from rapid_rag.utils import read_yaml
    from ollama_env import filter_ollama_client_kwargs

    config = read_yaml("rapid_rag/config.yaml")
    llm_module = importlib.import_module("rapid_rag.llm")
    llm_params: Dict[str, Dict] = config.get("LLM_API", {})

    if "Ollama" in llm_params:
        return getattr(llm_module, "Ollama")(
            **filter_ollama_client_kwargs(llm_params["Ollama"])
        )

    llm_name, params = next(iter(llm_params.items()))
    return getattr(llm_module, llm_name)(**params)


def _parse_json_from_llm(text: str) -> Optional[List[Dict]]:
    """Try to extract a JSON array from LLM output (may be fenced)."""
    if not text:
        return None
    text = text.strip()
    # Try ```json ... ``` first
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if m:
        text = m.group(1).strip()
    # Try to find the outermost [ ... ]
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1 and end > start:
        text = text[start : end + 1]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _chunk_text(text: str, chunk_size: int = 2000, overlap: int = 200) -> List[str]:
    """Split long text into overlapping chunks of ~chunk_size characters."""
    if len(text) <= chunk_size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks


# ---------------------------------------------------------------------------
#  LLM-powered triple extraction
# ---------------------------------------------------------------------------

EXTRACTION_PROMPT = """你是一个学校规章制度知识图谱构建助手。请仔细阅读以下学校制度文本，提取其中包含的**实体关系三元组**。

每条三元组表示一个明确的规则事实，格式如下：
- source: 主体/前提（如"学生"、"考试违纪"、"旷课"、"课程未通过"）
- relation: 关系谓语（如"可申请"、"可能导致"、"需要"、"记为"、"影响"）
- target: 客体/后果（如"缓考"、"成绩无效"、"纪律处分"、"补考"）
- category: 所属类别（从以下选择：考试管理、学习管理、课堂考勤、违纪处分、宿舍管理、奖助学金、学籍管理、实习管理、其他）
- evidence: 原文依据（直接从文本中摘录原句）
- source_type: 主体类型（role/action/rule/result/material/scene）
- target_type: 客体类型（role/action/rule/result/material/scene）

重要要求：
1. 只提取文本中明确陈述的规则关系，绝不编造
2. 每条三元组必须能从原文中找到支撑
3. 宁可少提取，不要编造不存在的关系
4. 优先提取处罚、条件、流程、权利义务相关的关系
5. evidence 字段必须摘录文本原句

制度文本：
{text}

请严格以 JSON 数组格式返回，每个元素包含 source, relation, target, category, evidence, source_type, target_type 字段。
不要输出任何 JSON 之外的解释文字。"""


def extract_triples_with_llm(
    text: str,
    source_label: str = "",
    max_chunks: int = 8,
    progress_callback=None,
) -> List[Dict]:
    """Feed document text to LLM and extract knowledge-graph triples.

    Args:
        text: Raw document text.
        source_label: Human-readable source label (e.g. filename + page).
        max_chunks: Maximum number of text chunks to process.
        progress_callback: Optional callable(step, total) for progress reporting.

    Returns:
        List of triple dicts with source/relation/target/category/evidence/…
    """
    llm = _get_llm()
    chunks = _chunk_text(text, chunk_size=2000, overlap=200)
    chunks = chunks[:max_chunks]

    all_triples: List[Dict] = []
    for idx, chunk in enumerate(chunks):
        if progress_callback:
            progress_callback(idx, len(chunks))
        prompt = EXTRACTION_PROMPT.format(text=chunk)
        try:
            raw = llm(prompt)
            parsed = _parse_json_from_llm(raw)
            if parsed:
                for item in parsed:
                    if isinstance(item, dict) and item.get("source") and item.get("target"):
                        item.setdefault("source_label", source_label)
                        item.setdefault("category", "其他")
                        item.setdefault("source_type", "rule")
                        item.setdefault("target_type", "rule")
                        all_triples.append(item)
        except Exception:
            continue

    if progress_callback:
        progress_callback(len(chunks), len(chunks))
    return all_triples


def auto_build_graph_from_docs(
    record_path: Optional[Path] = None,
    max_chunks_per_file: int = 6,
    progress_callback=None,
) -> List[Dict]:
    """Read all document chunks from the record JSON, extract triples via LLM,
    merge with existing graph data, and persist.

    Returns the merged triple list.
    """
    record_path = Path(record_path) if record_path else RECORD_PATH
    if not record_path.exists():
        raise FileNotFoundError(f"Record file not found: {record_path}")

    all_records = json.loads(record_path.read_text(encoding="utf-8"))

    # Group by file_name
    file_groups: Dict[str, List[Dict]] = {}
    for rec in all_records:
        fname = rec.get("file_name", "unknown")
        file_groups.setdefault(fname, []).append(rec)

    existing = load_graph_data()
    existing_keys = {
        (item.get("source"), item.get("relation"), item.get("target"))
        for item in existing
    }

    new_triples: List[Dict] = []
    file_names = list(file_groups.keys())
    for file_idx, (fname, recs) in enumerate(file_groups.items()):
        # Merge chunks into page-ordered full text
        recs_sorted = sorted(
            recs,
            key=lambda r: (r.get("page_no") or 0, r.get("paragraph_no") or 0),
        )
        full_text = "\n\n".join(
            r.get("text", "") for r in recs_sorted if r.get("text")
        )
        if not full_text.strip():
            continue

        source_label = fname

        def file_progress(step, total):
            if progress_callback:
                progress_callback(file_idx, len(file_names), fname, step, total)

        triples = extract_triples_with_llm(
            full_text,
            source_label=source_label,
            max_chunks=max_chunks_per_file,
            progress_callback=file_progress,
        )

        for triple in triples:
            key = (
                triple.get("source"),
                triple.get("relation"),
                triple.get("target"),
            )
            if key not in existing_keys:
                existing_keys.add(key)
                new_triples.append(triple)

    if new_triples:
        merged = existing + new_triples
        save_graph_data(merged)
        return merged
    return existing


# ---------------------------------------------------------------------------
#  LLM-powered semantic graph search
# ---------------------------------------------------------------------------

SEARCH_PROMPT = """你是一个学校规章制度知识图谱查询助手。以下是知识图谱中存储的规则三元组，每行格式为：
[主体] --关系--> [客体] | 类别：xxx | 依据：xxx

{triples}

用户问题：{query}

请找出与用户问题最相关的规则链（1-5条），对于每条规则链：
1. 说明主体、关系、客体
2. 解释为什么这条规则与用户问题相关
3. 如果多条规则可以串联成因果链（A→B→C），请描述完整推理路径

以 JSON 数组格式返回：
[{{"source": "...", "relation": "...", "target": "...", "relevance": "相关原因", "chain": "因果链说明（如有）"}}]

只返回 JSON，不要其他文字。"""


def search_graph_with_llm(
    query: str,
    records: Optional[List[Dict]] = None,
) -> List[Dict]:
    """Semantically search the knowledge graph using LLM reasoning.

    Pre-filters with keyword matching to stay within context limits,
    then lets the LLM identify relevant chains and multi-hop paths.
    """
    if not query or not query.strip():
        return []

    records = records if records is not None else load_graph_data()
    if not records:
        return []

    # Pre-filter: if graph is large, reduce to keyword-relevant subset
    if len(records) > 30:
        records = filter_graph_records(query, records)

    triples_text = "\n".join(
        f"[{item.get('source', '')}] --{item.get('relation', '')}--> [{item.get('target', '')}] "
        f"| 类别：{item.get('category', '')} | 依据：{item.get('evidence', '')[:80]}"
        for item in records
    )

    llm = _get_llm()
    prompt = SEARCH_PROMPT.format(triples=triples_text, query=query)
    try:
        raw = llm(prompt)
        parsed = _parse_json_from_llm(raw)
        if parsed and isinstance(parsed, list):
            return [item for item in parsed if isinstance(item, dict)]
    except Exception:
        pass
    return []


def get_graph_context_for_query(
    query: str,
    max_items: int = 5,
) -> str:
    """Build a concise graph-context string for injection into the Q&A prompt."""
    related = search_graph_with_llm(query)
    if not related:
        return ""

    lines = ["[知识图谱规则链]"]
    for idx, item in enumerate(related[:max_items], start=1):
        chain = item.get("chain", "")
        source = item.get("source", "")
        relation = item.get("relation", "")
        target = item.get("target", "")
        relevance = item.get("relevance", "")

        line = f"{idx}. {source} → {target}（{relation}）"
        if chain:
            line += f"  因果链：{chain}"
        if relevance:
            line += f"  关联说明：{relevance}"
        lines.append(line)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
#  Persistence
# ---------------------------------------------------------------------------

def ensure_graph_data(path: Path = GRAPH_DATA_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(
            json.dumps(load_graph_seed_data(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return path


def load_graph_data(path: Path = GRAPH_DATA_PATH) -> List[Dict]:
    ensure_graph_data(path)
    return json.loads(path.read_text(encoding="utf-8"))


def save_graph_data(records: List[Dict], path: Path = GRAPH_DATA_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return path


def refresh_graph_data(path: Path = GRAPH_DATA_PATH) -> Path:
    return save_graph_data(load_graph_seed_data(), path)


# ---------------------------------------------------------------------------
#  Graph construction
# ---------------------------------------------------------------------------

def extract_graph_elements(records: List[Dict] | None = None) -> Dict:
    records = records if records is not None else load_graph_data()
    node_map = {}
    edges = []
    for item in records:
        source = item["source"]
        target = item["target"]
        node_map[source] = {
            "id": source,
            "label": source,
            "type": item.get("source_type", "rule"),
            "category": item.get("category", ""),
        }
        node_map[target] = {
            "id": target,
            "label": target,
            "type": item.get("target_type", "rule"),
            "category": item.get("category", ""),
        }
        edges.append(
            {
                "source": source,
                "target": target,
                "label": item.get("relation", ""),
                "category": item.get("category", ""),
                "evidence": item.get("evidence", ""),
                "source_label": item.get("source_label", ""),
            }
        )
    return {"nodes": list(node_map.values()), "edges": edges}


def build_rule_graph(graph_data: Dict):
    graph = nx.DiGraph()
    for node in graph_data["nodes"]:
        graph.add_node(
            node["id"],
            label=node["label"],
            node_type=node.get("type", "rule"),
            category=node.get("category", ""),
        )
    for edge in graph_data["edges"]:
        graph.add_edge(
            edge["source"],
            edge["target"],
            label=edge.get("label", ""),
            category=edge.get("category", ""),
            evidence=edge.get("evidence", ""),
            source_label=edge.get("source_label", ""),
        )
    return graph


# ---------------------------------------------------------------------------
#  Keyword-based search & scoring (kept as pre-filter / fallback)
# ---------------------------------------------------------------------------

def filter_graph_records(
    keyword: str = "", records: List[Dict] | None = None
) -> List[Dict]:
    records = records if records is not None else load_graph_data()
    query_terms = _extract_query_terms(keyword)
    if not query_terms:
        return records

    scored_records = []
    for item in records:
        score = _score_graph_record(item, query_terms)
        if score > 0:
            scored_records.append((score, item))

    scored_records.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in scored_records]


# ---------------------------------------------------------------------------
#  Stats & validation
# ---------------------------------------------------------------------------

def get_graph_stats(records: List[Dict] | None = None) -> Dict:
    records = records if records is not None else load_graph_data()
    graph_data = extract_graph_elements(records)
    return {
        "nodes": len(graph_data["nodes"]),
        "edges": len(graph_data["edges"]),
        "categories": len(
            {item.get("category", "") for item in records if item.get("category")}
        ),
        "missing_evidence": sum(
            1 for item in records if not item.get("evidence")
        ),
        "missing_source": sum(
            1 for item in records if not item.get("source_label")
        ),
    }


def find_graph_issues(records: List[Dict] | None = None) -> List[str]:
    records = records if records is not None else load_graph_data()
    issues = []
    seen = set()
    for index, item in enumerate(records, start=1):
        key = (item.get("source"), item.get("relation"), item.get("target"))
        if key in seen:
            issues.append(
                f"第 {index} 条关系重复：{item.get('source')} -> {item.get('target')}"
            )
        seen.add(key)
        if not item.get("evidence"):
            issues.append(f"第 {index} 条关系缺少依据说明。")
        if not item.get("source_label"):
            issues.append(f"第 {index} 条关系缺少来源。")
    return issues


def get_related_rule_chains(query: str, max_items: int = 4) -> List[Dict]:
    records = filter_graph_records(query)
    return records[:max_items]


def format_rule_chain(item: Dict) -> str:
    return (
        f"{item.get('source', '')} → {item.get('target', '')}"
        f"：{item.get('relation', '')}"
    )


# ---------------------------------------------------------------------------
#  Visualization
# ---------------------------------------------------------------------------

COLOR_MAP = {
    "role": "#7CA3C8",
    "action": "#D4918E",
    "rule": "#8AAA9A",
    "result": "#C9B884",
    "scene": "#A99BB4",
    "material": "#8AABAD",
}


def _build_pyvis_html(graph, height: str = "600px") -> str:
    """Build PyVis HTML and return it as a string (instead of writing to file)."""
    if not _HAS_PYVIS:
        raise ModuleNotFoundError("pyvis not installed")

    net = _PyVisNetwork(height=height, width="100%", directed=True)

    for node_id, attrs in graph.nodes(data=True):
        node_type = attrs.get("node_type", "rule")
        title = f"类型：{node_type}<br>类别：{attrs.get('category', '')}"
        net.add_node(
            node_id,
            label=attrs.get("label", node_id),
            title=title,
            color=COLOR_MAP.get(node_type, "#4b5563"),
        )

    for source, target, attrs in graph.edges(data=True):
        title = "<br>".join(
            part
            for part in [
                attrs.get("label", ""),
                attrs.get("evidence", ""),
                attrs.get("source_label", ""),
            ]
            if part
        )
        net.add_edge(source, target, label=attrs.get("label", ""), title=title)

    return net.generate_html()


def _build_fallback_html(graph, error: str = "") -> str:
    """Minimal HTML fallback when PyVis is not installed."""
    err_html = ""
    if error:
        err_html = (
            '<div style="background:#FFF3CD;border:1px solid #FFC107;'
            'padding:12px;margin-bottom:16px;border-radius:8px;">'
            '<strong>PyVis error:</strong> ' + error + '</div>'
        )
    node_items = []
    edge_items = []
    for node_id, attrs in graph.nodes(data=True):
        node_items.append(
            "<li><strong>" + str(attrs.get('label', node_id)) + "</strong>"
            " (" + str(attrs.get('node_type', 'rule')) + ")</li>"
        )
    for source, target, attrs in graph.edges(data=True):
        evidence = attrs.get("evidence", "")
        source_label = attrs.get("source_label", "")
        detail = ""
        if evidence or source_label:
            detail = "<br><small>" + str(evidence) + " " + str(source_label) + "</small>"
        edge_items.append(
            "<li>" + str(source) + " -> " + str(target)
            + " : " + str(attrs.get('label', '')) + detail + "</li>"
        )

    html = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>School Policy Rule Graph</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 24px; }
    h1 { margin-bottom: 8px; }
    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
    ul { line-height: 1.7; }
    small { color: #555; }
  </style>
</head>
<body>
  <h1>校规知识图谱</h1>
"""
    if err_html:
        html += err_html
    html += """  <div class="grid">
    <section><h2>节点</h2><ul>"""
    html += "".join(node_items)
    html += """</ul></section>
    <section><h2>关系</h2><ul>"""
    html += "".join(edge_items)
    html += """</ul></section>
  </div>
</body>
</html>"""
    return html


def render_graph_html_content(graph, height: str = "600px") -> str:
    """Return standalone HTML string of the interactive graph for embedding."""
    try:
        return _build_pyvis_html(graph, height=height)
    except ModuleNotFoundError:
        return _build_fallback_html(graph)
    except Exception as exc:
        return _build_fallback_html(graph, error=str(exc))


def render_graph_html(
    graph, output_path: str | Path = DEFAULT_HTML_PATH
) -> str:
    """Render graph to an HTML file. Returns the output path."""
    output_path = str(output_path)
    html = render_graph_html_content(graph)
    Path(output_path).write_text(html, encoding="utf-8")
    return output_path


def export_graph_html(
    output_path: str | Path = DEFAULT_HTML_PATH, keyword: str = ""
) -> str:
    records = filter_graph_records(keyword)
    graph_data = extract_graph_elements(records)
    graph = build_rule_graph(graph_data)
    return render_graph_html(graph, output_path)


def export_graph_json(output_path: str | Path = "rule_graph.json") -> str:
    records = load_graph_data()
    Path(output_path).write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return str(output_path)


# ---------------------------------------------------------------------------
#  Keyword helpers (internal)
# ---------------------------------------------------------------------------

def _extract_query_terms(text: str) -> List[str]:
    text = (text or "").strip()
    if not text:
        return []

    domain_terms = [
        "缓考", "补考", "重修", "绩点", "成绩", "考试",
        "违纪", "作弊", "缺考", "旷课", "宿舍", "用电",
        "处分", "证明", "审核",
    ]
    terms = [term for term in domain_terms if term in text]
    terms.extend(
        token for token in re.split(r"[，。！？、\s]+", text) if len(token) >= 2
    )

    deduped = []
    for term in terms:
        if term not in deduped:
            deduped.append(term)
    return deduped


def _score_graph_record(item: Dict, query_terms: List[str]) -> int:
    source = item.get("source", "")
    relation = item.get("relation", "")
    target = item.get("target", "")
    category = item.get("category", "")
    evidence = item.get("evidence", "")
    source_label = item.get("source_label", "")
    title_text = f"{source} {relation} {target} {category}"
    full_text = f"{title_text} {evidence} {source_label}"

    strong_terms = {
        "作弊", "违纪", "处分", "宿舍", "用电", "绩点",
        "补考", "重修", "缓考", "缺考", "旷课",
    }
    weak_terms = {"考试", "学生", "处理", "怎么办", "怎么"}
    has_strong_query = any(term in strong_terms for term in query_terms)

    score = 0
    for term in query_terms:
        if has_strong_query and term in weak_terms:
            continue
        if term in title_text:
            score += 6 if term in strong_terms else 2
        elif term in full_text:
            score += 3 if term in strong_terms else 1

    if (
        "作弊" in query_terms
        and category == "违纪处分"
        and (
            "考试违纪" in title_text
            or "成绩无效" in title_text
            or "纪律处分" in title_text
        )
    ):
        score += 12
    if "违规" in query_terms and (
        "宿舍违规用电" in title_text or "纪律处分" in title_text
    ):
        score += 8
    if "缓考" in query_terms and "缓考" in title_text:
        score += 10
    if (
        "绩点" in query_terms
        and category == "学习管理"
        and ("绩点" in title_text or "成绩" in title_text)
    ):
        score += 10

    if all(term in weak_terms for term in query_terms):
        return 0
    return score
