# -*- encoding: utf-8 -*-
import streamlit as st

from document_service import analyze_document_request, generate_document_bytes
from document_service.registry import get_disclaimer, list_type_options


DOC_EXAMPLES = [
    "我因病想申请休学一学期",
    "期末考试想申请缓考，因为住院了",
    "下周三天有事不能上课，想请假",
    "申请某门课的免考",
]


def _set_doc_example(example: str) -> None:
    st.session_state["doc_user_text"] = example


def _render_reasoning_panel(analysis: dict) -> None:
    """Show symbolic reasoning and regulation excerpts on the page (not in Word)."""
    chain = analysis.get("reasoning_chain") or []
    excerpts = analysis.get("regulation_excerpts", "")
    sources = analysis.get("regulation_sources") or []

    with st.container(border=True):
        st.markdown("#### 符号推理链")
        if chain:
            for step in chain:
                st.markdown(f"- {step}")
        else:
            st.caption("暂无推理记录。")

    with st.container(border=True):
        st.markdown("#### 制度依据摘录")
        if excerpts:
            st.text(excerpts)
        else:
            st.caption("未检索到相关制度原文。")
        if sources:
            st.markdown("**来源文件**")
            for src in sources:
                st.caption(src)


def _collect_form_slots(analysis: dict) -> dict:
    labels = analysis.get("slot_labels") or {}
    all_keys = list(analysis.get("required_slots") or []) + list(
        analysis.get("optional_slots") or []
    )
    slots = {}
    for key in all_keys:
        label = labels.get(key, key)
        widget_key = f"doc_slot_{key}"
        default = (analysis.get("slots") or {}).get(key, "")
        slots[key] = st.session_state.get(widget_key, default)
    return slots


def render_document_panel() -> None:
    st.subheader("办事文书生成")
    st.caption(
        "面向休学、缓考、请假等常见办事事项，对照校规制度辅助填写并生成 Word 文书草稿；"
        "若知识库暂无相关依据，将明确提示无法生成。"
    )

    disclaimer = get_disclaimer()
    if disclaimer:
        st.info(disclaimer)

    if "doc_user_text" not in st.session_state:
        st.session_state["doc_user_text"] = ""
    if "doc_analysis" not in st.session_state:
        st.session_state["doc_analysis"] = None

    type_options = list_type_options()
    type_ids = [t[0] for t in type_options]
    type_labels = {t[0]: t[1] for t in type_options}

    col_a, col_b = st.columns([2, 1])
    with col_a:
        user_text = st.text_area(
            "描述您的办事需求",
            height=100,
            placeholder="例如：我因病需要休学半年，或：想申请期末考试缓考…",
            key="doc_user_text",
        )
    with col_b:
        manual_type = st.selectbox(
            "或直接选择文书类型（可选）",
            options=["自动识别"] + type_ids,
            format_func=lambda x: "自动识别" if x == "自动识别" else type_labels.get(x, x),
            key="doc_manual_type",
        )

    st.caption("快捷示例")
    ex_cols = st.columns(2)
    for idx, example in enumerate(DOC_EXAMPLES):
        with ex_cols[idx % 2]:
            st.button(
                example,
                key=f"doc_example_{idx}",
                use_container_width=True,
                on_click=_set_doc_example,
                args=(example,),
            )

    if st.button("分析需求并校验制度依据", type="primary", key="doc_analyze_btn"):
        forced = None
        if st.session_state.get("doc_manual_type") != "自动识别":
            forced = st.session_state["doc_manual_type"]
        with st.spinner("正在识别文书类型并检索制度依据…"):
            analysis = analyze_document_request(
                user_text or "",
                form_slots={},
                forced_type_id=forced,
            )
            st.session_state["doc_analysis"] = analysis
        st.rerun()

    analysis = st.session_state.get("doc_analysis")
    if not analysis:
        return

    status = analysis.get("status")
    st.markdown(f"**识别结果：** {analysis.get('document_title', '未识别')}")
    if analysis.get("brief_summary"):
        st.caption(f"诉求摘要：{analysis['brief_summary']}")

    if status == "unsupported":
        st.error(analysis.get("message", "无法生成文书。"))
        _render_reasoning_panel(analysis)
        return

    labels = analysis.get("slot_labels") or {}
    required = analysis.get("required_slots") or []
    optional = analysis.get("optional_slots") or []

    with st.form("doc_slot_form", clear_on_submit=False):
        st.markdown("#### 填写 / 补充申请信息")
        for key in required:
            label = labels.get(key, key)
            st.text_input(
                f"{label} *",
                value=(analysis.get("slots") or {}).get(key, ""),
                key=f"doc_slot_{key}",
            )
        for key in optional:
            label = labels.get(key, key)
            st.text_input(
                label,
                value=(analysis.get("slots") or {}).get(key, ""),
                key=f"doc_slot_{key}",
            )
        submitted = st.form_submit_button("更新校验并准备生成")

    if submitted:
        form_slots = _collect_form_slots(analysis)
        forced = analysis.get("document_type_id")
        with st.spinner("正在校验…"):
            analysis = analyze_document_request(
                st.session_state.get("doc_user_text", ""),
                form_slots=form_slots,
                forced_type_id=forced,
            )
            st.session_state["doc_analysis"] = analysis
        st.rerun()

    analysis = st.session_state.get("doc_analysis")

    _render_reasoning_panel(analysis)

    if analysis.get("default_attachments"):
        st.markdown("**建议材料：**")
        for item in analysis.get("default_attachments", []):
            st.write(f"- {item}")

    if analysis.get("status") == "incomplete":
        st.warning(analysis.get("message", "请补充必填项。"))
    elif analysis.get("status") == "ready":
        st.success(analysis.get("message", "可生成文书。"))
        if st.button("生成 Word 文书草稿", type="primary", key="doc_generate_btn"):
            result = generate_document_bytes(analysis)
            if result:
                st.session_state["doc_download"] = result
                st.rerun()
            else:
                st.error("生成失败，请重新分析。")

    download = st.session_state.get("doc_download")
    if download and download.get("bytes"):
        st.download_button(
            label=f"下载：{download.get('filename', '文书.docx')}",
            data=download["bytes"],
            file_name=download.get("filename", "文书.docx"),
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            key="doc_download_btn",
        )
