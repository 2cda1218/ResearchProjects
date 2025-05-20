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
            audio = None
            start_time = time()

            # 無音検知
            while time() - start_time < timeout_sec:
                try:
                    #タイムアウト内でも録音続行
                    audio = r.listen(source,timeout = 1)
                    start_time = time() #タイムアウトの延長
                    print('音声取得成功')
                    break #これがあるとwhileのループの必要性がない...? そもそもr.listen(source,timeout = 10)にすればもっと簡素化できる?
                except sr.WaitTimeoutError:
                    #音声無かった場合，タイムアウトの無音処理
                    if time() - start_time >= silence_timeout:
                        print("10秒の無音で終了します")
                        recognized_txt = "無音なので終了しました"
                        break
                    print("無音")
                except sr.UnknownValueError:
                    recognized_txt = "音声が認識できません"
                    break
                except Exception as e: # sr.RequestError as e:だったけどそれ以外のExceptionもキャッチした方がより安定する?
                    recognized_txt = f"error has occured : {e}"

        if audio:
            try:
                recognized_txt = r.recognize_google(audio, language = "ja-jp") # もう一回コード確認してくる
                print("認識されたテキスト：",recognized_txt)
            except Exception as e:
                recognized_txt = f"認識エラー:{e}"

    #認識スレッド開始
    listen_thread_instance = threading.Thread(target = listen_thread)
    listen_thread_instance.start()

    #タイムアウト
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