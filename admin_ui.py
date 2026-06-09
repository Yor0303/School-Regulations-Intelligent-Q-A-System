from pathlib import Path

import streamlit as st

from graph_engine import (
    auto_build_graph_from_docs,
    export_graph_html,
    export_graph_json,
    find_graph_issues,
    get_graph_stats,
    load_graph_data,
    refresh_graph_data,
)
from settings_manager import load_settings, save_settings
from knowledge_base import KnowledgeBaseService


def render_admin_panel() -> None:
    st.subheader("管理员后台")
    settings = load_settings()
    kb_service = KnowledgeBaseService()

    with st.expander("系统设置", expanded=True):
        site_title = st.text_input("系统标题", value=settings.get("site_title", ""))
        bot_name = st.text_input("机器人名称", value=settings.get("bot_name", ""))
        welcome_message = st.text_area(
            "欢迎语",
            value=settings.get("welcome_message", ""),
            height=120,
        )
        bot_avatar = st.text_input(
            "机器人头像路径",
            value=settings.get("bot_avatar", ""),
            help="可填写本地图片路径，供前端显示头像。",
        )
        admin_password = st.text_input(
            "管理员密码", value=settings.get("admin_password", ""), type="password"
        )
        if st.button("保存设置"):
            save_settings(
                {
                    "site_title": site_title,
                    "bot_name": bot_name,
                    "bot_avatar": bot_avatar,
                    "welcome_message": welcome_message,
                    "admin_password": admin_password,
                }
            )
            st.success("设置已保存。")

    with st.expander("知识库文件管理", expanded=True):
        uploaded_files = st.file_uploader(
            "上传学校制度文件",
            accept_multiple_files=True,
            type=["pdf", "docx", "doc", "txt", "md", "ppt", "pptx", "xlsx", "xls"],
        )
        if st.button("导入所选文件"):
            if not uploaded_files:
                st.warning("请至少选择一个文件。")
            else:
                temp_paths = []
                for uploaded_file in uploaded_files:
                    temp_path = Path("data/uploads") / uploaded_file.name
                    temp_path.write_bytes(uploaded_file.getbuffer())
                    temp_paths.append(str(temp_path))
                kb_service.add_documents(temp_paths)
                st.success("文件已导入知识库。")

        documents = kb_service.list_documents()
        if documents:
            st.markdown("当前知识库文件：")
            for item in documents:
                col1, col2 = st.columns([4, 1])
                col1.write(item["file_name"])
                if col2.button("删除", key=f"delete_{item['file_name']}"):
                    kb_service.delete_document(item["file_name"])
                    st.rerun()
        else:
            st.info("当前知识库中还没有文件。")

        st.markdown("---")
        st.markdown("#### 网页种子爬取")
        st.caption(
            "从预设的种子 URL 出发，提取该页面正文，并自动跟随页面上所有"
            "同域链接再提取一层（不递归）。种子 URL 保存在 `data/settings/seed_urls.json`。"
        )

        col_a, col_b = st.columns([3, 1])
        with col_a:
            import json as _json
            seed_path = Path("data/settings/seed_urls.json")
            try:
                current_seeds = _json.loads(seed_path.read_text(encoding="utf-8"))
            except Exception:
                current_seeds = []

            edited_seeds = st.text_area(
                "种子 URL（每行一个，可直接编辑）",
                value="\n".join(current_seeds),
                height=100,
                key="seed_url_editor",
            )
        with col_b:
            st.caption("")  # spacer
            st.caption("")

        col_crawl, col_save = st.columns([1, 1])
        with col_save:
            if st.button("保存种子列表", key="save_seeds_btn"):
                new_seeds = [u.strip() for u in edited_seeds.split("\n") if u.strip()]
                seed_path.parent.mkdir(parents=True, exist_ok=True)
                seed_path.write_text(
                    _json.dumps(new_seeds, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                st.success(f"已保存 {len(new_seeds)} 个种子 URL。")
                st.rerun()
        with col_crawl:
            if st.button("从种子 URL 爬取", type="primary", key="crawl_seed_btn"):
                urls_to_crawl = [u.strip() for u in edited_seeds.split("\n") if u.strip()]
                if not urls_to_crawl:
                    st.warning("请至少输入一个种子 URL。")
                else:
                    with st.spinner(f"正在爬取 {len(urls_to_crawl)} 个种子页面（含链接页面）..."):
                        result = kb_service.add_seed_urls(urls_to_crawl)
                    if result:
                        st.success(f"爬取完成，共导入 {len(result)} 个文本块。")
                        st.rerun()
                    else:
                        st.error("爬取失败。请检查 URL 是否可访问。")

        st.markdown("---")
        st.markdown("#### 网页单页导入")
        st.caption("粘贴单个网页 URL，仅提取该页正文（不跟随链接）。")

        web_urls = st.text_area(
            "网页 URL（每行一个）",
            height=80,
            placeholder="https://xxx.edu.cn/policy/123",
            key="web_url_input",
        )
        if st.button("导入网页内容", key="import_web_btn"):
            urls = [u.strip() for u in web_urls.split("\n") if u.strip()]
            if not urls:
                st.warning("请至少输入一个 URL。")
            else:
                with st.spinner(f"正在抓取 {len(urls)} 个网页并提取正文..."):
                    result = kb_service.add_urls(urls)
                if result:
                    st.success(f"已导入 {len(urls)} 个网页，共 {len(result)} 个文本块。")
                    st.rerun()
                else:
                    st.error("导入失败。请检查 URL 是否可访问，以及页面是否包含可提取的正文。")

    with st.expander("规则图谱维护", expanded=False):
        records = load_graph_data()
        stats = get_graph_stats(records)
        col1, col2, col3 = st.columns(3)
        col1.metric("节点数", stats["nodes"])
        col2.metric("关系数", stats["edges"])
        col3.metric("规则类别", stats["categories"])

        col1, col2, col3 = st.columns(3)
        if col1.button("刷新图谱数据"):
            data_path = refresh_graph_data()
            st.success(f"图谱数据已刷新：{data_path}")
            st.rerun()
        if col2.button("导出 HTML"):
            output_path = export_graph_html()
            st.success(f"图谱已导出到 {output_path}")
        if col3.button("导出 JSON"):
            output_path = export_graph_json()
            st.success(f"图谱数据已导出到 {output_path}")

        st.markdown("---")
        st.markdown("#### LLM 自动抽取规则")
        st.caption(
            "利用大模型从已上传的文档中自动提取实体-关系-实体三元组，"
            "扩充知识图谱。处理时间取决于文档数量和 LLM 速度。"
        )

        if st.button("从文档自动抽取规则", type="primary"):
            import sys
            from pathlib import Path as _Path

            record_path = _Path("vector_db_data/handbook_chunks.json")
            if not record_path.exists():
                st.error("未找到文档切片数据，请先导入制度文件。")
            else:
                progress_bar = st.progress(0, "正在准备...")
                status_text = st.empty()

                def progress_callback(
                    file_idx, total_files, fname, step, total_steps
                ):
                    pct = int(((file_idx + step / max(total_steps, 1)) / total_files) * 100)
                    progress_bar.progress(
                        min(pct, 100),
                        f"处理中：{fname} ({step}/{total_steps})",
                    )
                    status_text.text(
                        f"正在处理第 {file_idx + 1}/{total_files} 个文件：{fname}"
                    )

                try:
                    merged = auto_build_graph_from_docs(
                        record_path=record_path,
                        max_chunks_per_file=6,
                        progress_callback=progress_callback,
                    )
                    progress_bar.progress(100, "抽取完成！")
                    new_stats = get_graph_stats(merged)
                    st.success(
                        f"规则抽取完成！图谱现有 {new_stats['nodes']} 个节点、"
                        f"{new_stats['edges']} 条关系，覆盖 {new_stats['categories']} 个类别。"
                    )
                    st.rerun()
                except Exception as exc:
                    st.error(f"抽取过程出错：{exc}")

        issues = find_graph_issues(records)
        if issues:
            st.warning("发现需要检查的图谱数据：")
            for issue in issues:
                st.write(f"- {issue}")
        else:
            st.success("图谱节点和关系检查通过。")
