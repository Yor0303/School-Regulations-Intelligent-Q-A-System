import streamlit as st

from chains import answer_question
from graph_engine import export_graph_html
from knowledge_base.memory import ConversationMemory
from knowledge_base.violation_checker import judge_violation
from settings_manager import load_settings


def render_user_panel() -> None:
    settings = load_settings()
    #st.title(settings.get("site_title", "School Rules QA System"))
    #st.caption(settings.get("welcome_message", ""))
    if settings.get("bot_name"):
        st.markdown(f"**{settings['bot_name']}**")
    if settings.get("bot_avatar"):
        st.image(settings["bot_avatar"], width=96)

    if "conversation_memory" not in st.session_state:
        st.session_state["conversation_memory"] = ConversationMemory()

    st.subheader("校园制度分类")
    col1,col2,col3,col4,col5 = st.columns(5)
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
    col1,col2,col3 = st.columns(3)

    with col1:
        st.info("绩点不足怎么办")
        st.info("缓考申请流程")
    with col2:
        st.info("考试作弊怎样处理")
        st.info("宿舍违规用电会受处分吗")
    with col3:
        st.info("获得奖学金需要绩点排名多少")
        st.info("受到警告处分后多久可以解除？")

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
            # ===== 前端过滤英文模板 =====
            answer_text = result["answer"]
            lines = answer_text.split("\n")
            filtered_lines = [
                line for line in lines
                if "No clear supporting rule" not in line
                and "If the documents are not sufficient" not in line
            ]
            clean_answer = "\n".join(filtered_lines)
            # ===============================
            st.chat_message("assistant").write(result["answer"])

    with tabs[1]:
        st.warning("""
        案例示例：考试时使用手机查询答案、连续旷课三次、宿舍使用违规电器
        、论文存在抄袭行为
        """)

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
        #st.markdown(f"规则图谱文件：`{graph_path}`")
        st.subheader("校园规则知识图谱")
        st.markdown("""
        知识图谱展示学生、行为、制度、
        处分结果之间的关联关系，
        帮助理解校园规则体系。
        """)
        st.success("图谱已生成")
        st.code(graph_path)