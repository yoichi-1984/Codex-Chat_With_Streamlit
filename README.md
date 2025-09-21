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
 ├── env/  
 │ └── *.env # モデル設定ファイル (選択可能)  
 ├── src/  
 │ 　└── codex_chat/  
 │ 　　├── __init__.py  
 │ 　　├── main.py # Streamlit アプリケーション本体  
 │ 　　├── main_runner.py # CLI からの起動用ラッパー  
 │ 　　├── utils.py # ヘルパー関数群  
 │ 　　├── config.py # 定数・テキスト定義  
 │ 　　└── prompts.yaml # プロンプト定義  
 ├── .gitignore  
 ├── LICENSE  
 ├── README.md  
 ├── activate.bat  
 ├── pyproject.toml  
 ├── sample_of_env.txt  
 ├── requirements.txt  
 ├── install.bat  
 ├── START.bat  
 └── CHANGELOG.md  
  
---  
## インストール例  
    
```bash  
git clone https://github.com/ユーザ名/codex-mini.git  
cd codex-mini  
python3 -m venv .env  
source .env/bin/activate  
python.exe -m pip install --upgrade pip  
python.exe -m pip install --upgrade pip setuptools  
pip install -r requirements.txt  
```  
  
---  
## 環境設定  
  
プロジェクトルートに env/ ディレクトリを作成し、.env ファイルを配置してください。  
  
AZURE_OPENAI_KEY=<your_api_key>  
AZURE_OPENAI_ENDPOINT=<your_endpoint>  
AZURE_OPENAI_DEPLOYMENT=<deployment_name>  
AZURE_OPENAI_API_VERSION=<api_version>  
MAX_TOKEN=<max_token>  
  
---  
## 使い方    
  
pyproject.tomlに従ってインストール。  
pip install -e .  
その後は  
仮想環境で「codex-chat」と打ち込めば、内部的にstreamlit run で main_runner.py が実行される。  
  
他には  
python -m src.codex_chat.main_runner  
や  
streamlit run src/codex_chat/main.py  
でも起動できます。  
  
---  
## 主な機能  
### AIモデルの選択:  
 サイドバー最上部に.envファイルの選択リストがあります。使いたいモデル(.env)を選択してください。  
### AIの役割設定:  
 最初のチャット画面で、AIの役割を定義するシステムプロンプトを入力し、「この役割でチャットを開始する」ボタンをクリックします。  
### マルチ Canvas コードエディタ（最大 20）:  
 Canvasを用いてコードをAIに効率よく読ませることができます。マルチコード機能を有効にすることで、最大20個までCanvasを拡張することも可能です。  
### 会話履歴の JSON ダウンロード／アップロード:  
 AIの役割、チャット履歴、Canvasの内容すべてをJSON形式でダウンロードし、途中再開が可能です。  
 チャット再開時には、AIモデルの選択情報、Canvasに記述したコード、チャット内容すべて再開できます。  
### 応答ストリーミング＆停止ボタン:  
 APIからの応答をリアルタイム表示し、途中停止が可能。  
### トークン使用量の表示・累計:  
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
