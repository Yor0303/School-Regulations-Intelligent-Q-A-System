import streamlit as st

from chains import answer_question
from graph_engine import export_graph_html
from knowledge_base.memory import ConversationMemory
from knowledge_base.violation_checker import judge_violation
from settings_manager import load_settings


def render_user_panel() -> None:
    settings = load_settings()
    st.title(settings.get("site_title", "School Rules QA System"))
    st.caption(settings.get("welcome_message", ""))
    if settings.get("bot_name"):
        st.markdown(f"**{settings['bot_name']}**")
    if settings.get("bot_avatar"):
        st.image(settings["bot_avatar"], width=96)

    if "conversation_memory" not in st.session_state:
        st.session_state["conversation_memory"] = ConversationMemory()

    tabs = st.tabs(["智能问答", "违规判定", "规则图谱"])

    with tabs[0]:
        history = st.session_state["conversation_memory"].get_history()
        for message in history:
            with st.chat_message(message["role"]):
                st.write(message["content"])

        query = st.chat_input("请输入学校制度相关问题")
        if query:
            st.chat_message("user").write(query)
            result = answer_question(
                query, memory=st.session_state["conversation_memory"]
            )
            st.chat_message("assistant").write(result["answer"])

    with tabs[1]:
        description = st.text_area(
            "请输入需要判断的行为描述",
            height=120,
        )
        if st.button("开始判定"):
            result = judge_violation(description)
            st.write(f"结论：{result['conclusion']}")
            st.write(f"依据：{result['basis']}")
            if result["sources"]:
                st.markdown("来源：")
                for item in result["sources"]:
                    st.write(f"- {item.get('source_label', item.get('file_name', ''))}")

    with tabs[2]:
        graph_path = export_graph_html()
        st.markdown(f"规则图谱文件：`{graph_path}`")
