# -*- encoding: utf-8 -*-
import importlib
import streamlit as st
import base64
from pathlib import Path

from ollama_env import apply_ollama_env, validate_models_directory

apply_ollama_env(force_from_config=True)

import admin_ui
import chains
import graph_engine
import knowledge_base.kb_service as kb_service_module
import rapid_rag.encoder.sentence_transformer as sentence_transformer_module
import document_ui
import user_ui
from auth import ensure_auth_state, login_admin, logout_admin
from settings_manager import load_settings

# Streamlit 会缓存已 import 的模块；热更新后避免 UI/检索仍跑旧代码。
# 注意：依赖顺序很重要 — graph_engine 必须在 chains 之前重载。
importlib.reload(sentence_transformer_module)
importlib.reload(kb_service_module)
importlib.reload(graph_engine)
import document_service.service as document_service_module

importlib.reload(chains)
importlib.reload(document_service_module)
importlib.reload(document_ui)
importlib.reload(user_ui)
importlib.reload(admin_ui)

def img_to_base64(image_path):
    """将本地图片转换为 Base64 字符串"""
    image_path = Path(__file__).parent / image_path
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode()

def main():
    settings = load_settings()
    st.set_page_config(
        page_title=settings.get("site_title", "上海大学校园规则检索与合规咨询系统"),
        page_icon="assets/images/shu_logo1.png",
        layout="wide"
    )
    ensure_auth_state()

    # ==================== 自定义上海大学风格 CSS ====================
    st.markdown("""
    <style>
    /* 全局背景 */
    .stApp {
        background-color: #F5F7FA;
    }
    /* 顶部横幅样式 */
    .shu-banner {
        background: linear-gradient(135deg, #004098 0%, #002766 100%);
        padding: 1.2rem 2rem;
        border-radius: 0 0 20px 20px;
        margin-bottom: 1.5rem;
        color: white;
        display: flex;
        align-items: center;
        gap: 1rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    .shu-banner h1 {
        margin: 0;
        font-size: 1.8rem;
        font-weight: 600;
    }
    .shu-banner p {
        margin: 0;
        opacity: 0.85;
        font-size: 0.9rem;
    }
    /* 侧边栏保留默认样式，不覆盖按钮 */
    /* 卡片样式（用于主内容区） */
    .main-card {
        background-color: white;
        border-radius: 20px;
        padding: 1rem 1.5rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        margin-bottom: 1.5rem;
        border: 1px solid #E9EDF2;
    }
    /* 校园制度分类：低调标签，避免像可点击按钮 */
    .category-tags {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 0.35rem 0.5rem;
        margin: 0.25rem 0 1.75rem 0;
        padding-bottom: 0.75rem;
        border-bottom: 1px solid #E9EDF2;
    }
    .category-tags-label {
        font-size: 0.78rem;
        color: #94A3B8;
        letter-spacing: 0.04em;
        margin-right: 0.25rem;
    }
    .category-tag {
        display: inline-block;
        padding: 0.12rem 0.55rem;
        border-radius: 999px;
        background: #F1F5F9;
        color: #94A3B8;
        font-size: 0.76rem;
        font-weight: 400;
        border: none;
        pointer-events: none;
    }

    /* 热门咨询：官网风标题区 */
    .hot-q-panel {
        position: relative;
    }
    .hot-q-header {
        text-align: center;
        margin-bottom: 1.25rem;
    }
    .hot-q-eyebrow {
        font-size: 0.72rem;
        letter-spacing: 0.22em;
        color: #004098;
        font-weight: 600;
        opacity: 0.85;
        margin-bottom: 0.35rem;
    }
    .hot-q-title {
        margin: 0;
        font-size: 1.85rem;
        font-weight: 700;
        color: #002766;
        letter-spacing: 0.02em;
    }
    .hot-q-subtitle {
        margin: 0.5rem auto 0;
        max-width: 36rem;
        font-size: 0.92rem;
        color: #64748B;
        line-height: 1.6;
    }

    /* 热门咨询问题卡片按钮 */
    [data-testid="stVerticalBlock"]:has(.hot-q-panel) {
        background: linear-gradient(180deg, #FFFFFF 0%, #F8FAFC 100%);
        border: 1px solid #E2E8F0;
        border-radius: 20px;
        padding: 0 1.25rem 1.25rem 1.25rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 8px 32px rgba(0, 64, 152, 0.06);
        position: relative;
        overflow: hidden;
    }
    [data-testid="stVerticalBlock"]:has(.hot-q-panel)::before {
        content: "";
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
        background: linear-gradient(90deg, #004098 0%, #3B82F6 50%, #004098 100%);
    }
    [data-testid="stVerticalBlock"]:has(.hot-q-panel) .hot-q-panel {
        border: none;
        box-shadow: none;
        padding: 1.75rem 0.75rem 0.25rem 0.75rem;
        margin-bottom: 0;
        background: transparent;
    }
    [data-testid="stVerticalBlock"]:has(.hot-q-panel) button {
        background: #FFFFFF !important;
        color: #1E293B !important;
        border: 1px solid #E2E8F0 !important;
        border-left: 3px solid #004098 !important;
        border-radius: 12px !important;
        padding: 1.1rem 1rem !important;
        min-height: 4.25rem !important;
        height: auto !important;
        font-size: 0.95rem !important;
        font-weight: 500 !important;
        line-height: 1.55 !important;
        white-space: normal !important;
        text-align: left !important;
        box-shadow: 0 2px 10px rgba(15, 23, 42, 0.04) !important;
        transition: all 0.2s ease !important;
    }
    [data-testid="stVerticalBlock"]:has(.hot-q-panel) button:hover {
        color: #004098 !important;
        border-color: #B8C9E0 !important;
        border-left-color: #004098 !important;
        background: #F8FAFC !important;
        transform: translateY(-2px);
        box-shadow: 0 10px 24px rgba(0, 64, 152, 0.1) !important;
    }
    /* 输入框圆角 */
    .stTextInput > div > div > input {
        border-radius: 40px;
        border: 1px solid #CCD7E8;
        padding: 0.5rem 1rem;
    }
    .stTextArea > div > div > textarea {
        border-radius: 20px;
        border: 1px solid #CCD7E8;
    }

    /* 功能 Tab：加大、加边框、选中态上大蓝 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.75rem;
        background-color: #E8EEF8;
        border-radius: 16px;
        padding: 0.5rem;
        border: 1px solid #CCD7E8;
    }
    .stTabs [data-baseweb="tab"] {
        height: 3rem;
        padding: 0 1.5rem;
        background-color: #ffffff;
        border-radius: 12px !important;
        border: 2px solid #B8C9E0 !important;
        color: #334155 !important;
        font-weight: 600 !important;
        font-size: 1.05rem !important;
        box-shadow: 0 2px 6px rgba(0, 64, 152, 0.06);
    }
    .stTabs [data-baseweb="tab"]:hover {
        border-color: #004098 !important;
        color: #004098 !important;
        background-color: #F0F5FC !important;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #004098 0%, #002766 100%) !important;
        color: #ffffff !important;
        border-color: #004098 !important;
        box-shadow: 0 4px 12px rgba(0, 64, 152, 0.28);
    }
    .stTabs [data-baseweb="tab-highlight"] {
        background-color: transparent !important;
    }
    .stTabs [data-baseweb="tab-border"] {
        display: none;
    }

    /* 聊天输入框：白底、蓝框、阴影，一眼能看出是可输入区域 */
    [data-testid="stChatInput"] {
        background: #ffffff;
        border: 2px solid #004098;
        border-radius: 18px;
        padding: 0.35rem 0.5rem;
        box-shadow: 0 6px 20px rgba(0, 64, 152, 0.14);
    }
    [data-testid="stChatInput"]:focus-within {
        border-color: #002766;
        box-shadow: 0 8px 24px rgba(0, 64, 152, 0.22);
    }
    [data-testid="stChatInput"] textarea {
        font-size: 1.05rem !important;
        color: #1e293b !important;
        min-height: 3rem !important;
        padding: 0.65rem 0.75rem !important;
    }
    [data-testid="stChatInput"] textarea::placeholder {
        color: #64748b !important;
        font-weight: 500;
        opacity: 1 !important;
    }
    [data-testid="stChatInput"] button {
        background-color: #004098 !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 12px !important;
    }
    [data-testid="stChatInput"] button:hover {
        background-color: #002766 !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # 读取校徽并转为 Base64
    logo_base64 = img_to_base64("assets/images/shu_logo2.png")
    # 自定义 CSS 样式 + HTML 横幅（嵌入 base64 图片）
    st.markdown(
        f"""
        <style>
        .shu-banner {{
            background: linear-gradient(135deg, #004098 0%, #002766 100%);
            padding: 1rem 2rem;
            border-radius: 20px;
            margin-bottom: 1.5rem;
            color: white;
            display: flex;
            align-items: center;
            gap: 1rem;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }}
        .shu-banner h1 {{
            margin: 0;
            font-size: 1.6rem;
            font-weight: 600;
        }}
        .shu-banner p {{
            margin: 0;
            opacity: 0.85;
            font-size: 0.9rem;
        }}
        </style>
        <div class="shu-banner">
            <img src="data:image/png;base64,{logo_base64}" style="height: 100px; width: auto; margin-right: 1rem;" alt="上海大学校徽">
            <div>
                <h1>上海大学校园规则语义检索与合规咨询系统</h1>
                <p>基于大模型与知识库的智能校规问答助手</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("""
    <style>
    [data-testid="stSidebar"] {
        background-color: linear-gradient(135deg, #E8EEF8 0%, #D9E2EF 100%);
    }
    </style>
    """, unsafe_allow_html=True)
    with st.sidebar:
        st.header("访问控制")
        ok, models_msg = validate_models_directory()
        st.caption(f"Ollama 模型库：{models_msg}")
        if not ok:
            st.caption(
                "可在 `rapid_rag/config.local.yaml` 配置本机 models_path；"
                "中文用户名可配合 `scripts/ollama.local.ps1` + restart_ollama.ps1。"
            )
        if st.session_state["is_admin"]:
            st.success("当前为管理员模式")
            if st.button("退出管理员模式"):
                logout_admin()
                st.rerun()
        else:
            password = st.text_input("管理员密码", type="password")
            if st.button("登录管理员"):
                if login_admin(password):
                    st.session_state["is_admin"] = True
                    st.rerun()
                else:
                    st.error("密码错误。")

    user_ui.render_user_panel()

    if st.session_state["is_admin"]:
        st.divider()
        admin_ui.render_admin_panel()


if __name__ == "__main__":
    main()
