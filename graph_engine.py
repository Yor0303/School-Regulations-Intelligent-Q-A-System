# -*- encoding: utf-8 -*-
import json
import re
from pathlib import Path
from typing import Dict, List

import networkx as nx


GRAPH_DATA_PATH = Path("data/rule_graph/rule_graph.json")
DEFAULT_HTML_PATH = Path("rule_graph.html")


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
    path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def refresh_graph_data(path: Path = GRAPH_DATA_PATH) -> Path:
    return save_graph_data(load_graph_seed_data(), path)


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


def filter_graph_records(keyword: str = "", records: List[Dict] | None = None) -> List[Dict]:
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


def get_graph_stats(records: List[Dict] | None = None) -> Dict:
    records = records if records is not None else load_graph_data()
    graph_data = extract_graph_elements(records)
    return {
        "nodes": len(graph_data["nodes"]),
        "edges": len(graph_data["edges"]),
        "categories": len({item.get("category", "") for item in records if item.get("category")}),
        "missing_evidence": sum(1 for item in records if not item.get("evidence")),
        "missing_source": sum(1 for item in records if not item.get("source_label")),
    }


def find_graph_issues(records: List[Dict] | None = None) -> List[str]:
    records = records if records is not None else load_graph_data()
    issues = []
    seen = set()
    for index, item in enumerate(records, start=1):
        key = (item.get("source"), item.get("relation"), item.get("target"))
        if key in seen:
            issues.append(f"第 {index} 条关系重复：{item.get('source')} -> {item.get('target')}")
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
    return f"{item.get('source', '')} -> {item.get('target', '')}：{item.get('relation', '')}"


def render_graph_html(graph, output_path: str | Path = DEFAULT_HTML_PATH) -> str:
    output_path = str(output_path)
    try:
        from pyvis.network import Network

        net = Network(height="720px", width="100%", directed=True)
        color_map = {
            "role": "#2563eb",
            "action": "#dc2626",
            "rule": "#16a34a",
            "result": "#ca8a04",
            "scene": "#7c3aed",
            "material": "#0891b2",
        }

        for node_id, attrs in graph.nodes(data=True):
            node_type = attrs.get("node_type", "rule")
            title = f"类型：{node_type}<br>类别：{attrs.get('category', '')}"
            net.add_node(
                node_id,
                label=attrs.get("label", node_id),
                title=title,
                color=color_map.get(node_type, "#4b5563"),
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

        net.write_html(output_path)
        return output_path
    except ModuleNotFoundError:
        html = _render_basic_html(graph)
        Path(output_path).write_text(html, encoding="utf-8")
        return output_path


def _render_basic_html(graph) -> str:
    node_items = []
    edge_items = []
    for node_id, attrs in graph.nodes(data=True):
        node_items.append(
            f"<li><strong>{attrs.get('label', node_id)}</strong> ({attrs.get('node_type', 'rule')})</li>"
        )
    for source, target, attrs in graph.edges(data=True):
        evidence = attrs.get("evidence", "")
        source_label = attrs.get("source_label", "")
        detail = f"<br><small>{evidence} {source_label}</small>" if evidence or source_label else ""
        edge_items.append(f"<li>{source} -> {target} : {attrs.get('label', '')}{detail}</li>")

    return f"""
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>School Policy Rule Graph</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; }}
    h1 {{ margin-bottom: 8px; }}
    .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }}
    ul {{ line-height: 1.7; }}
    small {{ color: #555; }}
  </style>
</head>
<body>
  <h1>School Policy Rule Graph</h1>
  <div class="grid">
    <section>
      <h2>Nodes</h2>
      <ul>
        {''.join(node_items)}
      </ul>
    </section>
    <section>
      <h2>Edges</h2>
      <ul>
        {''.join(edge_items)}
      </ul>
    </section>
  </div>
</body>
</html>
"""


def export_graph_html(output_path: str | Path = DEFAULT_HTML_PATH, keyword: str = "") -> str:
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


def _extract_query_terms(text: str) -> List[str]:
    text = (text or "").strip()
    if not text:
        return []

    domain_terms = [
        "缓考",
        "补考",
        "重修",
        "绩点",
        "成绩",
        "考试",
        "违纪",
        "作弊",
        "缺考",
        "旷课",
        "宿舍",
        "用电",
        "处分",
        "证明",
        "审核",
    ]
    terms = [term for term in domain_terms if term in text]
    terms.extend(token for token in re.split(r"[，。！？、\s]+", text) if len(token) >= 2)

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

    strong_terms = {"作弊", "违纪", "处分", "宿舍", "用电", "绩点", "补考", "重修", "缓考", "缺考", "旷课"}
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

    # Common user wording maps to the policy graph's normalized nodes.
    if (
        "作弊" in query_terms
        and category == "违纪处分"
        and ("考试违纪" in title_text or "成绩无效" in title_text or "纪律处分" in title_text)
    ):
        score += 12
    if "违规" in query_terms and ("宿舍违规用电" in title_text or "纪律处分" in title_text):
        score += 8
    if "缓考" in query_terms and "缓考" in title_text:
        score += 10
    if "绩点" in query_terms and category == "学习管理" and ("绩点" in title_text or "成绩" in title_text):
        score += 10

    if all(term in weak_terms for term in query_terms):
        return 0
    return score
