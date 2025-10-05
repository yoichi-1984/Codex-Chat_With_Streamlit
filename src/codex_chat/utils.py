import os
import sys
import json
import yaml
import tempfile
import subprocess
from importlib import resources

import streamlit as st

from . import config


@st.cache_data
def load_prompts():
    """
    パッケージ内のprompts.yamlを一度だけ読み込み、結果をキャッシュする
    """
    try:
        with resources.open_text("codex_chat", "prompts.yaml") as f:
            yaml_data = yaml.safe_load(f)
            return yaml_data.get("prompts", {})
    except FileNotFoundError:
        st.error("重大なエラー: prompts.yamlが見つかりません。")
        st.stop()
    except Exception as e:
        st.error(f"重大なエラー: prompts.yamlの読み込みに失敗しました: {e}")
        st.stop()

def find_env_files(directory="env"):
    """
    指定されたディレクトリ内の.envファイルをすべて検索する
    """
    if not os.path.isdir(directory):
        return []
    return [os.path.join(directory, f) for f in os.listdir(directory) if f.endswith(".env")]

def format_history_for_input(messages, canvases):
    """
    会話履歴とCanvasコードをAIへの単一の入力文字列に変換する
    """
    formatted_string = ""
    system_prompt = ""
    
    for message in messages:
        if message["role"] == "system":
            system_prompt = message["content"]
            break
    
    formatted_string += system_prompt

    for i, canvas_code in enumerate(canvases):
        if canvas_code and canvas_code.strip() != config.ACE_EDITOR_DEFAULT_CODE.strip():
            formatted_string += f"\n\n### 参考コード (Canvas-{i + 1})\n```python\n{canvas_code}\n```"

    formatted_string += "\n\n---\n\n### 会話履歴\n"

    for message in messages:
        if message["role"] != "system":
            formatted_string += f'{message["role"].upper()}: {message["content"]}\n\n'
    
    formatted_string += "ASSISTANT:"
    return formatted_string


def run_pylint_validation(canvas_code, canvas_index, prompts):
    """
    指定されたコードに対してpylintを実行し、AI分析用のプロンプトを生成または成功を通知する
    """
    if not canvas_code or canvas_code.strip() == "" or canvas_code.strip() == config.ACE_EDITOR_DEFAULT_CODE.strip():
        st.toast(config.UITexts.NO_CODE_TO_VALIDATE, icon="⚠️")
        return

    spinner_text = config.UITexts.VALIDATE_SPINNER_MULTI.format(i=canvas_index + 1) if st.session_state['multi_code_enabled'] else config.UITexts.VALIDATE_SPINNER_SINGLE
    with st.spinner(spinner_text):
        tmp_file_path = ""
        pylint_report = ""
        try:
            with tempfile.NamedTemporaryFile(mode='w+', suffix='.py', delete=False, encoding='utf-8') as tmp_file:
                tmp_file_path = tmp_file.name
                tmp_file.write(canvas_code.replace('\r\n', '\n'))
                tmp_file.flush()
            
            result = subprocess.run(
                [sys.executable, "-m", "pylint", tmp_file_path],
                capture_output=True, text=True, check=False
            )
            
            error_output = (result.stderr or "") + (result.stdout or "")
            if ("invalid syntax" in error_output.lower() or 
                "parsing error" in error_output.lower() or
                "E0001: syntax-error" in error_output):
                st.toast(config.UITexts.PYLINT_SYNTAX_ERROR, icon="⚠️")
                return 

            issues = []
            if result.stdout:
                issues = [line for line in result.stdout.splitlines() if line.strip() and not line.startswith(('*', '-')) and 'Your code has been rated' not in line]
            
            if issues:
                cleaned_issues = [issue.replace(f'{tmp_file_path}:', 'Line ') for issue in issues]
                pylint_report = "\n".join(cleaned_issues)
        finally:
            if os.path.exists(tmp_file_path):
                os.remove(tmp_file_path)

    success_message = config.UITexts.PYLINT_SUCCESS_MULTI.format(i=canvas_index + 1) if st.session_state['multi_code_enabled'] else config.UITexts.PYLINT_SUCCESS_SINGLE
    if not pylint_report.strip():
        st.sidebar.success(success_message)
        return

    code_for_prompt = f"\n\n# 解析対象のコード (Canvas-{canvas_index + 1})\n```python\n{canvas_code}\n```"
    validation_template = prompts.get("validation", {}).get("text", "")
    validation_prompt = validation_template.format(code_for_prompt=code_for_prompt, pylint_report=pylint_report)
    
    system_message = st.session_state['messages'][0] if st.session_state['messages'] and st.session_state['messages'][0]["role"] == "system" else {"role": "system", "content": ""}
    st.session_state['special_generation_messages'] = [system_message, {"role": "user", "content": validation_prompt}]
    st.session_state['is_generating'] = True
    st.session_state['stop_generation'] = False
    st.rerun()

def load_app_config():
    """
    パッケージ内のconfig.yamlを一度だけ読み込み、結果をキャッシュする
    """
    try:
        with resources.open_text("codex_chat", "config.yaml") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        st.error("重大なエラー: config.yamlが見つかりません。")
        st.stop()
    except Exception as e:
        st.error(f"重大なエラー: config.yamlの読み込みに失敗しました: {e}")
        st.stop()