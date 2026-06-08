# -*- encoding: utf-8 -*-
"""Batch import files from materials/ into the vector knowledge base."""
import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from knowledge_base import KnowledgeBaseService
from rapid_rag.utils import read_yaml

SUPPORTED_SUFFIXES = {
    ".pdf",
    ".doc",
    ".docx",
    ".txt",
    ".md",
    ".ppt",
    ".pptx",
    ".xlsx",
    ".xls",
}


def collect_material_files(materials_dir: Path) -> list[Path]:
    files = []
    for path in sorted(materials_dir.iterdir()):
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES:
            files.append(path)
    return files


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Batch import materials into the school rules knowledge base."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List files that would be imported without writing to the database.",
    )
    parser.add_argument(
        "--force",
        action="append",
        default=[],
        metavar="FILE",
        help="Re-import a specific file even if it already exists in the database.",
    )
    parser.add_argument(
        "--force-all",
        action="store_true",
        help="Clear the knowledge base and re-import every file in materials/.",
    )
    parser.add_argument(
        "--materials-dir",
        type=str,
        default=None,
        help="Override materials directory from config.yaml.",
    )
    args = parser.parse_args()

    config = read_yaml("rapid_rag/config.yaml")
    materials_dir = Path(args.materials_dir or config.get("materials_dir", "materials"))
    if not materials_dir.exists():
        print(f"Materials directory not found: {materials_dir}")
        return 1

    service = KnowledgeBaseService()
    material_files = collect_material_files(materials_dir)
    if not material_files:
        print(f"No supported files found in {materials_dir}")
        return 1

    if args.force_all:
        if args.dry_run:
            print("[dry-run] Would clear all documents and re-import everything.")
        else:
            print("Clearing existing knowledge base...")
            service.clear_all_documents()

    existing = {item["file_name"] for item in service.list_documents()}
    force_names = set(args.force)

    to_import: list[Path] = []
    skipped: list[str] = []
    for path in material_files:
        name = path.name
        if name in force_names:
            if not args.dry_run and name in existing:
                service.delete_document(name)
                existing.discard(name)
            to_import.append(path)
        elif name in existing:
            skipped.append(name)
        else:
            to_import.append(path)

    print(f"Materials dir: {materials_dir.resolve()}")
    print(
        f"Found {len(material_files)} file(s), "
        f"import {len(to_import)}, skip {len(skipped)}"
    )
    if skipped:
        print("Skipped (already in DB):")
        for name in skipped:
            print(f"  - {name}")

    if not to_import:
        print("Nothing to import.")
        return 0

    if args.dry_run:
        print("[dry-run] Would import:")
        for path in to_import:
            print(f"  - {path.name}")
        return 0

    service._get_encoder()
    encoder = service.encoder
    print(f"Encoder device: {getattr(encoder, 'device', 'unknown')}")

    for path in to_import:
        print(f"Importing: {path.name} ...", flush=True)
        records = service.add_documents([str(path)])
        print(f"  -> {len(records)} chunk(s)")

    print("\nKnowledge base now contains:")
    for item in service.list_documents():
        print(f"  - {item['file_name']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
