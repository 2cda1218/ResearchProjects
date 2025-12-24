from gtts import gTTS
import os
import logging

logger = logging.getLogger(__name__)

REQUIRED_WAV_FILES = [
    "guide.wav",
    "kesseki_kakunin.wav",
    "kesseki_kakutei.wav",
    "chikoku_kakunin.wav",
    "chikoku_kakutei.wav",
    "error.wav",
    "retry.wav"
    ]

def Generate_Guide(file_type:str,path:str):
    if file_type == "guide.wav":
        tts = gTTS("こちらは土屋研究室です．ご用件をお話しください．",lang="ja")
    elif file_type == "kesseki_kakunin.wav":
        tts = gTTS("欠席のご連絡で間違いありませんか？",lang="ja")
    elif file_type == "kesseki_kakutei.wav":
        tts = gTTS("欠席ですね．わかりました．他にご用件はございますか？",lang="ja")
    elif file_type == "chikoku_kakunin.wav":
        tts = gTTS("遅刻のご連絡で間違いありませんか？",lang="ja")
    elif file_type == "chikoku_kakutei.wav":
        tts = gTTS("遅刻ですね．わかりました．他にご用件はございますか？",lang="ja")
    elif file_type == "error.wav":
        tts = gTTS("システムでエラーが発生しました．担当者にお繋ぎしますので，しばらくお待ちください．",lang="ja")
    elif file_type == "retry.wav":
        tts = gTTS("認識に失敗しました．お手数おかけしますが，もう一度お話ください．",lang="ja")
    
    tts.save(f"{path}")

def check_wav_files():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    guide_dir = os.path.join(script_dir, "guide")
    logger.info("固定返答の整合性検証を開始します")

    if not os.path.exists(guide_dir):
        os.makedirs(guide_dir)
        logger.info("guideディレクトリを作成しました")
    
    for wav_file in REQUIRED_WAV_FILES:
        wav_path = os.path.join(guide_dir,wav_file)

        if not os.path.exists(wav_path):
            logger.warning(f"{wav_file}が見つかりません")
            logger.warning("ファイルを生成します")
            Generate_Guide(wav_file,wav_path)
        
        else:
            logger.info(f"{wav_file}は存在します")
    logger.info("整合性チェックを終了します")

check_wav_files()