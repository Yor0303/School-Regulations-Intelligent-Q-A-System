import streamlit as st

from chains import answer_question
from graph_engine import (
    build_rule_graph,
    export_graph_html,
    extract_graph_elements,
    filter_graph_records,
    format_rule_chain,
    get_graph_stats,
    load_graph_data,
    render_graph_html_content,
    search_graph_with_llm,
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
    st.rerun()


def _inject_home_styles() -> None:
    st.markdown(
        """
        <style>
        div[data-testid="stVerticalBlockBorderWrapper"]:has([data-testid="stMarkdownContainer"] .shu-hot-marker) {
            background: #FAFBFC;
            border: 1px solid #E2E8F0 !important;
            border-radius: 12px !important;
            padding: 0.5rem 0.75rem 0.75rem 0.75rem !important;
            margin-bottom: 0.75rem;
            box-shadow: none;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has([data-testid="stMarkdownContainer"] .shu-hot-marker) button[kind="secondary"] {
            background: #FFFFFF !important;
            color: #334155 !important;
            border: 1px solid #E2E8F0 !important;
            border-left: 3px solid #004098 !important;
            border-radius: 8px !important;
            padding: 0.45rem 0.65rem !important;
            min-height: 2.4rem !important;
            height: auto !important;
            font-size: 0.86rem !important;
            font-weight: 500 !important;
            line-height: 1.4 !important;
            white-space: normal !important;
            text-align: left !important;
            box-shadow: none !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has([data-testid="stMarkdownContainer"] .shu-hot-marker) button[kind="secondary"]:hover {
            color: #004098 !important;
            background: #F8FAFC !important;
            border-color: #B8C9E0 !important;
            box-shadow: none !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.shu-chat-marker) {
            background: #FFFFFF;
            border: 1px solid #D8E2F0 !important;
            border-radius: 16px !important;
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_user_panel() -> None:
    _inject_home_styles()

    settings = load_settings()
    if settings.get("bot_name"):
        st.markdown(f"### {settings['bot_name']}")
    if settings.get("bot_avatar"):
        st.image(settings["bot_avatar"], width=96)

    if "conversation_memory" not in st.session_state:
        st.session_state["conversation_memory"] = ConversationMemory()

    st.caption(
        "知识库涵盖：学籍管理 · 考试管理 · 宿舍管理 · 奖助学金 · 违纪处分"
    )

    tabs = st.tabs(["智能问答", "违规判定", "规则图谱"])

    with tabs[0]:
        history = st.session_state["conversation_memory"].get_history()
        turns = _build_conversation_turns(history)

        with st.container(height=460, border=True, autoscroll=True):
            st.markdown('<span class="shu-chat-marker"></span>', unsafe_allow_html=True)
            if not turns:
                st.markdown(
                    "<p style='color:#94A3B8;text-align:center;margin:4rem 0 0;'>"
                    "在下方输入框或热门咨询中提问，对话会显示在这里</p>",
                    unsafe_allow_html=True,
                )
            for turn in turns:
                for message in turn:
                    with st.chat_message(message["role"]):
                        st.write(message["content"])

        st.caption("热门咨询")
        with st.container(border=True):
            st.markdown('<span class="shu-hot-marker"></span>', unsafe_allow_html=True)
            cols = st.columns(3, gap="small")
            for index, question in enumerate(EXAMPLE_QUESTIONS):
                with cols[index % 3]:
                    if st.button(
                        question,
                        key=f"example_question_{index}",
                        use_container_width=True,
                        type="secondary",
                    ):
                        _submit_question(question)

        query = st.chat_input("请输入学校制度相关问题")
        if query:
            _submit_question(query)

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

        records = load_graph_data()
        stats = get_graph_stats(records)
        col1, col2, col3 = st.columns(3)
        col1.metric("节点数", stats["nodes"])
        col2.metric("关系数", stats["edges"])
        col3.metric("规则类别", stats["categories"])

        # --- Interactive graph visualization ---
        graph_data = extract_graph_elements(records)
        graph = build_rule_graph(graph_data)
        graph_html = render_graph_html_content(graph, height="520px")

        with st.expander("交互式图谱", expanded=True):
            st.components.v1.html(graph_html, height=540, scrolling=True)

        # --- Search ---
        st.markdown("#### 规则检索")
        search_mode = st.radio(
            "检索模式",
            ["关键词匹配", "LLM 语义推理"],
            horizontal=True,
            label_visibility="collapsed",
        )

        keyword = st.text_input(
            "搜索规则主题",
            placeholder="例如：缓考怎么申请、作弊会有什么后果、宿舍违规怎么处理",
            key="graph_search_input",
        )

        if keyword:
            if search_mode == "LLM 语义推理":
                with st.spinner("LLM 正在分析知识图谱..."):
                    llm_results = search_graph_with_llm(keyword, records)
                if llm_results:
                    st.caption(f"LLM 推理结果（共 {len(llm_results)} 条）")
                    for idx, item in enumerate(llm_results):
                        chain_text = item.get("chain", "")
                        with st.container(border=True):
                            st.markdown(
                                f"**{item.get('source', '?')}**"
                                f" → **{item.get('target', '?')}**"
                                f"（{item.get('relation', '')}）"
                            )
                            if chain_text:
                                st.caption(f"推理链：{chain_text}")
                            st.caption(f"关联说明：{item.get('relevance', '')}")
                else:
                    st.info("LLM 未找到明确关联的规则链，请尝试其他关键词。")

            # Always show keyword-matched records below
            related_records = filter_graph_records(keyword, records)
            if related_records:
                st.markdown("##### 规则详情")
                for item in related_records:
                    with st.expander(format_rule_chain(item), expanded=False):
                        st.write(item.get("evidence", "暂无依据说明。"))
                        st.caption(f"类别：{item.get('category', '未分类')}")
                        st.caption(f"来源：{item.get('source_label', '暂无来源')}")
            elif search_mode == "关键词匹配":
                st.info("未找到相关规则链。")
