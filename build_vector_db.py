# -*- encoding: utf-8 -*-
from pathlib import Path

from knowledge_base import KnowledgeBaseService
from rapid_rag.utils import read_yaml


def main():
    config = read_yaml("rapid_rag/config.yaml")
    service = KnowledgeBaseService()
    default_handbook = Path(config.get("default_handbook", ""))
    if not default_handbook.exists():
        print(f"Default handbook not found: {default_handbook}")
        return

    existing_files = {item["file_name"] for item in service.list_documents()}
    if default_handbook.name in existing_files:
        print(f"{default_handbook.name} already exists in the knowledge base.")
        return

    service.add_documents([str(default_handbook)])
    print(f"Imported default handbook: {default_handbook.name}")


if __name__ == "__main__":
    main()
