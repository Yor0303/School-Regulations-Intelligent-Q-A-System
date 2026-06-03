# -*- encoding: utf-8 -*-
# @Author: SWHL
# @Contact: liekkaskono@163.com
import io
import sqlite3
import time
from pathlib import Path
from typing import Dict, List, Optional

import faiss
import numpy as np

from ..utils.logger import logger


def adapt_array(arr):
    out = io.BytesIO()
    np.save(out, arr)
    out.seek(0)
    return sqlite3.Binary(out.read())


def convert_array(text):
    out = io.BytesIO(text)
    out.seek(0)
    return np.load(out, allow_pickle=True)


sqlite3.register_adapter(np.ndarray, adapt_array)
sqlite3.register_converter("array", convert_array)


class DBUtils:
    def __init__(
        self,
        db_path: str,
    ) -> None:
        self.db_path = db_path

        self.table_name = "embedding_texts"
        self.vector_nums = 0

        self.max_prompt_length = 4096

        self.connect_db()

    def connect_db(
        self,
    ):
        db_parent = Path(self.db_path).parent
        db_parent.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        cur = con.cursor()
        cur.execute(
            f"create table if not exists {self.table_name} (id integer primary key autoincrement, file_name TEXT, embeddings array UNIQUE, texts TEXT, uids TEXT)"
        )
        self._ensure_metadata_columns(cur)
        return cur, con

    def _ensure_metadata_columns(self, cur):
        cur.execute(f"pragma table_info({self.table_name})")
        columns = {row[1] for row in cur.fetchall()}
        metadata_columns = {
            "chunk_id": "TEXT",
            "doc_type": "TEXT",
            "page_no": "INTEGER",
            "paragraph_no": "INTEGER",
            "section_title": "TEXT",
            "upload_time": "TEXT",
        }
        for column_name, column_type in metadata_columns.items():
            if column_name not in columns:
                cur.execute(
                    f"alter table {self.table_name} add column {column_name} {column_type}"
                )

    def load_vectors(self, uid: Optional[str] = None):
        cur, _ = self.connect_db()

        search_sql = f"select file_name, embeddings, texts from {self.table_name}"
        if uid:
            search_sql = f'select file_name, embeddings, texts from {self.table_name} where uids="{uid}"'

        cur.execute(search_sql)
        all_vectors = cur.fetchall()

        self.file_names = np.array([v[0] for v in all_vectors])
        all_embeddings = np.array([v[1] for v in all_vectors])
        self.all_texts = np.array([v[2] for v in all_vectors])

        self.search_index = faiss.IndexFlatL2(all_embeddings.shape[1])
        self.search_index.add(all_embeddings)
        self.vector_nums = len(all_vectors)

    def count_vectors(
        self,
    ):
        cur, _ = self.connect_db()

        cur.execute(f"select file_name from {self.table_name}")
        all_vectors = cur.fetchall()
        return len(all_vectors)

    def search_local(
        self,
        embedding_query: np.ndarray,
        top_k: int = 5,
        uid: Optional[str] = None,
    ) -> Optional[Dict[str, List[str]]]:
        s = time.perf_counter()

        cur_vector_nums = self.count_vectors()
        if cur_vector_nums == 0:
            return None, 0

        if cur_vector_nums != self.vector_nums:
            self.load_vectors(uid)

        # cur_vector_nums 小于 top_k 时，返回 cur_vector_nums 个结果
        _, I = self.search_index.search(embedding_query, min(top_k, cur_vector_nums))
        top_index = I.squeeze().tolist()

        # 处理只有一个结果的情况
        if isinstance(top_index, int):
            top_index = [top_index]

        search_contents = self.all_texts[top_index]
        file_names = [self.file_names[idx] for idx in top_index]
        dup_file_names = list(set(file_names))
        dup_file_names.sort(key=file_names.index)

        search_res = {v: [] for v in dup_file_names}
        for file_name, content in zip(file_names, search_contents):
            search_res[file_name].append(content)

        elapse = time.perf_counter() - s
        return search_res, elapse

    def insert(
        self, file_name: str, embeddings: np.ndarray, texts: List[str], uid: str
    ):
        cur, con = self.connect_db()

        file_names = [file_name] * len(embeddings)
        uids = [uid] * len(embeddings)

        t1 = time.perf_counter()
        insert_sql = f"insert or ignore into {self.table_name} (file_name, embeddings, texts, uids) values (?, ?, ?, ?)"
        cur.executemany(insert_sql, list(zip(file_names, embeddings, texts, uids)))
        elapse = time.perf_counter() - t1
        logger.info(
            f"Insert {len(embeddings)} data, total is {len(embeddings)}, cost: {elapse:4f}s"
        )
        con.commit()

    def insert_records(self, records: List[Dict]):
        if not records:
            return

        cur, con = self.connect_db()
        insert_sql = f"""
        insert or replace into {self.table_name}
        (file_name, embeddings, texts, uids, chunk_id, doc_type, page_no, paragraph_no, section_title, upload_time)
        values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        payload = [
            (
                record["file_name"],
                record["embedding"],
                record["text"],
                record.get("uid", ""),
                record["chunk_id"],
                record.get("doc_type"),
                record.get("page_no"),
                record.get("paragraph_no"),
                record.get("section_title"),
                record.get("upload_time"),
            )
            for record in records
        ]
        cur.executemany(insert_sql, payload)
        con.commit()
        self.vector_nums = 0

    def search_with_metadata(
        self,
        embedding_query: np.ndarray,
        top_k: int = 5,
        uid: Optional[str] = None,
    ) -> Optional[List[Dict]]:
        s = time.perf_counter()
        cur_vector_nums = self.count_vectors()
        if cur_vector_nums == 0:
            return None, 0

        if cur_vector_nums != self.vector_nums:
            self.load_vectors(uid)

        _, indexes = self.search_index.search(
            embedding_query, min(top_k, cur_vector_nums)
        )
        top_index = indexes.squeeze().tolist()
        if isinstance(top_index, int):
            top_index = [top_index]

        cur, _ = self.connect_db()
        placeholders = ",".join(["?"] * len(top_index))
        cur.execute(
            f"""
            select file_name, texts, chunk_id, doc_type, page_no, paragraph_no, section_title, uids
            from {self.table_name}
            where id in ({placeholders})
            """,
            [idx + 1 for idx in top_index],
        )
        rows = cur.fetchall()
        row_map = {
            row[2]: {
                "file_name": row[0],
                "text": row[1],
                "chunk_id": row[2],
                "doc_type": row[3],
                "page_no": row[4],
                "paragraph_no": row[5],
                "section_title": row[6],
                "uid": row[7],
            }
            for row in rows
        }

        results = []
        for idx in top_index:
            cur.execute(
                f"""
                select file_name, texts, chunk_id, doc_type, page_no, paragraph_no, section_title, uids
                from {self.table_name}
                where id=?
                """,
                (idx + 1,),
            )
            row = cur.fetchone()
            if row is None:
                continue
            results.append(
                {
                    "file_name": row[0],
                    "text": row[1],
                    "chunk_id": row[2],
                    "doc_type": row[3],
                    "page_no": row[4],
                    "paragraph_no": row[5],
                    "section_title": row[6],
                    "uid": row[7],
                }
            )

        elapse = time.perf_counter() - s
        return results, elapse

    def get_files(self, uid: Optional[str] = None):
        cur, _ = self.connect_db()

        if uid:
            search_sql = (
                f'select distinct file_name from {self.table_name} where uids="{uid}"'
            )
            cur.execute(search_sql)
        else:
            cur.execute(f"select distinct file_name from {self.table_name}")
        search_res = cur.fetchall()
        search_res = [v[0] for v in search_res]
        return search_res

    def delete_file(self, file_name: str):
        cur, con = self.connect_db()
        cur.execute(f"delete from {self.table_name} where file_name=?", (file_name,))
        con.commit()
        self.vector_nums = 0

    def clear_db(
        self,
    ):
        cur, con = self.connect_db()

        run_sql = f"delete from {self.table_name}"
        cur.execute(run_sql)

        con.commit()
        self.connect_db()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.cur.close()
        self.con.close()
