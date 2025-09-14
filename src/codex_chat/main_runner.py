import os
import sys
import subprocess

def run():
    """
    Streamlitアプリケーションを安全なサブプロセスとして起動します。
    ワーキングディレクトリをプロジェクトルートに設定することで、
    Pythonのパッケージコンテキストを確実に維持し、相対インポートを解決します。
    """
    try:
        # このスクリプト(main_runner.py)の絶対パスを取得
        runner_path = os.path.abspath(__file__)
        # 'src/codex_chat' ディレクトリのパスを取得
        package_dir = os.path.dirname(runner_path)
        # 'src' ディレクトリのパスを取得
        src_dir = os.path.dirname(package_dir)
        # プロジェクトのルートディレクトリのパスを取得
        project_root = os.path.dirname(src_dir)

        # プロジェクトルートから見たmain.pyの相対パス
        # os.path.joinはOSに合わせて'/'または'\'を自動で使う
        relative_script_path = os.path.join("src", "codex_chat", "main.py")

        # 実行するコマンドを構築
        command = [sys.executable, "-m", "streamlit", "run", relative_script_path]
        
        print(f"プロジェクトルート: {project_root}")
        print(f"実行コマンド: {' '.join(command)}")

        # ワーキングディレクトリをプロジェクトルートに設定してコマンドを実行
        # これが最も重要な変更点です
        subprocess.run(command, check=True, cwd=project_root)

    except subprocess.CalledProcessError as e:
        print(f"Streamlitの実行中にエラーが発生しました: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nアプリケーションを終了します。")
        sys.exit(0)
    except Exception as e:
        print(f"予期せぬエラーが発生しました: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    run()
