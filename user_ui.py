import streamlit as st

from chains import answer_question
from graph_engine import (
    export_graph_html,
    filter_graph_records,
    format_rule_chain,
    get_graph_stats,
)
from knowledge_base.memory import ConversationMemory
from knowledge_base.violation_checker import judge_violation
from settings_manager import load_settings


EXAMPLE_QUESTIONS = [
    "绩点不足怎么办？",
    "缓考怎么申请？",
    "考试作弊会怎样处理？",
    "宿舍违规用电会受处分吗？",
    "获得奖学金需要绩点排名多少？",
    "受到警告处分后多久可以解除？",
]


def _build_conversation_turns(history):
    turns = []
    current_turn = []
    for message in history:
        if message["role"] == "user":
            if current_turn:
                turns.append(current_turn)
            current_turn = [message]
        else:
            current_turn.append(message)
            turns.append(current_turn)
            current_turn = []

    if current_turn:
        turns.append(current_turn)
    return list(reversed(turns))


def _submit_question(query: str) -> None:
    with st.spinner("正在检索相关制度并生成回答..."):
        answer_question(query, memory=st.session_state["conversation_memory"])


def render_user_panel() -> None:
    settings = load_settings()
    if settings.get("bot_name"):
        st.markdown(f"**{settings['bot_name']}**")
    if settings.get("bot_avatar"):
        st.image(settings["bot_avatar"], width=96)

    if "conversation_memory" not in st.session_state:
        st.session_state["conversation_memory"] = ConversationMemory()

    st.subheader("校园制度分类")
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.info("学籍管理")
    with col2:
        st.info("考试管理")
    with col3:
        st.info("宿舍管理")
    with col4:
        st.info("奖助学金")
    with col5:
        st.info("违纪处分")

    st.subheader("热门咨询")
    cols = st.columns(3)
    for index, question in enumerate(EXAMPLE_QUESTIONS):
        with cols[index % 3]:
            if st.button(question, key=f"example_question_{index}", use_container_width=True):
                _submit_question(question)

    tabs = st.tabs(["智能问答", "违规判定", "规则图谱"])

    with tabs[0]:
        query = st.chat_input("请输入学校制度相关问题")
        if query:
            _submit_question(query)

        history = st.session_state["conversation_memory"].get_history()
        turns = _build_conversation_turns(history)
        for turn in turns:
            for message in turn:
                with st.chat_message(message["role"]):
                    st.write(message["content"])

    with tabs[1]:
        st.warning(
            "案例示例：考试时使用手机查询答案、连续旷课三次、宿舍使用违规电器、论文存在抄袭行为。"
        )

        description = st.text_area(
            "请输入需要判定的行为描述",
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
        st.subheader("校园规则知识图谱")
        stats = get_graph_stats()
        col1, col2, col3 = st.columns(3)
        col1.metric("节点数", stats["nodes"])
        col2.metric("关系数", stats["edges"])
        col3.metric("规则类别", stats["categories"])

        keyword = st.text_input(
            "搜索规则主题",
            placeholder="例如：缓考、绩点、考试违纪、宿舍用电",
        )
        related_records = filter_graph_records(keyword)
        graph_path = export_graph_html(keyword=keyword)

        st.markdown("#### 相关规则链")
        if related_records:
            for item in related_records:
                with st.expander(format_rule_chain(item), expanded=False):
                    st.write(item.get("evidence", "暂无依据说明。"))
                    st.caption(f"类别：{item.get('category', '未分类')}")
                    st.caption(f"来源：{item.get('source_label', '暂无来源')}")
        else:
            st.info("未找到相关规则链。")

        st.markdown("#### 图谱文件")
        st.code(graph_path)
