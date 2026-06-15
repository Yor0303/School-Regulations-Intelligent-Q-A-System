# -*- encoding: utf-8 -*-
import json
from pathlib import Path
from typing import Dict, List, Optional

REGISTRY_PATH = Path("data/documents/registry.json")


def load_registry() -> Dict:
    path = REGISTRY_PATH
    if not path.exists():
        return {"document_types": [], "disclaimer": ""}
    return json.loads(path.read_text(encoding="utf-8"))


def get_document_types() -> List[Dict]:
    return load_registry().get("document_types", [])


def get_disclaimer() -> str:
    return load_registry().get("disclaimer", "")


def get_type_by_id(type_id: str) -> Optional[Dict]:
    for item in get_document_types():
        if item.get("id") == type_id:
            return item
    return None


def match_type_by_keywords(text: str) -> Optional[Dict]:
    text = text or ""
    best = None
    best_score = 0
    for item in get_document_types():
        score = 0
        for kw in item.get("keywords", []):
            if kw in text:
                score += len(kw)
        if score > best_score:
            best_score = score
            best = item
    return best if best_score > 0 else None


def list_type_options() -> List[tuple]:
    return [(t["id"], t["title"]) for t in get_document_types()]
