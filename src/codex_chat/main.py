import os
import json
import sys  # standard library
import time
import tempfile
import subprocess

import streamlit as st  # third party
from dotenv import load_dotenv
from openai import AzureOpenAI
from streamlit_ace import st_ace  # Code Editor

# --- 定数定義 ---
# .envから読み込むため、ここのAPIバージョンは不要になりました
MAX_INPUT_TOKENS = 200000
MAX_CANVASES = 20

# --- ユーティリティ関数 ---

def format_history_for_input(messages, canvases):
    """
    Streamlitのセッション履歴とCanvasコードを、
    codex-miniのResponses APIが要求する単一の入力文字列に変換する。
    """
    formatted_string = ""
    system_prompt = ""
    
    for message in messages:
        if message["role"] == "system":
            system_prompt = message["content"]
            break
    
    formatted_string += system_prompt

    # マルチコード対応: 複数のCanvasコードをプロンプトに含める
    for i, canvas_code in enumerate(canvases):
        if canvas_code and canvas_code.strip() != "# ここにコードを書いてください":
            formatted_string += f"\n\n### 参考コード (Canvas-{i + 1})\n```python\n{canvas_code}\n```"

    formatted_string += "\n\n---\n\n### 会話履歴\n"

    for message in messages:
        if message["role"] != "system":
            formatted_string += f'{message["role"].upper()}: {message["content"]}\n\n'
    
    formatted_string += "ASSISTANT:"
    return formatted_string

def load_history():
    """
    ファイルアップローダーの on_change コールバック。
    会話履歴とCanvasコードを読み込む。
    """
    uploaded_file = st.session_state.history_uploader
    if uploaded_file:
        try:
            # 会話履歴とCanvasコードの両方を読み込む
            loaded_data = json.load(uploaded_file)

            # 新フォーマット (辞書形式) のチェック
            if isinstance(loaded_data, dict) and "messages" in loaded_data:
                loaded_messages = loaded_data["messages"]
                # messagesが正しい形式かさらにチェック
                if not (isinstance(loaded_messages, list) and all(isinstance(m, dict) and "role" in m and "content" in m for m in loaded_messages)):
                    st.error("JSON内の 'messages' のフォーマットが不正です。")
                    return
                
                st.session_state.messages = loaded_messages
                # Canvasコードもあれば復元
                if "python_canvas" in loaded_data:
                    # 旧フォーマットとの互換性のため、リストに変換
                    st.session_state.python_canvases = [loaded_data["python_canvas"]]
                    st.session_state.multi_code_enabled = False
                    st.session_state.canvas_key_counter += 1
                elif "python_canvases" in loaded_data:
                    st.session_state.python_canvases = loaded_data["python_canvases"]
                    st.session_state.multi_code_enabled = True
                    st.session_state.canvas_key_counter += 1

                st.success("会話履歴とCanvasコードを読み込みました。")

            # 旧フォーマット (リスト形式) のチェック (後方互換性のため)
            elif isinstance(loaded_data, list) and all(isinstance(m, dict) and "role" in m and "content" in m for m in loaded_data):
                st.session_state.messages = loaded_data
                st.warning("古い形式の履歴ファイルを読み込みました。Canvasコードは復元されません。")
            
            else:
                st.error("対応していないJSONフォーマットです。")
                return

            # 共通の初期化処理
            st.session_state.system_role_defined = True
            st.session_state.total_usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
            st.session_state.last_usage_info = None

        except Exception as e:
            st.error(f"JSON の読み込みに失敗しました: {e}")


# --- Streamlit アプリケーション ---

def run_chatbot_app():
    st.set_page_config(page_title="codex-mini 高性能チャットボット", layout="wide")
    st.title("🤖 codex-mini 専用チャットボット")

    # 環境変数の読み込み
    # 改善点: .envファイルのパスを変更
    dotenv_path = "env/codex.env"
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)
        # 改善点: .env読み込み成功をフィードバック
        st.sidebar.success(f"`{dotenv_path}` を読み込みました")
    else:
        st.info(f"`{dotenv_path}` が見つかりません。環境変数が直接設定されていることを前提に動作します。")

    api_key = os.getenv("AZURE_OPENAI_KEY")
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION")
    
    # 実際に使用するAPIバージョンを画面に表示
    st.caption(f"このチャットは、`Responses API (api-version={api_version or '未設定'})` を使用して動作します。")

    if not all([api_key, azure_endpoint, deployment_name, api_version]):
        st.error("エラー: 必要な環境変数 (AZURE_OPENAI_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT, AZURE_OPENAI_API_VERSION) が設定されていません。")
        st.stop()

    try:
        client = AzureOpenAI(
            api_key=api_key,
            azure_endpoint=azure_endpoint,
            api_version=api_version,
        )
    except Exception as e:
        st.error(f"Azure OpenAIクライアントの初期化に失敗しました: {e}")
        st.stop()

    # セッションステート初期化
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "system_role_defined" not in st.session_state:
        st.session_state.system_role_defined = False
    if "total_usage" not in st.session_state:
        st.session_state.total_usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    if "is_generating" not in st.session_state:
        st.session_state.is_generating = False
    if "last_usage_info" not in st.session_state:
        st.session_state.last_usage_info = None
    # マルチコード対応: 単一の文字列からリストに変更
    if "python_canvases" not in st.session_state:
        st.session_state.python_canvases = ["# ここにコードを書いてください\n"]
    if "multi_code_enabled" not in st.session_state:
        st.session_state.multi_code_enabled = False
    if "stop_generation" not in st.session_state:
        st.session_state.stop_generation = False
    # 改善点: Canvasの再描画を制御するためのカウンタ
    if "canvas_key_counter" not in st.session_state:
        st.session_state.canvas_key_counter = 0

    # サイドバー
    with st.sidebar:
        st.header("設定")
        if st.button("会話履歴をリセット", use_container_width=True, disabled=st.session_state.is_generating):
            st.session_state.messages = []
            st.session_state.system_role_defined = False
            st.session_state.total_usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
            st.session_state.last_usage_info = None
            st.session_state.python_canvases = ["# ここにコードを書いてください\n"]
            st.session_state.multi_code_enabled = False
            st.rerun()

        st.info("`codex-mini` はCLIタスクに特化しているため、コード生成やスクリプト編集で真価を発揮します。")

        st.subheader("チャット履歴 (JSON)")
        if st.session_state.is_generating:
            st.warning("AIの回答が完了していません。完了後に保存してください。")
        else:
            if st.session_state.messages:
                # Canvasのコードも一緒に保存する
                history_data = {
                    "messages": st.session_state.messages,
                    "python_canvases": st.session_state.python_canvases
                }
                history_json = json.dumps(history_data, ensure_ascii=False, indent=2)
                st.download_button(
                    label="履歴を JSON でダウンロード",
                    data=history_json,
                    file_name=f"chat_session_{int(time.time())}.json",
                    mime="application/json",
                    use_container_width=True,
                )

        st.file_uploader(
            label="JSON ファイルをアップロードして読み込み",
            type="json",
            key="history_uploader",
            on_change=load_history,
            disabled=st.session_state.is_generating,
        )
        
        # --- Pythonコードエディタ (Canvas) ---
        st.subheader("🔧 コードエディタ")

        multi_code_enabled = st.checkbox("マルチコードを有効にする", value=st.session_state.multi_code_enabled)

        if multi_code_enabled != st.session_state.multi_code_enabled:
            st.session_state.multi_code_enabled = multi_code_enabled
            st.session_state.canvas_key_counter += 1
            st.rerun()

        if multi_code_enabled and len(st.session_state.python_canvases) < MAX_CANVASES:
            if st.button("次のコードを追加", use_container_width=True):
                st.session_state.python_canvases.append("# ここにコードを書いてください\n")
                st.session_state.canvas_key_counter += 1
                st.rerun()

        if st.session_state.multi_code_enabled:
            # --- マルチコードモード ---
            for i, canvas_content in enumerate(st.session_state.python_canvases):
                st.write(f"**Canvas-{i + 1}**")
                updated_content = st_ace(
                    value=canvas_content,
                    language="python",
                    theme="monokai",
                    key=f"python_canvas_editor_{i}_{st.session_state.canvas_key_counter}",
                    auto_update=True,
                )
                if updated_content != canvas_content:
                    st.session_state.python_canvases[i] = updated_content
                    st.session_state.canvas_key_counter += 1
                    st.rerun()

                # --- Canvasごとの個別操作ボタン ---
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("クリア", key=f"clear_canvas_{i}", use_container_width=True):
                        st.session_state.python_canvases[i] = "# ここにコードを書いてください\n"
                        st.session_state.canvas_key_counter += 1
                        st.rerun()
                with col2:
                    if st.button("レビュー", key=f"review_canvas_{i}", use_container_width=True):
                        review_prompt = f"### 参考コード (Canvas-{i+1})\nこのCanvasのコードをレビューし、改善点を提案してください。"
                        st.session_state.messages.append({"role": "user", "content": review_prompt})
                        st.session_state.is_generating = True
                        st.session_state.stop_generation = False
                        st.session_state.last_usage_info = None
                        st.rerun()
                with col3:
                    if st.button("検証", key=f"validate_canvas_{i}", use_container_width=True, help=f"pylintでCanvas-{i+1}のコードを検証し、結果をAIが分析します。"):
                        with st.spinner(f"Canvas-{i+1} を検証中..."):
                            canvas_code = st.session_state.python_canvases[i]
                            if not canvas_code or canvas_code.strip() == "" or canvas_code.strip() == "# ここにコードを書いてください":
                                st.toast(f"Canvas-{i+1}には検証するコードがありません。", icon="⚠️")
                            else:
                                code_for_prompt = f"\n\n# 解析対象のコード (Canvas-{i + 1})\n```python\n{canvas_code}\n```"
                                processed_code = canvas_code.replace('\r\n', '\n')
                                tmp_file_path = ""
                                pylint_report = ""
                                try:
                                    with tempfile.NamedTemporaryFile(mode='w+', suffix='.py', delete=False, encoding='utf-8') as tmp_file:
                                        tmp_file_path = tmp_file.name
                                        tmp_file.write(processed_code)
                                        tmp_file.flush()
                                    result = subprocess.run([sys.executable, "-m", "pylint", tmp_file_path], capture_output=True, text=True, encoding='utf-8', check=False)
                                    issues = [line for line in result.stdout.splitlines() if line.strip() and not line.startswith('*') and not line.startswith('-') and 'Your code has been rated' not in line]
                                    if issues:
                                        cleaned_issues = [issue.replace(f'{tmp_file_path}:', 'Line ') for issue in issues]
                                        pylint_report = "\n".join(cleaned_issues)
                                finally:
                                    if os.path.exists(tmp_file_path):
                                        os.remove(tmp_file_path)

                                if not pylint_report.strip():
                                    st.sidebar.success(f"✅ Canvas-{i+1}: pylint検証完了。問題なし。")
                                else:
                                    validation_prompt = f"""あなたは優秀なPython開発アシスタントです。
以下のコードと、それに対するpylintの解析レポートをレビューしてください。
# 前提条件
- このコードはWindows環境で実行されます。
- 改行コードの違い(CRLF)、末尾の空白、長すぎる行、変数名の命名規則など、コーディングスタイルに関する指摘は、動作に直接的な影響がない限り無視してください。
# 解析対象のコード
{code_for_prompt}
# pylintの解析レポート
{pylint_report}

# あなたのタスク
上記のレポートの中から、「Windowsでの動作に致命的な影響を与える可能性のある、修正必須のエラー」のみを特定してください。
- **修正必須のエラーがある場合：** その内容と、なぜそれが問題なのかを簡潔に説明し、修正案を提示してください。
- **修正必須のエラーがない場合：** 「pylintでいくつかの指摘がありましたが、Windows環境での動作を妨げる致命的なエラーではありません。」とだけ回答してください。
"""
                                    system_message = st.session_state.messages[0] if st.session_state.messages and st.session_state.messages[0]["role"] == "system" else {"role": "system", "content": ""}
                                    st.session_state.special_generation_messages = [system_message, {"role": "user", "content": validation_prompt}]
                                    st.session_state.is_generating = True
                                    st.session_state.stop_generation = False
                                    st.session_state.last_usage_info = None
                                    st.rerun()
                st.divider()
            
            # --- 全Canvas対象の一括操作ボタン ---
            st.subheader("一括操作")
            g_col1, g_col2, g_col3 = st.columns(3)
            with g_col1:
                if st.button("すべてクリア", key="clear_all_canvases", use_container_width=True):
                    st.session_state.python_canvases = ["# ここにコードを書いてください\n"] * len(st.session_state.python_canvases)
                    st.session_state.canvas_key_counter += 1
                    st.rerun()
            with g_col2:
                if st.button("すべてレビュー", key="review_all_canvases", use_container_width=True):
                    review_prompt = "### 参考コード (Canvas)\n上記のすべてのコードをレビューし、改善点を提案してください。"
                    st.session_state.messages.append({"role": "user", "content": review_prompt})
                    st.session_state.is_generating = True
                    st.session_state.stop_generation = False
                    st.session_state.last_usage_info = None
                    st.rerun()
            with g_col3:
                if st.button("すべて検証", key="validate_all_canvases_ai", use_container_width=True, help="pylintですべてのコードを検証し、結果をAIが分析して重要度を判断します。"):
                    # This is the original full validation logic
                    with st.spinner("すべてのコードを検証し、AIが分析しています..."):
                        full_pylint_report = ""
                        code_for_prompt = ""
                        has_code_to_validate = False
                        for i, canvas_code in enumerate(st.session_state.python_canvases):
                            if not canvas_code or canvas_code.strip() == "" or canvas_code.strip() == "# ここにコードを書いてください":
                                continue
                            has_code_to_validate = True
                            code_for_prompt += f"\n\n# 解析対象のコード (Canvas-{i + 1})\n```python\n{canvas_code}\n```"
                            processed_code = canvas_code.replace('\r\n', '\n')
                            tmp_file_path = ""
                            try:
                                with tempfile.NamedTemporaryFile(mode='w+', suffix='.py', delete=False, encoding='utf-8') as tmp_file:
                                    tmp_file_path = tmp_file.name
                                    tmp_file.write(processed_code)
                                    tmp_file.flush()
                                result = subprocess.run([sys.executable, "-m", "pylint", tmp_file_path], capture_output=True, text=True, encoding='utf-8', check=False)
                                issues = [line for line in result.stdout.splitlines() if line.strip() and not line.startswith('*') and not line.startswith('-') and 'Your code has been rated' not in line]
                                if issues:
                                    cleaned_issues = [issue.replace(f'{tmp_file_path}:', 'Line ') for issue in issues]
                                    full_pylint_report += f"# Canvas-{i + 1} のpylintレポート\n" + "\n".join(cleaned_issues) + "\n"
                            finally:
                                if os.path.exists(tmp_file_path):
                                    os.remove(tmp_file_path)
                        
                        if not has_code_to_validate:
                            st.toast("検証するコードがありません。", icon="⚠️")
                        elif not full_pylint_report.strip():
                            st.sidebar.success("✅ pylintによる検証が完了しました。問題は見つかりませんでした。")
                        else:
                            validation_prompt = f"""あなたは優秀なPython開発アシスタントです。
以下のコードと、それに対するpylintの解析レポートをレビューしてください。
# 前提条件
- このコードはWindows環境で実行されます。
- 改行コードの違い(CRLF)、末尾の空白、長すぎる行、変数名の命名規則など、コーディングスタイルに関する指摘は、動作に直接的な影響がない限り無視してください。
# 解析対象のコード
{code_for_prompt}
# pylintの解析レポート
{full_pylint_report}

# あなたのタスク
上記のレポートの中から、「Windowsでの動作に致命的な影響を与える可能性のある、修正必須のエラー」のみを特定してください。
- **修正必須のエラーがある場合：** その内容と、なぜそれが問題なのかを簡潔に説明し、修正案を提示してください。
- **修正必須のエラーがない場合：** 「pylintでいくつかの指摘がありましたが、Windows環境での動作を妨げる致命的なエラーではありません。」とだけ回答してください。
"""
                            system_message = st.session_state.messages[0] if st.session_state.messages and st.session_state.messages[0]["role"] == "system" else {"role": "system", "content": ""}
                            st.session_state.special_generation_messages = [system_message, {"role": "user", "content": validation_prompt}]
                            st.session_state.is_generating = True
                            st.session_state.stop_generation = False
                            st.session_state.last_usage_info = None
                            st.rerun()

        else:
            # --- シングルコードモード ---
            st.session_state.python_canvases = [st.session_state.python_canvases[0]]
            updated_content = st_ace(
                value=st.session_state.python_canvases[0],
                language="python",
                theme="monokai",
                key=f"python_canvas_editor_0_{st.session_state.canvas_key_counter}",
                auto_update=True,
            )
            if updated_content != st.session_state.python_canvases[0]:
                st.session_state.python_canvases[0] = updated_content
                st.session_state.canvas_key_counter += 1
                st.rerun()

            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("クリア", key="clear_canvas_single", use_container_width=True):
                    st.session_state.python_canvases[0] = "# ここにコードを書いてください\n"
                    st.session_state.canvas_key_counter += 1
                    st.rerun()
            with col2:
                if st.button("レビュー", key="review_canvas_single", use_container_width=True):
                    review_prompt = "### 参考コード (Canvas)\n上記のコードをレビューし、改善点を提案してください。"
                    st.session_state.messages.append({"role": "user", "content": review_prompt})
                    st.session_state.is_generating = True
                    st.session_state.stop_generation = False
                    st.session_state.last_usage_info = None
                    st.rerun()
            with col3:
                if st.button("検証", key="validate_canvas_single", use_container_width=True, help="pylintでこのコードを検証し、結果をAIが分析します。"):
                    # This is the same logic as the individual button in multi-code mode, but for index 0
                    with st.spinner(f"コードを検証し、AIが分析しています..."):
                        canvas_code = st.session_state.python_canvases[0]
                        if not canvas_code or canvas_code.strip() == "" or canvas_code.strip() == "# ここにコードを書いてください":
                            st.toast("検証するコードがありません。", icon="⚠️")
                        else:
                            code_for_prompt = f"\n\n# 解析対象のコード\n```python\n{canvas_code}\n```"
                            processed_code = canvas_code.replace('\r\n', '\n')
                            tmp_file_path = ""
                            pylint_report = ""
                            try:
                                with tempfile.NamedTemporaryFile(mode='w+', suffix='.py', delete=False, encoding='utf-8') as tmp_file:
                                    tmp_file_path = tmp_file.name
                                    tmp_file.write(processed_code)
                                    tmp_file.flush()
                                result = subprocess.run([sys.executable, "-m", "pylint", tmp_file_path], capture_output=True, text=True, encoding='utf-8', check=False)
                                issues = [line for line in result.stdout.splitlines() if line.strip() and not line.startswith('*') and not line.startswith('-') and 'Your code has been rated' not in line]
                                if issues:
                                    cleaned_issues = [issue.replace(f'{tmp_file_path}:', 'Line ') for issue in issues]
                                    pylint_report = "\n".join(cleaned_issues)
                            finally:
                                if os.path.exists(tmp_file_path):
                                    os.remove(tmp_file_path)

                            if not pylint_report.strip():
                                st.sidebar.success("✅ pylint検証完了。問題なし。")
                            else:
                                validation_prompt = f"""あなたは優秀なPython開発アシスタントです。
以下のコードと、それに対するpylintの解析レポートをレビューしてください。
# 前提条件
- このコードはWindows環境で実行されます。
- 改行コードの違い(CRLF)、末尾の空白、長すぎる行、変数名の命名規則など、コーディングスタイルに関する指摘は、動作に直接的な影響がない限り無視してください。
# 解析対象のコード
{code_for_prompt}
# pylintの解析レポート
{pylint_report}

# あなたのタスク
上記のレポートの中から、「Windowsでの動作に致命的な影響を与える可能性のある、修正必須のエラー」のみを特定してください。
- **修正必須のエラーがある場合：** その内容と、なぜそれが問題なのかを簡潔に説明し、修正案を提示してください。
- **修正必須のエラーがない場合：** 「pylintでいくつかの指摘がありましたが、Windows環境での動作を妨げる致命的なエラーではありません。」とだけ回答してください。
"""
                                system_message = st.session_state.messages[0] if st.session_state.messages and st.session_state.messages[0]["role"] == "system" else {"role": "system", "content": ""}
                                st.session_state.special_generation_messages = [system_message, {"role": "user", "content": validation_prompt}]
                                st.session_state.is_generating = True
                                st.session_state.stop_generation = False
                                st.session_state.last_usage_info = None
                                st.rerun()

        st.header("デバッグ")
        debug_mode = st.checkbox("デバッグモードを有効にする", help="有効にすると、APIからの生の応答データがチャット欄に表示されます。", disabled=st.session_state.is_generating)


    # システムプロンプト設定
    if not st.session_state.system_role_defined:
        st.subheader("最初にAIの役割（システムプロンプト）を設定してください")
        default_prompt = """あなたは、コマンドライン操作とスクリプト生成に特化した専門家AI、codex-miniです。
以下のタスクを正確かつ効率的に実行してください。

1.  **自然言語をシェルコマンドに変換する:** "カレントディレクトリのファイルをすべてリストして" -> `ls -l`
2.  **スクリプトの生成と編集:** Python, Bash, PowerShellなどのスクリプトを生成・修正する。
3.  **コードのリファクタリング:** 提示されたコードをより効率的、または読みやすく書き換える。
4.  **参考コードの利用:** プロンプトに「### 参考コード (Canvas)」が含まれている場合、そのコードを最優先の文脈として扱い、質問への回答やコードの修正を行ってください。
5.  **出典の明記:** コードのレビュー、修正、または特定のコード部分について言及する際は、必ず `(出典: Canvas-1, 15-20行目)` の形式で、参照したCanvas番号と行番号を明記してください。これは回答の信頼性を担保するために非常に重要です。

常に簡潔で、直接的で、実行可能なコードを優先して回答してください。説明は必要最小限に留めてください。
"""
        system_prompt_input = st.text_area("AIの役割", value=default_prompt, height=300)
        if st.button("この役割でチャットを開始する", type="primary"):
            if system_prompt_input:
                st.session_state.messages = [{"role": "system", "content": system_prompt_input}]
                st.session_state.system_role_defined = True
                st.rerun()
            else:
                st.warning("役割を入力してください。")

    # メインチャット画面
    else:
        # AI検証機能からの特別なリクエストでない場合のみ、通常のメッセージ履歴を表示
        if "special_generation_messages" not in st.session_state:
            for message in st.session_state.messages:
                if message["role"] != "system":
                    with st.chat_message(message["role"]):
                        # 改行文字(\n)を、Markdownの改行(スペース2つ + \n)に置換する
                        st.markdown(message["content"].replace('\n', '  \n'))
        
        if st.session_state.messages and st.session_state.messages[-1]["role"] == "assistant" and st.session_state.last_usage_info:
            usage = st.session_state.last_usage_info
            usage_text = (
                f"今回のトークン数: {usage['total_tokens']} (入力: {usage['input_tokens']} / **最大: {MAX_INPUT_TOKENS:,}**, 出力: {usage['output_tokens']}) | "
                f"累計トークン数: {st.session_state.total_usage['total_tokens']}"
            )
            st.caption(usage_text)

        # 応答中に停止ボタンを表示
        if st.session_state.is_generating:
            if st.button("生成を停止", key="stop_generation_button"):
                st.session_state.stop_generation = True
                # 即座に反映させるためにリラン
                st.rerun()

        if prompt := st.chat_input("シェルコマンドの生成やスクリプト作成の指示を入力...", disabled=st.session_state.is_generating):
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.session_state.is_generating = True
            st.session_state.stop_generation = False # 新しい生成が始まるのでリセット
            st.session_state.last_usage_info = None
            st.rerun() 

    # ストリーミングでAI応答を生成
    if st.session_state.get("is_generating"):
        with st.chat_message("assistant"):
            full_response = ""
            final_response_object = None
            placeholder = st.empty()
            is_special_generation = "special_generation_messages" in st.session_state

            try:
                # AI検証ボタンからの特別なリクエストか、通常のチャットかを判断
                if is_special_generation:
                    input_prompt = format_history_for_input(
                        st.session_state.special_generation_messages,
                        [] # キャンバスコードはプロンプトに内包されているため不要
                    )
                    # 使用後は削除して通常モードに戻す
                    del st.session_state.special_generation_messages
                else:
                    # 通常のチャットの場合
                    input_prompt = format_history_for_input(
                        st.session_state.messages,
                        st.session_state.python_canvases
                    )

                stream = client.responses.create(
                    model=deployment_name,
                    input=input_prompt,
                    stream=True,
                )
                
                if debug_mode:
                    debug_area = st.expander("デバッグ出力").container()

                for chunk in stream:
                    # 停止フラグをチェック
                    if st.session_state.get("stop_generation"):
                        st.warning("ユーザーによって応答の生成が中断されました。")
                        break

                    if debug_mode:
                        debug_area.json(chunk.model_dump_json(indent=2))

                    if hasattr(chunk, 'type'):
                        if chunk.type == 'response.output_text.delta':
                            if hasattr(chunk, 'delta') and chunk.delta:
                                full_response += chunk.delta
                                placeholder.markdown(full_response + "▌")
                        elif chunk.type == 'response.completed':
                            if hasattr(chunk, 'response'):
                                final_response_object = chunk.response
                
                placeholder.markdown(full_response)

            except Exception as e:
                st.error(f"APIリクエスト中にエラーが発生しました: {e}")
                st.info("エンドポイント、デプロイ名、APIキー等が正しいか確認してください。")
            finally:
                st.session_state.is_generating = False
                st.session_state.stop_generation = False # 完了またはエラー時にリセット
            
            if final_response_object:
                usage = getattr(final_response_object, 'usage', None)
                finish_details = getattr(final_response_object, 'finish_details', None)

                if not full_response and finish_details:
                    if finish_details.type == 'stop' and getattr(finish_details, 'stop', None) == 'content_filter':
                        st.error("応答がコンテンツフィルターによってブロックされました。入力内容を変更して再度お試しください。")
                    else:
                        st.warning(f"AIが空の応答を返しました。(終了理由: {finish_details.type}) プロンプトが適切でない可能性があります。")
                
                if usage:
                    st.session_state.total_usage["input_tokens"] += usage.input_tokens
                    st.session_state.total_usage["output_tokens"] += usage.output_tokens
                    st.session_state.total_usage["total_tokens"] += usage.total_tokens
                    st.session_state.last_usage_info = {
                        "total_tokens": usage.total_tokens,
                        "input_tokens": usage.input_tokens,
                        "output_tokens": usage.output_tokens,
                    }

            if full_response:
                # 通常のチャット履歴にアシスタントの最終回答を追加
                st.session_state.messages.append({"role": "assistant", "content": full_response})
            
            st.rerun() 

if __name__ == "__main__":
    run_chatbot_app()
