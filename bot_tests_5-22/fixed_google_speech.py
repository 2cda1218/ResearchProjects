import speech_recognition as sr
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
            timeout_check = False

            # 無音検知
            while audio is None:
                try:
                    #タイムアウト内でも録音続行
                    audio = r.listen(source,timeout = 10)
                    print('音声取得成功')
                    break
                except sr.WaitTimeoutError:
                    #音声無かった場合，タイムアウトの無音処理
                    if timeout_check:
                        print("10秒の無音または20秒以上無言なので終了します")
                        recognized_txt = "無音なので終了しました"
                        break
                    print("無音")
                    timeout_check = True
                except sr.UnknownValueError:
                    recognized_txt = "音声が認識できません"
                    break
                except sr.RequestError as e:
                    recognized_txt = f'RequestError:{e}'
                except Exception as e:
                    recognized_txt = f"Some error has occured : {e}"

        if audio:
            try:
                recognized_txt = r.recognize_google(audio, language = "ja-jp")
                print("認識されたテキスト：",recognized_txt)
            except Exception as e:
                recognized_txt = f"認識エラー:{e}"

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
    
recognized_text = listen_util_ctrl(30,silence_timeout=10)