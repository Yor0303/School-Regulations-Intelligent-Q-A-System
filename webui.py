# -*- encoding: utf-8 -*-
# @Author: SWHL
# @Contact: liekkaskono@163.com
import importlib
import shutil
import time
import uuid
from pathlib import Path
from typing import Dict

import numpy as np
import streamlit as st

from rapid_rag.encoder import EncodeText, ErnieEncodeText
from rapid_rag.file_loader import FileLoader
from rapid_rag.utils import get_timestamp, logger, make_prompt, mkdir, read_yaml
from rapid_rag.vector_utils import DBUtils

config = read_yaml("rapid_rag/config.yaml")

st.set_page_config(
    page_title=config.get("title"),
    page_icon=":robot:",
)


def init_ui_parameters():
    st.session_state["params"] = {}
    param = config.get("Parameter")

    st.sidebar.markdown("### 🛶 参数设置")

    param_max_length = param.get("max_length")
    max_length = st.sidebar.slider(
        "max_length",
        min_value=param_max_length.get("min_value"),
        max_value=param_max_length.get("max_value"),
        value=param_max_length.get("default"),
        step=param_max_length.get("step"),
        help=param_max_length.get("tip"),
    )
    st.session_state["params"]["max_length"] = max_length

    param_top = param.get("top_p")
    top_p = st.sidebar.slider(
        "top_p",
        min_value=param_top.get("min_value"),
        max_value=param_top.get("max_value"),
        value=param_top.get("default"),
        step=param_top.get("step"),
        help=param_top.get("tip"),
    )
    st.session_state["params"]["top_p"] = top_p

    param_temp = param.get("temperature")
    temperature = st.sidebar.slider(
        "temperature",
        min_value=param_temp.get("min_value"),
        max_value=param_temp.get("max_value"),
        value=param_temp.get("default"),
        step=param_temp.get("step"),
        help=param_temp.get("tip"),
    )
    st.session_state["params"]["temperature"] = temperature


def init_ui_db():
    st.sidebar.markdown("### 🧻 知识库")
    uploaded_files = st.sidebar.file_uploader(
        "default",
        accept_multiple_files=True,
        label_visibility="hidden",
        help="支持多个文件的选取",
    )

    upload_dir = config.get("upload_dir")
    btn_upload = st.sidebar.button("上传文档并加载")
    if btn_upload:
        time_stamp = get_timestamp()
        doc_dir = Path(upload_dir) / time_stamp

        tips("正在上传文件到平台中...", icon="⏳")
        for file_data in uploaded_files:
            bytes_data = file_data.getvalue()

            mkdir(doc_dir)
            save_path = doc_dir / file_data.name
            with open(save_path, "wb") as f:
                f.write(bytes_data)
        tips("上传完毕！")

        with st.spinner(f"正在从{doc_dir}提取内容...."):
            all_doc_contents = file_loader(doc_dir)

        pro_text = "提取语义向量..."
        batch_size = config.get("encoder_batch_size", 16)
        uid = str(uuid.uuid1())
        st.session_state["connect_id"] = uid
        for file_path, one_doc_contents in all_doc_contents.items():
            my_bar = st.sidebar.progress(0, text=pro_text)
            content_nums = len(one_doc_contents)
            all_embeddings = []
            for i in range(0, content_nums, batch_size):
                start_idx = i
                end_idx = start_idx + batch_size
                end_idx = content_nums if end_idx > content_nums else end_idx

                cur_contents = one_doc_contents[start_idx:end_idx]
                if not cur_contents:
                    continue

                embeddings = embedding_extract(cur_contents)
                if embeddings is None or embeddings.size == 0:
                    continue

                all_embeddings.append(embeddings)
                my_bar.progress(
                    end_idx / content_nums,
                    f"Extract {file_path} datas: [{end_idx}/{content_nums}]",
                )
            my_bar.empty()

            if all_embeddings:
                all_embeddings = np.vstack(all_embeddings)
                db_tools.insert(file_path, all_embeddings, one_doc_contents, uid)
            else:
                tips(f"从{file_path}提取向量为空。")

        shutil.rmtree(doc_dir.resolve())
        tips("现在可以提问问题了哈！")

    clear_db_btn = st.sidebar.button("清空知识库")
    if clear_db_btn:
        db_tools.clear_db()
        tips("知识库已经被清空！")

    if "connect_id" in st.session_state:
        had_files = db_tools.get_files(uid=st.session_state.connect_id)
    else:
        had_files = db_tools.get_files()

    st.session_state.had_file_nums = len(had_files) if had_files else 0
    if had_files:
        st.sidebar.markdown("已有文档:")
        st.sidebar.markdown("\n".join([f" - {v}" for v in had_files]))


@st.cache_resource
def init_encoder(encoder_name: str, **kwargs):
    if "ERNIEBot" in encoder_name:
        return ErnieEncodeText(**kwargs)
    return EncodeText(**kwargs)


def predict(
    text,
    search_res,
    model,
    custom_prompt=None,
):
    for file, content in search_res.items():
        content = "\n".join(content)
        one_context = f"**从《{file}》** 检索到相关内容： \n{content}"
        bot_print(one_context, avatar="📄")

        logger.info(f"Context:\n{one_context}\n")

    context = "\n".join(sum(search_res.values(), []))
    response, elapse = get_model_response(text, context, custom_prompt, model)

    print_res = f"**推理耗时:{elapse:.5f}s**"
    bot_print(print_res, avatar="📄")
    bot_print(response)


def predict_only_model(text, model):
    params_dict = st.session_state["params"]
    response = model(text, history=None, **params_dict)
    bot_print(response)


def bot_print(content, avatar: str = "🤖"):
    with st.chat_message("assistant", avatar=avatar):
        message_placeholder = st.empty()
        full_response = ""
        for chunk in content.split():
            full_response += chunk + " "
            time.sleep(0.05)
            message_placeholder.markdown(full_response + "▌")
        message_placeholder.markdown(full_response)


def get_model_response(text, context, custom_prompt, model):
    params_dict = st.session_state["params"]

    s_model = time.perf_counter()
    prompt_msg = make_prompt(text, context, custom_prompt)
    logger.info(f"Final prompt: \n{prompt_msg}\n")

    response = model(prompt_msg, history=None, **params_dict)
    elapse = time.perf_counter() - s_model

    logger.info(f"Reponse of LLM: \n{response}\n")
    if not response:
        response = "抱歉，我并不能正确回答该问题。"
    return response, elapse


def tips(txt: str, wait_time: int = 2, icon: str = "🎉"):
    st.toast(txt, icon=icon)
    time.sleep(wait_time)


if __name__ == "__main__":
    title = config.get("title")
    version = config.get("version", "0.0.1")
    st.markdown(
        f"<h3 style='text-align: center;'>{title} v{version}</h3><br/>",
        unsafe_allow_html=True,
    )

    init_ui_parameters()

    file_loader = FileLoader()

    db_path = config.get("vector_db_path")
    db_tools = DBUtils(db_path)

    llm_module = importlib.import_module("rapid_rag.llm")
    llm_params: Dict[str, Dict] = config.get("LLM_API")

    menu_col1, menu_col2, menu_col3 = st.columns([1, 1, 1])
    select_model = menu_col1.selectbox("🎨LLM:", llm_params.keys())
    if "ERNIEBot" in select_model:
        with st.expander("LLM ErnieBot", expanded=True):
            opt_col1, opt_col2 = st.columns([1, 1])
            api_type = opt_col1.selectbox(
                "API Type(必选)",
                options=["aistudio", "qianfan", "yinian"],
                help="提供对话能力的后端平台",
            )
            access_token = opt_col2.text_input(
                "Access Token(必填) &nbsp;[如何获得？](https://github.com/PaddlePaddle/ERNIE-Bot-SDK/blob/develop/docs/authentication.md)",
                "",
                help="用于访问后端平台的access token（参考使用说明获取），如果设置了AK、SK则无需设置此参数",
            )
            llm_params[select_model]["api_type"] = api_type

            if access_token:
                llm_params[select_model]["access_token"] = access_token

    MODEL_OPTIONS = {
        name: getattr(llm_module, name)(**params) for name, params in llm_params.items()
    }

    encoder_params = config.get("Encoder")
    select_encoder = menu_col2.selectbox("🧬提取向量模型:", encoder_params.keys())
    if "ERNIEBot" in select_encoder:
        with st.expander("提取语义向量 ErnieBot", expanded=True):
            opt_col1, opt_col2 = st.columns([1, 1])
            extract_api_type = opt_col1.selectbox(
                "API Type(必选)",
                options=["aistudio", "qianfan", "yinian"],
                help="提供对话能力的后端平台",
                key="Extract_type",
            )
            encoder_params[select_encoder]["api_type"] = extract_api_type

            extract_access_token = opt_col2.text_input(
                "Access Token(必填) &nbsp;[如何获得？](https://github.com/PaddlePaddle/ERNIE-Bot-SDK/blob/develop/docs/authentication.md)",
                "",
                help="用于访问后端平台的access token（参考使用说明获取），如果设置了AK、SK则无需设置此参数",
                key="Extract_token",
            )
            if extract_access_token:
                encoder_params[select_encoder]["access_token"] = extract_access_token

    embedding_extract = init_encoder(select_encoder, **encoder_params[select_encoder])

    TOP_OPTIONS = [5, 10, 15]
    search_top = menu_col3.selectbox("🔍搜索 Top_K:", TOP_OPTIONS)

    init_ui_db()

    with st.expander("💡Prompt", expanded=False):
        text_area = st.empty()
        input_prompt = text_area.text_area(
            label="Input",
            max_chars=500,
            height=200,
            label_visibility="hidden",
            value=config.get("DEFAULT_PROMPT"),
            key="input_prompt",
        )

    input_txt = st.chat_input("问点啥吧！")
    if input_txt:
        with st.chat_message("user", avatar="😀"):
            st.markdown(input_txt)

        llm = MODEL_OPTIONS[select_model]

        if not input_prompt:
            input_prompt = config.get("DEFAULT_PROMPT")

        query_embedding = embedding_extract(input_txt)
        with st.spinner("正在搜索相关文档..."):
            uid = st.session_state.get("connect_id", None)
            search_res, search_elapse = db_tools.search_local(
                query_embedding, top_k=search_top, uid=uid
            )

        if search_res is None:
            bot_print("从知识库中抽取结果为空，直接采用LLM的本身能力回答。", avatar="📄")
            predict_only_model(input_txt, llm)
        else:
            logger.info(f"使用 {type(llm).__name__}")

            res_cxt = f"**Top{search_top}\n(得分从高到低，耗时:{search_elapse:.5f}s):** \n"
            bot_print(res_cxt, avatar="📄")

            predict(
                input_txt,
                search_res,
                llm,
                input_prompt,
            )
