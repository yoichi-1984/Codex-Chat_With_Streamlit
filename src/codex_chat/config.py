# --- 定数定義 ---
MAX_CANVASES = 20

# --- 環境変数キー名 ---
AZURE_OPENAI_KEY_NAME = "AZURE_OPENAI_KEY"
AZURE_OPENAI_ENDPOINT_NAME = "AZURE_OPENAI_ENDPOINT"
AZURE_OPENAI_DEPLOYMENT_NAME = "AZURE_OPENAI_DEPLOYMENT"
AZURE_OPENAI_API_VERSION_NAME = "AZURE_OPENAI_API_VERSION"

# --- streamlit-ace (コードエディタ) 設定 ---
ACE_EDITOR_SETTINGS = {
    "language": "python",
    "theme": "monokai",
    "font_size": 14,
    "show_gutter": True,
    "wrap": True,
}
ACE_EDITOR_DEFAULT_CODE = "# ここにコードを書いてください\n"

# --- Streamlit セッションステートのデフォルト値 ---
SESSION_STATE_DEFAULTS = {
    "messages": [],
    "system_role_defined": False,
    "total_usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
    "is_generating": False,
    "last_usage_info": None,
    "python_canvases": [ACE_EDITOR_DEFAULT_CODE],
    "multi_code_enabled": False,
    "stop_generation": False,
    "canvas_key_counter": 0
}

# --- UIに表示されるテキスト ---
class UITexts:
    APP_TITLE = "🤖Codex-Chat_With_Streamlit"
    SIDEBAR_HEADER = "設定"
    RESET_BUTTON_LABEL = "会話履歴をリセット"
    CODEX_MINI_INFO = "`codex-mini` はCLIタスクに特化しているため、コード生成やスクリプト編集で真価を発揮します。"
    HISTORY_SUBHEADER = "チャット履歴 (JSON)"
    DOWNLOAD_HISTORY_BUTTON = "履歴を JSON でダウンロード"
    UPLOAD_HISTORY_LABEL = "JSON ファイルをアップロードして読み込み"
    HISTORY_LOADED_SUCCESS = "会話履歴とCanvasコードを読み込みました。"
    OLD_HISTORY_FORMAT_WARNING = "古い形式の履歴ファイルを読み込みました。Canvasコードは復元されません。"
    JSON_FORMAT_ERROR = "対応していないJSONフォーマットです。"
    JSON_LOAD_ERROR = "JSON の読み込みに失敗しました: {e}"

    EDITOR_SUBHEADER = "🔧 コードエディタ"
    MULTI_CODE_CHECKBOX = "マルチコードを有効にする"
    ADD_CANVAS_BUTTON = "次のコードを追加"
    CLEAR_BUTTON = "クリア"
    REVIEW_BUTTON = "レビュー"
    VALIDATE_BUTTON = "検証"
    VALIDATE_BUTTON_HELP = "pylintでCanvas-{i}のコードを検証し、結果をAIが分析します。"

    SYSTEM_PROMPT_HEADER = "最初にAIの役割（システムプロンプト）を設定してください"
    SYSTEM_PROMPT_TEXT_AREA_LABEL = "AIの役割"
    START_CHAT_BUTTON = "この役割でチャットを開始する"

    ENV_VARS_ERROR = "エラー: 必要な環境変数 ({vars}) が設定されていません。"
    CLIENT_INIT_ERROR = "Azure OpenAIクライアントの初期化に失敗しました: {e}"
    API_REQUEST_ERROR = "APIリクエスト中にエラーが発生しました: {e}"
    
    NO_CODE_TO_VALIDATE = "検証するコードがありません。"
    VALIDATE_SPINNER_MULTI = "Canvas-{i} を検証中..."
    VALIDATE_SPINNER_SINGLE = "コードを検証中..."
    PYLINT_SUCCESS_MULTI = "✅ Canvas-{i}: pylint検証完了。問題なし。"
    PYLINT_SUCCESS_SINGLE = "✅ pylint検証完了。問題なし。"
    
    # ★★★★★ 修正点 ★★★★★
    # pylintが構文エラーを検出した際のメッセージを追加
    PYLINT_SYNTAX_ERROR = "⚠️ このコードは有効なPythonではないようです。pylintが構文エラーを検出しました。"

    STOP_GENERATION_BUTTON = "生成を停止"
    CHAT_INPUT_PLACEHOLDER = "シェルコマンドの生成やスクリプト作成の指示を入力..."
    
    # --- Pylintエラー修正のために追加 ---
    REVIEW_PROMPT_SINGLE = "### 参考コード (Canvas)\n上記のコードをレビューし、改善点を提案してください。"
    REVIEW_PROMPT_MULTI = "### 参考コード (Canvas-{i})\nこのCanvasのコードをレビューし、改善点を提案してください。"
    GENERATION_STOPPED_WARNING = "ユーザーによって応答の生成が中断されました。"
