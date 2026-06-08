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
