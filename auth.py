import streamlit as st

from settings_manager import load_settings


def login_admin(password: str) -> bool:
    settings = load_settings()
    return password == settings.get("admin_password", "admin123")


def ensure_auth_state() -> None:
    if "is_admin" not in st.session_state:
        st.session_state["is_admin"] = False


def logout_admin() -> None:
    st.session_state["is_admin"] = False
