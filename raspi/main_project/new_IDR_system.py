import RPi.GPIO as GPIO
# from gpiozero import Servo 先代スクリプトに入っていたが使用されていないモジュール
from time import sleep,time
import serial
import speech_recognition as sr
import threading
from datetime import datetime
import sys
import requests
import os
import tkinter as tk
from tkinter import scrolledtext
import logging
from dotenv import load_dotenv

# initialize logging
logging.basicConfig(level=logging.DEBUG, format='[%(asctime)s] [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger(__name__)
logger.info("loggingを開始します")

# initialize env
logger.info('.envをロードします')

load_dotenv()
LINE_TOKEN = os.getenv("LINE_TOKEN")
GEMINI_TOKEN = os.getenv("GEMINI_TOKEN")

logger.info('TOKENをロードしました')

# initialize GPIO
logger.info('GPIOの初期化開始...')

GPIO.setmode(GPIO.BCM)
servo_pin = 9
GPIO.setup(servo_pin,GPIO.OUT)
pwm = GPIO.PWM(servo_pin,50)
pwm.start(0)

logger.info('GPIOの初期化成功')

# initialize Arduino's Serial
logger.info('シリアル通信の初期化開始...')

ser = serial.Serial('/dev/tty/ACM0', 9600)
ser.flush()
sleep(2)

logger.info('シリアル通信の初期化成功')

# initialize RAG
# 完成待ち
logger.info('RAGの初期化開始...')

#code

logger.info('RAGの初期化成功')


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
def listen_util_ctrl(timeout_sec:int,silence_timeout:int,interval:float):
    r = sr.Recognizer()
    recognized_txt = ""
    start_time = time()

    def listen_thread():
        nonlocal recognized_txt
        nonlocal start_time
        start_time  = time()
        with sr.Microphone(sample_rate = 16000) as source:
            logger.info("音声取得を開始")
            audio = []

            # 無音検知
            while time() - start_time < timeout_sec:
                try:
                    #タイムアウト内でも録音続行
                    audio.append(r.listen(source,timeout = 1,phrase_time_limit=10))
                    start_time = time() #タイムアウトの延長は5秒の方がいい？
                    logger.info('音声取得成功,録音を続けます')

                except sr.WaitTimeoutError:
                    #音声無かった場合，タイムアウトの無音処理
                    if time() - start_time >= silence_timeout:
                        print("10秒の無音で終了します")
                        recognized_txt = "無音なので終了しました"
                        break
                    print("無音")
                except sr.UnknownValueError:
                    audio.append("音声が認識できません")
                    #保険に時間延長入れた方がいい？
                except sr.RequestError as e:
                    recognized_txt = f"サービスに接続できませんでした : {e}"
                    break
                except Exception as e: # sr.RequestError as e:だけだったけどそれ以外のExceptionもキャッチした方がより安定する?
                    recognized_txt = f"error has occured : {e}"
                    break

        if audio:
            recognized_txt = ''
            for data in audio:
                if isinstance(data, sr.AudioData):
                    try:
                        text = r.recognize_google(data, language = "ja-jp")
                        recognized_txt += f' {text}'
                        print("認識されたテキスト：",text)
                    except Exception as e:
                        recognized_txt += f"認識エラー:{e}"
                else:
                    recognized_txt += f' {data}'
        print(f'最終認識:{recognized_txt}')

    #認識スレッド開始
    listen_thread_instance = threading.Thread(target = listen_thread)
    listen_thread_instance.start()

    #タイムアウト 機能はしているがシステムに上手くいかなさそう
#    listen_thread_instance.join(timeout = timeout_sec)
#    if listen_thread_instance.is_alive():
#        print("認識が終了できません．タイムアウトしました．")
#        recognized_txt = "音声認識スレッドがタイムアウトしました．"

    while listen_thread_instance.is_alive():
        listen_thread_instance.join(timeout = interval)
        if time() - start_time >= timeout_sec:
            print("認識が終了できません．タイムアウトしました.")
            recognized_txt = "音声認識スレッドがタイムアウトしました."
            break

    #音声認識結果をファイルに保存
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    with open("output.txt","a",encoding = "utf-8") as file:
        file.write(f"\n[{current_time}] {recognized_txt}")
        print("テキストをoutput.txtに保存しました.")

        return recognized_txt

    #認識スレッド開始
    listen_thread_instance = threading.Thread(target = listen_thread)
    listen_thread_instance.start()

    #タイムアウト
    # スレッドの強制終了はしていないが認識自体は無理やり生成文章を作成することで強制終了している．
    # スレッド自体が10秒しか存続できないため10秒を越える録音には対応できない．
    # いずれにしてもタイムアウトの調整には現場での一回の通話時間がどれくらいあるのかを調査することで，
    # 設定する必要があるという判断(ただし，認識のテスト時は一旦10秒で試してみる)
    listen_thread_instance.join(timeout = timeout_sec)

    if listen_thread_instance.is_alive():
        print("認識が終了できません．タイムアウトしました．")
        recognized_txt = "音声認識がタイムアウトしました．"

    #音声認識結果をファイルに保存
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    with open("output.txt","a",encoding = "utf-8") as file:
        file.write(f"\n[{current_time}] {recognized_txt}")
        print("テキストをoutput.txtに保存しました.")

        return recognized_txt
    
# recognized_text = listen_util_ctrl(30,silence_timeout=10,0.5)

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
def output_res(result:str):
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
                "text": result
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
                    
                    play_sound('sound_files/guide.wav') # 'file_pathに案内用の音声パスを設定
                    
                    is_need_rec = True
                    
                    while is_need_rec:
                        rec_text = listen_util_ctrl(30,5,0.5)
                    
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