Codex-chat with streamlit: AIコーディングアシスタント  
  
## Table of Contents

- [概要](#概要)  
- [リポジトリ構成](#リポジトリ構成)  
- [インストール](#インストール例)  
- [環境設定](#環境設定)  
- [使い方](#使い方)  
- [主な機能](#主な機能)  
- [CHANGELOG](#changelog)  
- [ライセンス](#ライセンス)  
- [Author](#Author)  
  
---  
## 概要  
  
`Codex-chat with streamlit` は、  
- 自然言語をシェルコマンドに変換  
- Python／Bash／PowerShell スクリプトの生成・編集  
- コードのリファクタリング  
- Streamlit ベースのチャットUI + 複数 Canvas（コードエディタ）  

に特化した専門家AIチャットボットです。  
本アプリケーションは、従来のチャット形式の対話に加え、複数のコードブロック（Canvas）をコンテキストとしてAIに提供できる「マルチコード」機能を搭載しています。これにより、既存のコードのレビュー、デバッグ、機能追加など、より複雑なコーディング作業を効率的に行えます。  

CLIラッパー (`main_runner.py`) は `streamlit run main.py` を自動で呼び出します。  
  
---  
## リポジトリ構成  
.  
 ├── env/codex.env #環境変数の雛形  
 ├── .gitignore  
 ├── LICENSE  
 ├── README.md  
 ├── activate.bat  
 ├── pyproject.toml  
 ├── requirements.txt  
 ├── CHANGELOG.md  
 └── src/codex_chat  
      　├── __init__.py  
      　├── main.py  
      　└── main_runner.py # Streamlit CLI ラッパー  
  
---  
## インストール例  
    
```bash  
git clone https://github.com/ユーザ名/codex-mini.git  
cd codex-mini  
python3 -m venv .env  
source .env/bin/activate  
pip install --upgrade pip  
pip install --upgrade pip setuptools
pip install -r requirements.txt  
```
  
---  
## 環境設定  
  
プロジェクトルートに env/codex.env を作成し、以下を設定してください。  
  
AZURE_OPENAI_KEY=<your_api_key>  
AZURE_OPENAI_ENDPOINT=<your_endpoint>  
AZURE_OPENAI_DEPLOYMENT=<deployment_name>  
AZURE_OPENAI_API_VERSION=<api_version>  
  
---  
## 使い方    
  
pyproject.tomlに従ってインストール。  
pip install -e .  
その後は  
仮想環境で「codex-chat」と打ち込めば、内部的にstreamlit run で main_runner.py が実行される。  
  
---  
## 主な機能  
### AIの役割設定:  
 最初の画面で、AIの役割を定義するシステムプロンプトを入力し、「この役割でチャットを開始する」ボタンをクリックします。  
### マルチ Canvas コードエディタ（最大 20）  
 Canvasを用いてコードをAIに効率よく読ませることができます。マルチコード機能を有効にすることで、最大20個までCanvasを拡張することも可能です。  
### 会話履歴の JSON ダウンロード／アップロード  
 AIの役割、チャット履歴、Canvasの内容すべてをJSON形式でダウンロードし、途中再開が可能です。  
### デバッグモード切替  
 デバッグモードを有効にすることで、APIからの生の応答データがチャット欄に表示されます。  
### トークン使用量の表示・累計  
 AIモデルの最大トークンに考慮した形でチャットができるように、最新の使用トークンを表示します。  
  
---  
## CHANGELOG  
すべてのリリース履歴は CHANGELOG.md に記載しています。  

---  
## ライセンス  
 本ソフトウェアは「Apache License 2.0」に準拠しています。

---  
## Author  
 -Yoichi-1984 (<yoichi.1984.engineer@gmail.com>)  
