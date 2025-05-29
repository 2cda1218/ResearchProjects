import speech_recognition as sr
from time import time
import threading
from datetime import datetime


def listen_util_ctrl(timeout_sec:int,silence_timeout = 10):
    r = sr.Recognizer()
    recognized_txt = ""

    def listen_thread():
        nonlocal recognized_txt
        with sr.Microphone(sample_rate = 16000) as source:
            print("話してください")
            audio = []
            start_time = time()

            # 無音検知
            while time() - start_time < timeout_sec:
                try:
                    #タイムアウト内でも録音続行
                    audio.append(r.listen(source,timeout = 1))
                    start_time = time() #タイムアウトの延長は5秒の方がいい？
                    print('音声取得成功,録音を続けます')

                except sr.WaitTimeoutError:
                    #音声無かった場合，タイムアウトの無音処理
                    if time() - start_time >= silence_timeout:
                        print("10秒の無音で終了します")
                        recognized_txt = "無音なので終了しました"
                        break
                    print("無音")
                except sr.UnknownValueError:
                    audio.append("音声が認識できません")
                except Exception as e: # sr.RequestError as e:だけだったけどそれ以外のExceptionもキャッチした方がより安定する?
                    recognized_txt = f"error has occured : {e}"

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

    #タイムアウト 機能してる？？調査の必要あり．
    listen_thread_instance.join(timeout = timeout_sec) #timeoutに関してかなり念入りだが冗長にも見える?

    if listen_thread_instance.is_alive():
        print("認識が終了できません．タイムアウトしました．")
        recognized_txt = "音声認識がタイムアウトしました．"

    #音声認識結果をファイルに保存
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    with open("output.txt","a",encoding = "utf-8") as file:
        file.write(f"\n[{current_time}] {recognized_txt}")
        print("テキストをoutput.txtに保存しました.")

        return recognized_txt
    
recognized_text = listen_util_ctrl(30,silence_timeout=10)