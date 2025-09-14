import os
import json
import sys
import time

import streamlit as st
from dotenv import load_dotenv
from openai import AzureOpenAI
from streamlit_ace import st_ace

# --- ローカルモジュールのインポート ---
from codex_chat import config
from codex_chat import utils

# --- ヘルパー関数 (アプリケーション固有) ---

def load_history():
    """
    アップロードされたJSONから会話履歴とCanvasコードを読み込む
    """
    uploaded_file = st.session_state['history_uploader']
    if not uploaded_file:
        return
    try:
        loaded_data = json.load(uploaded_file)
        if isinstance(loaded_data, dict) and "messages" in loaded_data:
            st.session_state['messages'] = loaded_data["messages"]
            if "python_canvases" in loaded_data:
                st.session_state['python_canvases'] = loaded_data["python_canvases"]
            
            # --- ★★★★★ 変更点 (ここから) ★★★★★ ---
            if "multi_code_enabled" in loaded_data:
                st.session_state['multi_code_enabled'] = loaded_data["multi_code_enabled"]
            # --- ★★★★★ 変更点 (ここまで) ★★★★★ ---

            if "selected_env_file" in loaded_data:
                env_files = utils.find_env_files()
                if loaded_data["selected_env_file"] in env_files:
                    st.session_state['selected_env_file'] = loaded_data["selected_env_file"]
                    st.toast(f"モデル設定 `{os.path.basename(st.session_state['selected_env_file'])}` を復元しました。")
                else:
                    st.warning(f"履歴ファイルのモデル設定 `{os.path.basename(loaded_data['selected_env_file'])}` が見つかりません。デフォルトのモデルで再開します。")

            st.success(config.UITexts.HISTORY_LOADED_SUCCESS)

        elif isinstance(loaded_data, list): # 後方互換性
            st.session_state['messages'] = loaded_data
            st.warning(config.UITexts.OLD_HISTORY_FORMAT_WARNING)
        else:
            st.error(config.UITexts.JSON_FORMAT_ERROR)
            return

        st.session_state['system_role_defined'] = True
        st.session_state['total_usage'] = config.SESSION_STATE_DEFAULTS["total_usage"].copy()
        st.session_state['last_usage_info'] = None
        st.session_state['canvas_key_counter'] += 1

    except Exception as e:
        st.error(config.UITexts.JSON_LOAD_ERROR.format(e=e))


# --- Streamlit アプリケーション ---

def run_chatbot_app():
    st.set_page_config(page_title=config.UITexts.APP_TITLE, layout="wide")
    st.title(config.UITexts.APP_TITLE)
    
    PROMPTS = utils.load_prompts()
    
    env_files = utils.find_env_files()
    if not env_files:
        st.error("`env` ディレクトリに `.env` ファイルが見つかりません。アプリケーションを続行できません。")
        st.stop()

    for key, value in config.SESSION_STATE_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = value.copy() if isinstance(value, (dict, list)) else value
    
    # --- ボタン/ウィジェット操作のコールバック関数 ---
    def handle_clear(canvas_index):
        """指定されたCanvasの内容をクリアする"""
        if 0 <= canvas_index < len(st.session_state['python_canvases']):
            st.session_state['python_canvases'][canvas_index] = config.ACE_EDITOR_DEFAULT_CODE

    def handle_review(canvas_index, is_multi_mode):
        """指定されたCanvasのレビュープロンプトを生成する"""
        if is_multi_mode:
            prompt = config.UITexts.REVIEW_PROMPT_MULTI.format(i=canvas_index + 1)
        else:
            prompt = config.UITexts.REVIEW_PROMPT_SINGLE
        st.session_state['messages'].append({"role": "user", "content": prompt})
        st.session_state['is_generating'] = True

    def handle_validation(canvas_index):
        """指定されたCanvasのpylint検証を実行する"""
        if 0 <= canvas_index < len(st.session_state['python_canvases']):
            utils.run_pylint_validation(st.session_state['python_canvases'][canvas_index], canvas_index, PROMPTS)

    def handle_file_upload(canvas_index, uploader_key):
        """ファイルアップロードを処理し、Canvasに内容を反映するコールバック"""
        uploaded_file = st.session_state.get(uploader_key)
        if uploaded_file:
            try:
                file_content = uploaded_file.getvalue().decode("utf-8")
                st.session_state['python_canvases'][canvas_index] = file_content
                # ACEエディタを強制的に再描画させるため、キーを更新
                st.session_state['canvas_key_counter'] += 1
            except Exception as e:
                st.error(f"ファイルの読み込みに失敗しました: {e}")

    # --- サイドバー ---
    with st.sidebar:
        st.header("モデル設定")

        def on_env_change():
            for key, value in config.SESSION_STATE_DEFAULTS.items():
                 st.session_state[key] = value.copy() if isinstance(value, (dict, list)) else value

        selected_env = st.selectbox(
            label="使用するAIモデル (.env) を選択",
            options=env_files,
            format_func=lambda x: os.path.basename(x),
            key='selected_env_file',
            on_change=on_env_change,
            help="モデル設定を切り替えると、現在の会話はリセットされます。会話開始後はロックされます。",
            disabled=st.session_state['system_role_defined'] or st.session_state['is_generating']
        )

        st.header(config.UITexts.SIDEBAR_HEADER)
        if st.button(config.UITexts.RESET_BUTTON_LABEL, use_container_width=True, disabled=st.session_state['is_generating']):
            for key, value in config.SESSION_STATE_DEFAULTS.items():
                st.session_state[key] = value.copy() if isinstance(value, (dict, list)) else value
            st.rerun()

        st.info(config.UITexts.CODEX_MINI_INFO)

        st.subheader(config.UITexts.HISTORY_SUBHEADER)
        if not st.session_state['is_generating'] and st.session_state['messages']:
            # --- ★★★★★ 変更点 (ここから) ★★★★★ ---
            history_data = {
                "messages": st.session_state['messages'],
                "python_canvases": st.session_state['python_canvases'],
                "selected_env_file": st.session_state.get('selected_env_file'),
                "multi_code_enabled": st.session_state['multi_code_enabled']
            }
            # --- ★★★★★ 変更点 (ここまで) ★★★★★ ---
            st.download_button(
                label=config.UITexts.DOWNLOAD_HISTORY_BUTTON,
                data=json.dumps(history_data, ensure_ascii=False, indent=2),
                file_name=f"chat_session_{int(time.time())}.json",
                mime="application/json",
                use_container_width=True,
                disabled=st.session_state['is_generating']
            )

        st.file_uploader(
            label=config.UITexts.UPLOAD_HISTORY_LABEL, type="json", key="history_uploader",
            on_change=load_history, disabled=st.session_state['is_generating']
        )
        
        st.subheader(config.UITexts.EDITOR_SUBHEADER)
        
        multi_code_enabled_before = st.session_state['multi_code_enabled']
        st.session_state['multi_code_enabled'] = st.checkbox(config.UITexts.MULTI_CODE_CHECKBOX, value=st.session_state['multi_code_enabled'], disabled=st.session_state['is_generating'])
        if multi_code_enabled_before != st.session_state['multi_code_enabled']:
            st.rerun()

        if st.session_state['multi_code_enabled']:
            if len(st.session_state['python_canvases']) < config.MAX_CANVASES and st.button(config.UITexts.ADD_CANVAS_BUTTON, use_container_width=True, disabled=st.session_state['is_generating']):
                st.session_state['python_canvases'].append(config.ACE_EDITOR_DEFAULT_CODE)
                st.rerun()
            
            for i, content in enumerate(st.session_state['python_canvases']):
                st.write(f"**Canvas-{i + 1}**")
                updated_content = st_ace(value=content, key=f"ace_{i}_{st.session_state['canvas_key_counter']}", **config.ACE_EDITOR_SETTINGS, auto_update=True)
                if updated_content != content:
                    st.session_state['python_canvases'][i] = updated_content
                    st.rerun()
                
                c1, c2, c3 = st.columns(3)
                c1.button(config.UITexts.CLEAR_BUTTON, key=f"clear_{i}", use_container_width=True, on_click=handle_clear, args=(i,), disabled=st.session_state['is_generating'])
                c2.button(config.UITexts.REVIEW_BUTTON, key=f"review_{i}", use_container_width=True, on_click=handle_review, args=(i, True), disabled=st.session_state['is_generating'])
                c3.button(config.UITexts.VALIDATE_BUTTON, key=f"validate_{i}", use_container_width=True, help=config.UITexts.VALIDATE_BUTTON_HELP.format(i=i + 1), on_click=handle_validation, args=(i,), disabled=st.session_state['is_generating'])

                uploader_key = f"uploader_{i}_{st.session_state['canvas_key_counter']}"
                st.file_uploader(
                    f"Canvas-{i+1} にファイルを読み込む",
                    type=['txt', 'csv', 'py', 'json', 'yaml'],
                    key=uploader_key,
                    on_change=handle_file_upload,
                    args=(i, uploader_key),
                    disabled=st.session_state['is_generating']
                )

                st.divider()

        else: # シングルコードモード
            if len(st.session_state['python_canvases']) > 1:
                st.session_state['python_canvases'] = [st.session_state['python_canvases'][0]]
            
            updated_content = st_ace(value=st.session_state['python_canvases'][0], key=f"ace_single_{st.session_state['canvas_key_counter']}", **config.ACE_EDITOR_SETTINGS, auto_update=True)
            if updated_content != st.session_state['python_canvases'][0]:
                st.session_state['python_canvases'][0] = updated_content
                st.rerun()

            c1, c2, c3 = st.columns(3)
            c1.button(config.UITexts.CLEAR_BUTTON, key="clear_single", use_container_width=True, on_click=handle_clear, args=(0,), disabled=st.session_state['is_generating'])
            c2.button(config.UITexts.REVIEW_BUTTON, key="review_single", use_container_width=True, on_click=handle_review, args=(0, False), disabled=st.session_state['is_generating'])
            c3.button(config.UITexts.VALIDATE_BUTTON, key="validate_single", use_container_width=True, help=config.UITexts.VALIDATE_BUTTON_HELP.format(i=1), on_click=handle_validation, args=(0,), disabled=st.session_state['is_generating'])
            
            uploader_key_single = f"uploader_single_{st.session_state['canvas_key_counter']}"
            st.file_uploader(
                "Canvasにファイルを読み込む",
                type=['txt', 'csv', 'py', 'json', 'yaml'],
                key=uploader_key_single,
                on_change=handle_file_upload,
                args=(0, uploader_key_single),
                disabled=st.session_state['is_generating']
            )

    # --- .envファイルのロードとクライアント設定 ---
    if 'selected_env_file' not in st.session_state:
        st.session_state['selected_env_file'] = env_files[0]

    load_dotenv(dotenv_path=st.session_state['selected_env_file'], override=True)
    if st.session_state.get('loaded_env') != st.session_state['selected_env_file']:
        st.sidebar.success(f"`{os.path.basename(st.session_state['selected_env_file'])}` を読み込みました。")
        st.session_state['loaded_env'] = st.session_state['selected_env_file']

    env_vars = {
        'api_key': os.getenv(config.AZURE_OPENAI_KEY_NAME),
        'azure_endpoint': os.getenv(config.AZURE_OPENAI_ENDPOINT_NAME),
        'deployment_name': os.getenv(config.AZURE_OPENAI_DEPLOYMENT_NAME),
        'api_version': os.getenv(config.AZURE_OPENAI_API_VERSION_NAME),
        'max_token': os.getenv('MAX_TOKEN'),
    }

    st.caption(f"このチャットは、`Responses API (api-version={env_vars['api_version'] or '未設定'})` を使用して動作します。")

    required_env_keys = { "MAX_TOKEN": "MAX_TOKEN", **{k: getattr(config, f"AZURE_OPENAI_{k}_NAME") for k in ["KEY", "ENDPOINT", "DEPLOYMENT", "API_VERSION"]} }
    missing_vars = [key for key, name in required_env_keys.items() if not os.getenv(name)]
    if missing_vars:
        st.error(f"選択された.envファイル `{os.path.basename(st.session_state['selected_env_file'])}` に必要な環境変数が設定されていません: {', '.join(missing_vars)}")
        st.stop()

    try:
        client = AzureOpenAI(api_key=env_vars['api_key'], azure_endpoint=env_vars['azure_endpoint'], api_version=env_vars['api_version'])
    except Exception as e:
        st.error(config.UITexts.CLIENT_INIT_ERROR.format(e=e))
        st.stop()

    # --- メインコンテンツ ---
    if not st.session_state['system_role_defined']:
        st.subheader(config.UITexts.SYSTEM_PROMPT_HEADER)
        system_prompt_input = st.text_area(config.UITexts.SYSTEM_PROMPT_TEXT_AREA_LABEL, value=PROMPTS.get("system", {}).get("text", ""), height=300)
        if st.button(config.UITexts.START_CHAT_BUTTON, type="primary"):
            st.session_state['messages'] = [{"role": "system", "content": system_prompt_input}]
            st.session_state['system_role_defined'] = True
            st.rerun()
        st.stop()

    for message in st.session_state['messages']:
        if message["role"] != "system":
            with st.chat_message(message["role"]):
                st.markdown(message["content"].replace('\n', '  \n'))

    if st.session_state['messages'][-1]["role"] == "assistant" and st.session_state['last_usage_info']:
        usage = st.session_state['last_usage_info']
        max_token = env_vars.get('max_token')
        token_display = f"{usage['total_tokens']:,}"
        if max_token and max_token.isdigit():
            token_display += f"/{int(max_token):,}"
        elif max_token:
            token_display += f"/{max_token}"
        usage_text = (
            f"今回のトークン数: {token_display} (入力: {usage['input_tokens']:,}, 出力: {usage['output_tokens']:,}) | "
            f"累計トークン数: {st.session_state['total_usage']['total_tokens']:,}"
        )
        st.caption(usage_text)

    if st.session_state['is_generating']:
        if st.button(config.UITexts.STOP_GENERATION_BUTTON):
            st.session_state['stop_generation'] = True
            st.rerun()

    if prompt := st.chat_input(config.UITexts.CHAT_INPUT_PLACEHOLDER, disabled=st.session_state['is_generating']):
        st.session_state['messages'].append({"role": "user", "content": prompt})
        st.session_state['is_generating'] = True
        st.session_state['stop_generation'] = False
        st.rerun()

    if st.session_state['is_generating']:
        with st.chat_message("assistant"):
            placeholder = st.empty()
            full_response = ""
            final_response_object = None
            
            messages_to_send = st.session_state.get("special_generation_messages", st.session_state['messages'])
            is_special = "special_generation_messages" in st.session_state
            if is_special:
                del st.session_state["special_generation_messages"]
            
            canvases_to_send = [] if is_special else st.session_state['python_canvases']
            input_prompt = utils.format_history_for_input(messages_to_send, canvases_to_send)

            try:
                stream = client.responses.create(model=env_vars['deployment_name'], input=input_prompt, stream=True)
                for chunk in stream:
                    if st.session_state['stop_generation']:
                        st.warning(config.UITexts.GENERATION_STOPPED_WARNING)
                        break
                    if hasattr(chunk, 'type'):
                        if chunk.type == 'response.output_text.delta' and hasattr(chunk, 'delta') and chunk.delta:
                            full_response += chunk.delta
                            placeholder.markdown(full_response + "▌")
                        elif chunk.type == 'response.completed' and hasattr(chunk, 'response'):
                            final_response_object = chunk.response
                placeholder.markdown(full_response)
            except Exception as e:
                st.error(config.UITexts.API_REQUEST_ERROR.format(e=e))
            finally:
                st.session_state['is_generating'] = False
                st.session_state['stop_generation'] = False
                if final_response_object and hasattr(final_response_object, 'usage'):
                    usage = final_response_object.usage
                    st.session_state['total_usage'].update({
                        "input_tokens": st.session_state['total_usage']["input_tokens"] + usage.input_tokens,
                        "output_tokens": st.session_state['total_usage']["output_tokens"] + usage.output_tokens,
                        "total_tokens": st.session_state['total_usage']["total_tokens"] + usage.total_tokens
                    })
                    st.session_state['last_usage_info'] = {"total_tokens": usage.total_tokens, "input_tokens": usage.input_tokens, "output_tokens": usage.output_tokens}
                if full_response:
                    st.session_state['messages'].append({"role": "assistant", "content": full_response})
                st.rerun()

if __name__ == "__main__":
    if __package__ is None:
        PACKAGE_PARENT = '..'
        SCRIPT_DIR = os.path.dirname(os.path.realpath(os.path.join(os.getcwd(), os.path.expanduser(__file__))))
        sys.path.append(os.path.normpath(os.path.join(SCRIPT_DIR, PACKAGE_PARENT)))
        from codex_chat import config, utils
    
    run_chatbot_app()

