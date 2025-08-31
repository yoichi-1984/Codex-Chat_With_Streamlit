import streamlit.web.cli as st_cli
from streamlit import __main__
import os
import sys

def run():
    # Streamlitが内部的に使用する引数リストを準備
    script_path = os.path.join(os.path.dirname(__file__), "main.py")
    sys.argv = ["streamlit", "run", script_path]

    # StreamlitのCLIを呼び出す
    sys.exit(__main__.main())

if __name__ == "__main__":
    run()
