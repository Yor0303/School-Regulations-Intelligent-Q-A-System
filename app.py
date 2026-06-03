# -*- encoding: utf-8 -*-
import streamlit as st

from admin_ui import render_admin_panel
from auth import ensure_auth_state, login_admin, logout_admin
from settings_manager import load_settings
from user_ui import render_user_panel


def main():
    settings = load_settings()
    st.set_page_config(page_title=settings.get("site_title", "School Rules QA System"))
    ensure_auth_state()

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
