from typing import Dict


def build_source_label(record: Dict) -> str:
    file_name = record.get("file_name", "unknown")
    page_no = record.get("page_no")
    paragraph_no = record.get("paragraph_no")
    section_title = record.get("section_title")

    suffix_parts = []
    if page_no:
        suffix_parts.append(f"page {page_no}")
    elif paragraph_no:
        suffix_parts.append(f"paragraph {paragraph_no}")

    if section_title:
        suffix_parts.append(section_title)

    if not suffix_parts:
        return file_name
    return f"{file_name}, " + ", ".join(suffix_parts)


def enrich_source(record: Dict) -> Dict:
    new_record = dict(record)
    new_record["source_label"] = build_source_label(record)
    return new_record
