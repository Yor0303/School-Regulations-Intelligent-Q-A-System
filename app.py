# -*- encoding: utf-8 -*-
import streamlit as st
import base64

from admin_ui import render_admin_panel
from auth import ensure_auth_state, login_admin, logout_admin
from settings_manager import load_settings
from user_ui import render_user_panel
from pathlib import Path

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
    /* 仅针对主内容区的按钮（不包含侧边栏） */
    section.main > div > div > div > div > div > div > div > button {
        background-color: #004098;
        color: white;
        border-radius: 40px;
        border: none;
        transition: 0.2s;
    }
    section.main > div > div > div > div > div > div > div > button:hover {
        background-color: #002766;
        transform: translateY(-1px);
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

    render_user_panel()

    if st.session_state["is_admin"]:
        st.divider()
        render_admin_panel()


if __name__ == "__main__":
    main()
