import chromadb
from datetime import datetime
from dotenv import load_dotenv
import logging
import os
import requests
import RPi.GPIO as GPIO
from sentence_transformers import SentenceTransformer as ST
import serial
import speech_recognition as sr
import sys
import threading
from time import sleep
import tkinter as tk
from tkinter import scrolledtext

import sound_files.create_guide as cguide


# loggingの初期化
logging.basicConfig(level=logging.DEBUG, format='[%(asctime)s] [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger(__name__)
logger.info("loggingを開始します")

# .envロード
logger.info('.envをロードします')

load_dotenv()
LINE_TOKEN = os.getenv("LINE_TOKEN")
GEMINI_TOKEN = os.getenv("GEMINI_TOKEN")

logger.info('TOKENをロードしました')

# GPIO初期化
logger.info('GPIOの初期化開始...')

GPIO.setmode(GPIO.BCM)
servo_pin = 9
GPIO.setup(servo_pin,GPIO.OUT)
pwm = GPIO.PWM(servo_pin,50)
pwm.start(0)

logger.info('GPIOの初期化成功')

# シリアル通信の初期化
logger.info('シリアル通信の初期化開始...')

ser = serial.Serial('/dev/tty/ACM0', 9600)
ser.flush()
sleep(2)

logger.info('シリアル通信の初期化成功')

# 固定応答ファイル整合性確認 threadingで非同期化
file_check_thread = threading.Thread(target=cguide.check_wav_files)
file_check_thread.start()

# RAGの初期化
logger.info('分類モデルの初期化開始...')

embedder = ST("all-MiniLM-L6-v2")

chroma_client = chromadb.Client()
collection = chroma_client.get_or_create_collection("school_pdf_docs")

logger.info('分類モデルの初期化成功')


# tkinter GUI作成
def create_gui():
    root = tk.Tk()
    root.title("受信メッセージ")

    # スクロール可能なテキストボックス
    text_area = scrolledtext.ScrolledText(root, width=50, height=10, wrap=tk.WORD)
    text_area.pack(padx=10,pady=10)

    file_path = 'output.txt'

    # 定期的な更新
    def auto_reload():
        last_line = get_last_line(file_path=file_path)
        text_area.delete(1.0, tk.END) # テキストエリアのクリア
        text_area.insert(tk.END, last_line)
        root.after(5000, auto_reload)

    # 手動更新
    reload_button = tk.Button(root, text='更新', command=auto_reload)
    reload_button.pack(pady=5)

    # 定期更新開始
    auto_reload()

    root.mainloop()

# 最終行取得
def get_last_line(file_path:str):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            return lines[-1] if lines else 'ファイルが空です'
    except FileNotFoundError:
        return '指定のファイルがみつかりません'

# サーボ回転
def set_servo_angle(angle:int):
    duty = angle / 18 + 2
    pwm.ChangeDutyCycle(duty)
    sleep(0.5)

# 音声再生
def play_sound(sound_path:str):
    os.system(f'aplay {sound_path}') # 'aplay {sound_path} &'で非同期で再生できるが必要あるのか? mp3再生の場合はaplayをmpg321にする

# 音声認識 差し替える必要あり
def listen_util_ctrl():
    r = sr.Recognizer()
    
    with sr.Microphone(sample_rate = 16000) as source:
        logger.info("音声取得を開始")
        audio = []
        # 無音検知
        try:
            #タイムアウト内でも録音続行
            audio.extend([r.listen(source,timeout = 5),"success"])# 5秒無音でタイムアウト
            logger.info('音声取得成功')

        except sr.WaitTimeoutError:
            # 無音の場合
            audio.extend(["無音","error"])
            logger.warning("無音でした")
        except sr.UnknownValueError:
            # 認識不可の時
            audio.extend(["音声が認識できません","error"])
            logger.warning("認識が不可能でした")
            
        except sr.RequestError as e:
            # 接続不可の時
            audio.extend([f"サービスに接続できませんでした : {e}","connect-error"])
            logger.warning("サービスへの接続に失敗しました",exc_info=True)
            
        except Exception as e: # sr.RequestError as e:だけだったけどそれ以外のExceptionもキャッチしておく
            audio.extend([f"エラーが発生しました : {e}","except-error"])
            logger.warning("エラーが発生しました",exc_info=True)

    if audio[1] == "success":
        try:
            audio[0] = r.recognize_google(audio[0], language = "ja-jp")
            logger.info("音声認識に成功")
        except:
            audio[0] = "認識エラーが発生しました"
            logger.warning("認識エラーが発生しました")
    logger.info(f'最終結果:{audio[0]}')

    #音声認識結果をファイルに保存
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    with open("output.txt","a",encoding = "utf-8") as file:
        file.write(f"\n[{current_time}] {audio[0]}")
        logger.info("テキストをoutput.txtに保存しました.")

        return audio

# 分類
def rag():
    logger.info('分類を開始します')
    return

# 定型
def pattern_res():
    logger.info('定型処理を開始')
    return

# 非定型
def non_pattern_res():
    logger.info('非定型処理を開始')
    return

# LINE
def send_line(ctx:str):
    logger.info('LINEへの出力を開始します')
    url = 'https://api.line.me/v2/bot/message/broadcast'
    headers = {
        'Authorization': f'Bearer {LINE_TOKEN}',
        'Content-Type': 'application/json'
    }
    payload = {
        "messages": [
            {
                "type": "text",
                "text": ctx
            }
        ]
    }
    response = requests.post(url,headers=headers, json=payload)

    if response.status_code == 200:
        logger.info('メッセージ送信に成功')
    else:
        logger.warning(f'エラーが発生しました\nステータスコード:{response.status_code}\n{response.text}')

# 異常終了
def except_finally():
    pwm.stop()
    GPIO.cleanup()

def main():
    cont_sys = True

    # initialize tkinter
    logger.info('tkinterを起動...')
    try:
        gui_thread = threading.Thread(target=create_gui)
        gui_thread.start()
    except Exception as e:
        logger.error(f'エラーが起きました: {e}', exc_info=True)
        return
    finally:
        except_finally()
    
    # Main System
    while cont_sys:
        set_servo_angle(90)
        if ser.in_waiting > 0:
            try:
                if ser.readline().decode('utf-8').rstrip() == '1':
                    logger.info('着信あり')
                    set_servo_angle(0)
                    # 自動応答システム本体↓↓↓
                    logger.info('自動応答システム起動')
                    
                    play_sound('sound_files/guide/guide.wav')
                    
                    is_need_rec = True
                    loop_count = 0

                    while is_need_rec:
                        rec_text, status = listen_util_ctrl()
                        if status == "error":
                            if loop_count < 3:
                                loop_count += 1
                                logger.info(f"{loop_count}回目の無音または認識失敗をしました")
                                play_sound("sound_files/guide/retry.wav")
                                continue

                            logger.info("無音または認識困難の可能性がある着信です")
                            play_sound('sound_files/guide/error.wav')
                            break

                        elif status == "connect-error" or "other-error":
                            logger.info("サービスへの接続またはその他のエラーによってシステムを実行できません")
                            play_sound('soun_files/guide/error.wav')
                            break
                        
                        send_line(f"【認識した音声】\n{rec_text}")
                        
                        # 分類処理
                        result = rag(rec_text)

                    
                    # 分類→定型or非定型(rag()で分類→命名は変更の可能性あり)
                    result = rag()
                    # 定型処理(pattern_res()で続きを処理→命名は変更の可能性あり)
                    # 非定型処理(non_pattern_res()で続きを処理→命名は変更の可能性あり)
                    if result[0] == 'pattern':
                        pattern_res()
                    elif result[0] == 'non-pattern':
                        non_pattern_res()
                    else:
                        logger.warning('分類に異常あり')
                    
                    set_servo_angle(90)
                    
                    logger.info('自動応答システム終了')
                    sleep(5)
                    output_res()
            except KeyboardInterrupt:
                logger.info('システムを終了します')
                cont_sys = False
            except Exception as e:
                logger.error(f'エラーが起きました: {e}', exc_info=True)
            finally:
                except_finally(pwm=pwm)


if __name__ == '__main__':
    main()