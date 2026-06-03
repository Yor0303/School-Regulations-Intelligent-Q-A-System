# -*- encoding: utf-8 -*-
from pathlib import Path
from typing import Dict, List

import networkx as nx


def load_graph_seed_data() -> List[Dict]:
    return [
        {"source": "学生", "target": "课程未通过", "relation": "可能出现", "source_type": "role", "target_type": "result"},
        {"source": "课程未通过", "target": "补考", "relation": "可参加", "source_type": "result", "target_type": "action"},
        {"source": "学生", "target": "旷课", "relation": "可能发生", "source_type": "role", "target_type": "action"},
        {"source": "旷课", "target": "不得参加期末考核", "relation": "导致", "source_type": "action", "target_type": "result"},
        {"source": "学生", "target": "缺考", "relation": "可能发生", "source_type": "role", "target_type": "action"},
        {"source": "缺考", "target": "零分", "relation": "记为", "source_type": "action", "target_type": "result"},
        {"source": "学生", "target": "缓考", "relation": "可申请", "source_type": "role", "target_type": "action"},
        {"source": "缓考", "target": "教务部审核", "relation": "需要", "source_type": "action", "target_type": "rule"},
        {"source": "学生", "target": "考试违纪", "relation": "可能发生", "source_type": "role", "target_type": "action"},
        {"source": "考试违纪", "target": "无效", "relation": "成绩标注", "source_type": "action", "target_type": "result"},
        {"source": "违纪课程", "target": "学分0", "relation": "记为", "source_type": "rule", "target_type": "result"},
        {"source": "学分0", "target": "计入绩点统计", "relation": "影响", "source_type": "result", "target_type": "rule"},
        {"source": "成绩", "target": "绩点", "relation": "影响", "source_type": "rule", "target_type": "rule"},
        {"source": "绩点", "target": "平均绩点", "relation": "组成", "source_type": "rule", "target_type": "rule"},
    ]


def extract_graph_elements() -> Dict:
    seeds = load_graph_seed_data()
    node_map = {}
    edges = []
    for item in seeds:
        node_map[item["source"]] = {"id": item["source"], "label": item["source"], "type": item["source_type"]}
        node_map[item["target"]] = {"id": item["target"], "label": item["target"], "type": item["target_type"]}
        edges.append(
            {
                "source": item["source"],
                "target": item["target"],
                "label": item["relation"],
            }
        )
    return {"nodes": list(node_map.values()), "edges": edges}


def build_rule_graph(graph_data: Dict):
    graph = nx.DiGraph()
    for node in graph_data["nodes"]:
        graph.add_node(node["id"], label=node["label"], node_type=node["type"])
    for edge in graph_data["edges"]:
        graph.add_edge(edge["source"], edge["target"], label=edge["label"])
    return graph


def render_graph_html(graph, output_path: str) -> str:
    try:
        from pyvis.network import Network

        net = Network(height="720px", width="100%", directed=True)
        color_map = {
            "role": "#2563eb",
            "action": "#dc2626",
            "rule": "#16a34a",
            "result": "#ca8a04",
            "scene": "#7c3aed",
        }

        for node_id, attrs in graph.nodes(data=True):
            node_type = attrs.get("node_type", "rule")
            net.add_node(
                node_id,
                label=attrs.get("label", node_id),
                color=color_map.get(node_type, "#4b5563"),
            )

        for source, target, attrs in graph.edges(data=True):
            net.add_edge(source, target, label=attrs.get("label", ""))

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
        node_items.append(f"<li><strong>{attrs.get('label', node_id)}</strong> ({attrs.get('node_type', 'rule')})</li>")
    for source, target, attrs in graph.edges(data=True):
        edge_items.append(f"<li>{source} -> {target} : {attrs.get('label', '')}</li>")

    return f"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Rule Graph</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; }}
    h1 {{ margin-bottom: 8px; }}
    .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }}
    ul {{ line-height: 1.6; }}
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


def export_graph_html(output_path: str = "rule_graph.html") -> str:
    graph_data = extract_graph_elements()
    graph = build_rule_graph(graph_data)
    return render_graph_html(graph, output_path)
