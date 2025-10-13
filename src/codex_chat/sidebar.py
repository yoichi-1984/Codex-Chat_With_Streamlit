import streamlit as st
import os
import json
import time
from streamlit_ace import st_ace
from . import config

def render_sidebar(supported_types, env_files, load_history, handle_clear, handle_review, handle_validation, handle_file_upload):
    """
    Streamlitアプリケーションのサイドバーを描画する関数
    """
    with st.sidebar:
        st.header("モデル設定")
        def on_env_change():
            # .envを切り替えたら会話はリセットするが、ウィジェットの設定は維持する
            for key, value in config.SESSION_STATE_DEFAULTS.items():
                if key in ['reasoning_effort']:  # このキーはリセットしない
                    continue
                st.session_state[key] = value.copy() if isinstance(value, (dict, list)) else value

        st.selectbox(
            label="使用するAIモデル (.env) を選択",
            options=env_files,
            format_func=lambda x: os.path.basename(x),
            key='selected_env_file',
            on_change=on_env_change,
            help="モデル設定を切り替えると、現在の会話はリセットされます。会話開始後はロックされます。",
            disabled=st.session_state['system_role_defined'] or st.session_state['is_generating']
        )

        st.selectbox(
            label="Reasoning Effort を選択",
            options=['high', 'medium', 'low'],
            key='reasoning_effort',
            help="AIの思考の深さを変更します。いつでも切り替え可能です。"
        )

        st.header(config.UITexts.SIDEBAR_HEADER)
        if st.button(config.UITexts.RESET_BUTTON_LABEL, use_container_width=True, disabled=st.session_state['is_generating']):
            # 会話をリセットするが、ウィジェットの設定は維持する
            for key, value in config.SESSION_STATE_DEFAULTS.items():
                if key in ['reasoning_effort', 'selected_env_file']: # このキーはリセットしない
                    continue
                st.session_state[key] = value.copy() if isinstance(value, (dict, list)) else value
            st.rerun()

        st.info(config.UITexts.CODEX_MINI_INFO)

        st.subheader(config.UITexts.HISTORY_SUBHEADER)
        if not st.session_state['is_generating'] and st.session_state['messages']:
            history_data = {
                "messages": st.session_state['messages'],
                "python_canvases": st.session_state['python_canvases'],
                "selected_env_file": st.session_state.get('selected_env_file'),
                "multi_code_enabled": st.session_state['multi_code_enabled']
            }
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
                    type= supported_types,
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
                type= supported_types,
                key=uploader_key_single,
                on_change=handle_file_upload,
                args=(0, uploader_key_single),
                disabled=st.session_state['is_generating']
            )

