from gtts import gTTS
import os
import logging

logger = logging.getLogger(__name__)

REQUIRED_MP3_FILES = [
    "guide.mp3",
    "kesseki_kakunin.mp3",
    "kesseki_kakutei.mp3",
    "chikoku_kakunin.mp3",
    "chikoku_kakutei.mp3",
    "error.mp3",
    "retry.mp3",
    "yes_or_no.mp3",
    "end.mp3"
    ]

def Generate_Guide(file_type:str,path:str):
    if file_type == "guide.mp3":
        txt = "こちらは土屋研究室です．ご用件をお話しください．"
    elif file_type == "kesseki_kakunin.mp3":
        txt = "欠席のご連絡で間違いありませんか？"
    elif file_type == "kesseki_kakutei.mp3":
        txt = "欠席ですね．わかりました．"
    elif file_type == "chikoku_kakunin.mp3":
        txt = "遅刻のご連絡で間違いありませんか？"
    elif file_type == "chikoku_kakutei.mp3":
        txt = "遅刻ですね．わかりました."
    elif file_type == "error.mp3":
        txt = "システムでエラーが発生しました．担当者にお繋ぎしますので，しばらくお待ちください．"
    elif file_type == "retry.mp3":
        txt = "認識に失敗しました．お手数おかけしますが，もう一度お話ください．"
    elif file_type == "yes_or_no.mp3":
        txt = "ハイかイイエでお答えください．"
    elif file_type == "end.mp3":
        txt = "お電話ありがとうございました．"
    tts = gTTS(txt,lang="ja")
    tts.save(f"{path}")

def check_mp3_files():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    guide_dir = os.path.join(script_dir, "guide")
    logger.info("固定返答の整合性検証を開始します")

    if not os.path.exists(guide_dir):
        os.makedirs(guide_dir)
        logger.info("guideディレクトリを作成しました")
    
    for mp3_file in REQUIRED_MP3_FILES:
        mp3_path = os.path.join(guide_dir,mp3_file)

        if not os.path.exists(mp3_path):
            logger.warning(f"{mp3_file}が見つかりません")
            logger.warning("ファイルを生成します")
            Generate_Guide(mp3_file,mp3_path)
        
        else:
            logger.info(f"{mp3_file}は存在します")
    logger.info("整合性チェックを終了します")

check_mp3_files()