# -*- encoding: utf-8 -*-
import inspect
import json
import re
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List

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
        self.encoder = None
        self.db = DBUtils(self.vector_db_path)
        self.pdf_loader = PDFLoader()
        self.office_loader = None
        self.txt_loader = TXTLoader()
        self.min_chunk_length = 20
        self.chunk_merge_target = max(
            int(self.config.get("SENTENCE_SIZE", 200) * 1.5), 120
        )

        mkdir(self.upload_dir)
        mkdir(self.record_path.parent)

    def _init_encoder(self):
        from rapid_rag.encoder.sentence_transformer import EncodeText as encode_cls

        encoder_params = self.config.get("Encoder", {})
        batch_size = int(self.config.get("encoder_batch_size", 16))
        for model_name, params in encoder_params.items():
            if model_name == "ERNIEBot":
                continue
            init_kwargs = {"batch_size": batch_size, **dict(params)}
            supported = inspect.signature(encode_cls.__init__).parameters
            filtered = {
                key: value
                for key, value in init_kwargs.items()
                if key in supported
            }
            return encode_cls(**filtered)
        raise RuntimeError("No local encoder configuration found.")

    def _get_encoder(self):
        if self.encoder is None:
            try:
                self.encoder = self._init_encoder()
            except ModuleNotFoundError as exc:
                raise RuntimeError(
                    "Embedding dependencies are missing. Install the project requirements before importing or querying documents."
                ) from exc
        return self.encoder

    def add_documents(self, file_paths: List[str]) -> List[Dict]:
        stored_records = []
        encoder = self._get_encoder()
        for file_path in file_paths:
            file_records = self._prepare_file_records(file_path)
            if not file_records:
                continue

            texts = [record["text"] for record in file_records]
            embeddings = encoder(texts)
            if embeddings is None or len(embeddings) == 0:
                continue

            for record, embedding in zip(file_records, embeddings):
                record["embedding"] = embedding

            self.db.insert_records(file_records)
            self._write_records(file_records)
            stored_records.extend(file_records)

        return [enrich_source(record) for record in stored_records]

    def _prepare_file_records(self, file_path: str) -> List[Dict]:
        source_path = Path(file_path)
        target_path = self.upload_dir / source_path.name
        if source_path.resolve() != target_path.resolve():
            shutil.copy2(source_path, target_path)
        return self._extract_structured_chunks(target_path)

    def clear_all_documents(self) -> None:
        for item in self.list_documents():
            self.delete_document(item["file_name"])

    def query_documents(self, query: str, top_k: int = 5) -> List[Dict]:
        query_embedding = self._get_encoder()(query)
        search_top_k = max(top_k * 3, top_k)
        results, _ = self.db.search_with_metadata(query_embedding, top_k=search_top_k)
        if not results:
            return []
        reranked = self._rerank_results(query, results)
        return [enrich_source(result) for result in reranked[:top_k]]

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
            merged_contents = self._merge_chunks(split_contents)
            for text in merged_contents:
                if not self._is_meaningful_chunk(text):
                    continue
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

    def _get_office_loader(self):
        if self.office_loader is None:
            from rapid_rag.file_loader.office_loader import OfficeLoader

            self.office_loader = OfficeLoader()
        return self.office_loader

    def _extract_text_chunks(self, file_path: Path) -> List[Dict]:
        suffix = file_path.suffix.lower()
        if suffix in {".doc", ".docx", ".ppt", ".pptx", ".xlsx", ".xls"}:
            office_loader = self._get_office_loader()
            contents = office_loader.extracter(file_path)
            splitter = office_loader.splitter
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
            merged_contents = self._merge_chunks(split_contents)
            for text in merged_contents:
                if not self._is_meaningful_chunk(text):
                    continue
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

    def _merge_chunks(self, chunks: List[str]) -> List[str]:
        merged = []
        buffer = []
        buffer_length = 0
        for raw_chunk in chunks:
            chunk = raw_chunk.strip()
            if not chunk:
                continue
            projected_length = buffer_length + len(chunk)
            if buffer and projected_length > self.chunk_merge_target:
                merged.append(" ".join(buffer).strip())
                buffer = [chunk]
                buffer_length = len(chunk)
            else:
                buffer.append(chunk)
                buffer_length = projected_length

        if buffer:
            merged.append(" ".join(buffer).strip())
        return merged

    def _is_meaningful_chunk(self, text: str) -> bool:
        compact = " ".join(text.split())
        if len(compact) < self.min_chunk_length:
            return False
        if "目录" in compact and len(compact) < 80:
            return False
        if compact.endswith("学生手册") and len(compact) < 40:
            return False
        digit_count = sum(char.isdigit() for char in compact)
        if digit_count > len(compact) * 0.5:
            return False
        return True

    def _rerank_results(self, query: str, results: List[Dict]) -> List[Dict]:
        keywords = self._extract_keywords(query)
        scored_results = []
        for index, result in enumerate(results):
            text = result.get("text", "")
            score = 0
            for keyword in keywords:
                if keyword in text:
                    score += 3
            if result.get("section_title"):
                for keyword in keywords:
                    if keyword in result["section_title"]:
                        score += 2
            if "绩点" in query and "绩点" in text:
                score += 4
            if any(term in query for term in ["怎么办", "如何", "怎么"]):
                if any(term in text for term in ["重修", "补考", "处理", "规定", "不得"]):
                    score += 2
            scored_results.append((score, -index, result))

        scored_results.sort(reverse=True)
        return [item[2] for item in scored_results]

    def _extract_keywords(self, query: str) -> List[str]:
        parts = re.split(r"[，。！？、\s]+", query)
        keywords = []
        stop_words = {"怎么办", "如何", "怎么", "是否", "可以", "需要", "如果", "什么"}
        for part in parts:
            token = part.strip()
            if len(token) < 2 or token in stop_words:
                continue
            keywords.append(token)
            if len(token) > 2:
                keywords.extend(
                    sub_token
                    for sub_token in ["绩点", "重修", "补考", "学分", "成绩", "不及格", "挂科"]
                    if sub_token in token
                )
        deduped = []
        for keyword in keywords:
            if keyword not in deduped:
                deduped.append(keyword)
        return deduped
