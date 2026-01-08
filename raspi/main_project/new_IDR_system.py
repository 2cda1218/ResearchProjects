import chromadb
from datetime import datetime
from dotenv import load_dotenv
import fasttext
from google import genai as gemini
from google.genai import types
from gtts import gTTS
import logging
import multiprocessing as mp
import os
import PyPDF2
import requests
import RPi.GPIO as GPIO
from sentence_transformers import SentenceTransformer as ST
import serial
import speech_recognition as sr
import threading
from time import sleep, strftime
import tkinter as tk
from tkinter import scrolledtext
import uuid

import sound_files.create_guide as cguide
import datasets.train_model as train

# path登録
MAIN_DIR = os.path.dirname(os.path.abspath(__file__))
PDF_PATH = os.path.join(MAIN_DIR,"datasets","schooltest.pdf")
MODEL_PATH = os.path.join(MAIN_DIR,"datasets","ft_model.bin")
GUIDE_PATH = os.path.join(MAIN_DIR,"sound_files","guide")
GENERATE_SOUND_PATH = os.path.join(MAIN_DIR,"sound_files","generate")

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

# 分類の初期化
logger.info('分類機能の初期化開始...')
embedder = ST("all-MiniLM-L6-v2")

chroma_client = chromadb.Client()
try:
    chroma_client.delete_collection("schooltest.pdf")
except:
    logger.info("該当するデータは見つかりませんでした")
    pass
collection = chroma_client.get_or_create_collection("schooltest.pdf")

gemini_client = gemini.Client(api_key=GEMINI_TOKEN)
gemini_model = "gemini-2.5-flash-lite"
gemini_config = types.GenerateContentConfig(temperature=0.7,max_output_tokens=512)

check_model = mp.Process(train.train_model)
check_model.start()

logger.info('分類機能の初期化成功')


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

def load_pdf():
    logger.info("PDFのロードを開始します")
    with open(PDF_PATH,"rb") as f:
        reader = PyPDF2.PdfReader(f)
        texts = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                texts.append(text.strip())
    chunks = []
    for text in texts:
        while len(text):
            chunks.append(text[:500])
            text = text[500:]
        if text:
            chunks.append(text)
    for chunk in chunks:
        emb = embedder.encode(chunk).tolist()
        collection.add(
            ids = [str(uuid.uuid4())],
            documents = [chunk],
            embeddings = [emb]
        )
    logger.info("PDFのロード終了")

# サーボ回転
def set_servo_angle(angle:int):
    duty = angle / 18 + 2
    pwm.ChangeDutyCycle(duty)
    sleep(0.5)

# 音声再生
def play_sound(sound_path:str):
    os.system(f'aplay {sound_path}') # 'aplay {sound_path} &'で非同期で再生できるが必要あるのか? mp3再生の場合はaplayをmpg321にする

# 音声認識
def listen_util_ctrl():
    r = sr.Recognizer()
    loop_count = 0
    with sr.Microphone(sample_rate = 16000) as source:
        while loop_count < 3:
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
                play_sound(GUIDE_PATH,"retry.wav")
            except sr.UnknownValueError:
                # 認識不可の時
                audio.extend(["音声が認識できません","error"])
                logger.warning("認識が不可能でした")
                play_sound(GUIDE_PATH,"retry.wav")
            
            except sr.RequestError as e:
                # 接続不可の時
                audio.extend([f"サービスに接続できませんでした : {e}","error"])
                logger.warning("サービスへの接続に失敗しました",exc_info=True)
            
            except Exception as e:
                # その他のエラー
                audio.extend([f"エラーが発生しました : {e}","error"])
                logger.warning("エラーが発生しました",exc_info=True)
            finally:
                loop_count += 1
                logger.info(f"{loop_count}回目の録音に失敗しました")
        else:
            logger.info("異常終了しました")

    if audio[1] == "success":
        try:
            audio[0] = r.recognize_google(audio[0], language = "ja-jp")
            logger.info("音声認識に成功")
        except:
            audio[0] = "認識エラーが発生しました"
            audio[1] = "error"
            logger.warning("認識エラーが発生しました")
    logger.info(f'最終結果:{audio[0]}')

    #音声認識結果をファイルに保存
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    with open("output.txt","a",encoding = "utf-8") as file:
        file.write(f"\n[{current_time}] {audio[0]}")
        logger.info("テキストをoutput.txtに保存しました.")

        return audio

# 分類
def predict(user_input:str):
    logger.info('分類を開始します')
    model = fasttext.load_model(MODEL_PATH)
    labels, scores = model.predict(user_input,k=2)
    label1, score1 = labels[0].replace("__label__",""), scores[0]
    label2, score2 = labels[1].replace("__label__",""), scores[0]
    
    logger.info(f"分類結果\nLabels: Label1 [{label1}], Label2 [{label2}]\nScores: Score1 [{score1}], Score2 [{score2}]\n分類時間: {end_time - start_time}")

    if score1 >= 0.7 and abs(score1 - score2) >= 0.2:
        logger.info(f"定型処理:{label1}")
        return "pattern" , label1
    
    elif label1 == "その他":
        logger.info(f"非定型処理:{label1}")
        return "non-pattern" , label1
    else:
        logger.info("曖昧処理")
        return "non-pattern" , "曖昧"

# 定型
def pattern_res(label:str):
    logger.info('定型処理を開始')
    loop_status = 0
    while loop_status < 3:
        if label == "遅刻":
            status = "chikoku"
        else:
            status = "kesseki"
        logger.info(f"{label}の処理を開始")
        logger.info(f"{label}の確認")
        play_sound(os.path.join(GUIDE_PATH,f"{status}_kakunin.wav"))
        sleep(0.5)
        play_sound(os.path.join(GUIDE_PATH,"yes_or_no.wav"))
        rec_text = listen_util_ctrl()
        if rec_text[1] == "error":
            logger.info("エラーが発生") #もうちょっと考える
            return
        if rec_text[0] == "はい":
            logger.info(f"{label}が確定")
            play_sound(os.path.join(GUIDE_PATH,f"{status}_kakutei.wav"))
            send_line(f"システムが{label}を判断しました.")
            return
        elif rec_text[0] == "いいえ":
            logger.info(f"{label}ではない")
            loop_status += 1
            if label == "遅刻":
                label = "欠席"
            else:
                label = "遅刻"
        else:
            logger.info("はい・いいえ以外が判定されています")
    else:
        logger.info("いたずら，または遅刻でも欠席でもない可能性があります.")
        send_line("いたずら，または遅刻でも欠席でもない連絡です.")
    return

# 非定型
def non_pattern_res(text:str):
    logger.info('非定型処理を開始')
    def gemini_answer(input_txt:str):
        querry_vec = embedder.encode(input_txt).tolist()
        results = collection.query(query_embeddings=[querry_vec], n_results=3)
        context = "\n".join(results["documents"][0])
        prompt = (
            "あなたは「学校の教師」です．\n"
            "【学校情報】の内容に従って，【質問】セクションの内容に対して丁寧な回答を簡潔に作成してください．\n"
            "該当する情報が存在しない場合は「すみません，この質問にはお答えすることができません」と答えてください．"
            "助言，補足説明，前置きは不要です．\n"
            "回答が可能な場合は，単語のみでの回答はせずに文章を作成してください．\n"
            "質問内容が「緊急」と判断される場合は「担当に交代します」と答えてください\n"
            "質問内容から遅刻または欠席と判断できる場合は「遅刻」または「欠席」とだけ回答してください．\n"
            "回答の際に情報が不足している場合に，推測や一般知識によって補完をしてはいけない.\n"
            f"【学校情報】\n{context}\n"
            f"【質問】\n{text}"
        )
        try:
            response = gemini_client.models.generate_content(
                model = gemini_model,
                contents = prompt,
                config = gemini_config
            )
            if not (response.text or "").strip():
                logger.error("回答を生成できませんでした．")
                return "error","回答を生成することができませんでした．"
            return "success",response.text.strip()
        except Exception as e:
            logger.error("エラーが発生しました",exc_info=True)
            return "error","Geminiからの応答にエラーがあります．"
        
    def gtts_gen(gen_text:str):
        logger.info("gTTSでの音声生成処理を開始")
        lang = "ja"
        tts = gTTS(gen_text,lang=lang)
        gen_file_name = f"{strftime('%Y%m%d_%H%M%S')}.wav"
        sound_path = os.path.join(GENERATE_SOUND_PATH,gen_file_name)
        logger.info(f'{sound_path}に生成した音声を保存しました')
        tts.save(sound_path)
        logger.info('生成した音声を再生')
        play_sound(sound_path)
        logger.info("使用済みの音声を削除")
        os.remove(sound_path)

    generate_status , output_text = gemini_answer(text)
    if generate_status == "success":
        if output_text == "遅刻" or "欠席":
            logger.info(f"{output_text}とGeminiが判断しました")
            pattern_res(output_text)
            return
        elif output_text == "緊急":
            logger.info("緊急と判断されたため担当に変更")
        gtts_gen(output_text)
    else:
        play_sound(os.path.join(GUIDE_PATH,"error.wav"))
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
    # PDFのロード
    load_pdf()

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
                    
                    play_sound(os.path.join(GUIDE_PATH,"guide.wav"))

                    rec_text, status = listen_util_ctrl()
                    if status == "error":
                        logger.info("サービスへの接続またはその他のエラーによってシステムを実行できません")
                        play_sound(GUIDE_PATH,'error.wav')
                    send_line(f"【認識した音声】\n{rec_text}")
                    
                    # 分類処理
                    pattern , label = predict(rec_text)

                    
                    # 分類→定型or非定型(rag()で分類→命名は変更の可能性あり)
                    if pattern == 'pattern':
                        pattern_res(label)
                    else:
                        non_pattern_res(rec_text)
                    
                    set_servo_angle(90)
                    
                    logger.info('自動応答システム終了')
                    sleep(5)
                    
            except KeyboardInterrupt:
                logger.info('システムを終了します')
                cont_sys = False
            except Exception as e:
                logger.error(f'エラーが起きました: {e}', exc_info=True)
            finally:
                except_finally(pwm=pwm)


if __name__ == '__main__':
    main()