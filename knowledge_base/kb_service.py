# -*- encoding: utf-8 -*-
import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from rapid_rag.encoder import EncodeText
from rapid_rag.file_loader.office_loader import OfficeLoader
from rapid_rag.file_loader.pdf_loader import PDFLoader
from rapid_rag.file_loader.txt_loader import TXTLoader
from rapid_rag.utils import mkdir, read_yaml
from rapid_rag.vector_utils import DBUtils

from .source_mapper import enrich_source


class KnowledgeBaseService:
    def __init__(self, config_path: str = "rapid_rag/config.yaml") -> None:
        self.config = read_yaml(config_path)
        self.upload_dir = Path(self.config.get("upload_dir", "data/uploads"))
        self.vector_db_path = self.config.get(
            "vector_db_path", "data/vector_db/school_rules.db"
        )
        self.record_path = Path(
            self.config.get("record_path", "vector_db_data/handbook_chunks.json")
        )
        self.encoder = self._init_encoder()
        self.db = DBUtils(self.vector_db_path)
        self.pdf_loader = PDFLoader()
        self.office_loader = OfficeLoader()
        self.txt_loader = TXTLoader()

        mkdir(self.upload_dir)
        mkdir(self.record_path.parent)

    def _init_encoder(self):
        encoder_params = self.config.get("Encoder", {})
        model_name, params = next(iter(encoder_params.items()))
        return EncodeText(**params)

    def add_documents(self, file_paths: List[str]) -> List[Dict]:
        stored_records = []
        for file_path in file_paths:
            source_path = Path(file_path)
            target_path = self.upload_dir / source_path.name
            if source_path.resolve() != target_path.resolve():
                shutil.copy2(source_path, target_path)
            structured_chunks = self._extract_structured_chunks(target_path)
            stored_records.extend(structured_chunks)

        if not stored_records:
            return []

        embeddings = self.encoder([record["text"] for record in stored_records])
        if embeddings is None or len(embeddings) == 0:
            return []

        for record, embedding in zip(stored_records, embeddings):
            record["embedding"] = embedding

        self.db.insert_records(stored_records)
        self._write_records(stored_records)
        return [enrich_source(record) for record in stored_records]

    def query_documents(self, query: str, top_k: int = 5) -> List[Dict]:
        query_embedding = self.encoder(query)
        results, _ = self.db.search_with_metadata(query_embedding, top_k=top_k)
        if not results:
            return []
        return [enrich_source(result) for result in results]

    def list_documents(self) -> List[Dict]:
        file_names = self.db.get_files() or []
        return [{"file_name": file_name} for file_name in file_names]

    def delete_document(self, file_name: str) -> None:
        self.db.delete_file(file_name)
        saved_file = self.upload_dir / file_name
        if saved_file.exists():
            saved_file.unlink()
        if self.record_path.exists():
            records = json.loads(self.record_path.read_text(encoding="utf-8"))
            records = [record for record in records if record["file_name"] != file_name]
            self.record_path.write_text(
                json.dumps(records, ensure_ascii=True, indent=2), encoding="utf-8"
            )

    def _extract_structured_chunks(self, file_path: Path) -> List[Dict]:
        suffix = file_path.suffix.lower()
        upload_time = datetime.now().isoformat(timespec="seconds")
        if suffix == ".pdf":
            chunks = self._extract_pdf_chunks(file_path)
        elif suffix in {".doc", ".docx", ".ppt", ".pptx", ".xlsx", ".xls", ".md", ".txt"}:
            chunks = self._extract_text_chunks(file_path)
        else:
            return []

        records = []
        for index, chunk in enumerate(chunks, start=1):
            text = chunk.get("text", "").strip()
            if not text:
                continue
            records.append(
                {
                    "file_name": file_path.name,
                    "chunk_id": f"{file_path.stem}_{index}_{uuid.uuid4().hex[:8]}",
                    "doc_type": suffix[1:],
                    "page_no": chunk.get("page_no"),
                    "paragraph_no": chunk.get("paragraph_no"),
                    "section_title": chunk.get("section_title"),
                    "text": text,
                    "uid": "",
                    "upload_time": upload_time,
                }
            )
        return records

    def _extract_pdf_chunks(self, file_path: Path) -> List[Dict]:
        contents = self.pdf_loader.extracter(file_path)
        records = []
        paragraph_no = 0
        for page_idx, content in enumerate(contents, start=1):
            page_text = content[1] if isinstance(content, (list, tuple)) else content
            split_contents = self.pdf_loader.splitter.split_text(page_text)
            for text in split_contents:
                paragraph_no += 1
                records.append(
                    {
                        "text": text,
                        "page_no": page_idx,
                        "paragraph_no": paragraph_no,
                        "section_title": "",
                    }
                )
        return records

    def _extract_text_chunks(self, file_path: Path) -> List[Dict]:
        suffix = file_path.suffix.lower()
        if suffix in {".doc", ".docx", ".ppt", ".pptx", ".xlsx", ".xls"}:
            contents = self.office_loader.extracter(file_path)
            splitter = self.office_loader.splitter
        else:
            contents = self.txt_loader(file_path)
            return [
                {
                    "text": text,
                    "page_no": None,
                    "paragraph_no": index,
                    "section_title": "",
                }
                for index, text in enumerate(contents, start=1)
            ]

        records = []
        paragraph_no = 0
        for raw_text in contents:
            split_contents = splitter.split_text(raw_text)
            for text in split_contents:
                paragraph_no += 1
                records.append(
                    {
                        "text": text,
                        "page_no": None,
                        "paragraph_no": paragraph_no,
                        "section_title": "",
                    }
                )
        return records

    def _write_records(self, records: List[Dict]) -> None:
        serializable_records = []
        for record in records:
            serializable_records.append(
                {
                    key: value
                    for key, value in record.items()
                    if key != "embedding"
                }
            )

        existing = []
        if self.record_path.exists():
            existing = json.loads(self.record_path.read_text(encoding="utf-8"))
        existing.extend(serializable_records)
        self.record_path.write_text(
            json.dumps(existing, ensure_ascii=True, indent=2), encoding="utf-8"
        )
