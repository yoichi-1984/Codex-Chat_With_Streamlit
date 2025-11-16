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
from codex_chat import sidebar

# --- ヘルパー関数 (アプリケーション固有) ---

# --- ★★★★★ 変更点 (ここから) ★★★★★ ---
# def load_history():
def load_history(uploader_key):
# --- ★★★★★ 変更点 (ここまで) ★★★★★ ---
    """
    アップロードされたJSONから会話履歴とCanvasコードを読み込む
    """
    # --- ★★★★★ 変更点 (ここから) ★★★★★ ---
    # uploaded_file = st.session_state['history_uploader']
    uploaded_file = st.session_state.get(uploader_key)
    # --- ★★★★★ 変更点 (ここまで) ★★★★★ ---
    if not uploaded_file:
        return
    try:
        loaded_data = json.load(uploaded_file)
        if isinstance(loaded_data, dict) and "messages" in loaded_data:
            st.session_state['messages'] = loaded_data["messages"]
            if "python_canvases" in loaded_data:
                st.session_state['python_canvases'] = loaded_data["python_canvases"]
            
            if "multi_code_enabled" in loaded_data:
                st.session_state['multi_code_enabled'] = loaded_data["multi_code_enabled"]

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
    APP_CONFIG = utils.load_app_config()
    supported_types = APP_CONFIG.get("file_uploader", {}).get("supported_extensions", [])
    
    env_files = utils.find_env_files()
    if not env_files:
        st.error("`env` ディレクトリに `.env` ファイルが見つかりません。アプリケーションを続行できません。")
        st.stop()

    for key, value in config.SESSION_STATE_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = value.copy() if isinstance(value, (dict, list)) else value

    if 'reasoning_effort' not in st.session_state:
        st.session_state['reasoning_effort'] = 'medium'  # デフォルト値を 'medium' に設定
    
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

    sidebar.render_sidebar(supported_types, env_files, load_history, handle_clear, handle_review, handle_validation, handle_file_upload)
    
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
                # --- ★★★★★ 変更点 ④ (ここから) ★★★★★ ---
                # セッション状態から選択された reasoning effort を取得
                selected_effort = st.session_state.get('reasoning_effort', 'medium')
                
                stream = client.responses.create(
                    model=env_vars['deployment_name'], 
                    input=input_prompt, 
                    stream=True, 
                    # 取得した値をAPIに渡す
                    extra_body={"reasoning": {"effort": selected_effort}}
                )
                # --- ★★★★★ 変更点 ④ (ここまで) ★★★★★ ---
                
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
                if final_response_object and hasattr(final_response_object, 'response'):
                    usage = final_response_object.response.usage
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
    