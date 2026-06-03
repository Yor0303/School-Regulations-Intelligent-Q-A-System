from pathlib import Path

import streamlit as st

from graph_engine import export_graph_html
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

    with st.expander("图谱导出", expanded=False):
        if st.button("生成规则图谱"):
            output_path = export_graph_html()
            st.success(f"图谱已导出到 {output_path}")
