#!/bin/bash

cd ~/Desktop
# 仮想環境作成
if [ !-d "myenv"]; then
    echo "仮想環境の作成"
    python3 -m venv myenv || {echo "仮想環境作成に失敗"; exit 1;}
fi

# 仮想環境アクティベート
echo "仮想環境をアクティベート"
source myenv/bin/activate || {echo "仮想環境のアクティベートに失敗"; exit 1;}

# 必要なパッケージをインストール
if [ -f "requirements.txt"]; then
    echo "必要なパッケージをインストール"
    pip install -r requirements.txt || {echo "パッケージインストール失敗";exit 1;}
fi

# py script
echo "pyスクリプトを実行"
python .py || {echo "スクリプト実行に失敗";exit 1;}

# 仮想環境のディアクティベート
deactivate