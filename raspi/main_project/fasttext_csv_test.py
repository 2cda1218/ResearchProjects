import fasttext
import pandas as pd
import os
import chromadb
from sentence_transformers import SentenceTransformer
import google.generativeai as genai
from gtts import gTTS
import PyPDF2
import csv
from datetime import datetime
import openai
from openai import OpenAI

# ===== 会話ログ保存関数 ===== 履歴は既存システムにもあるから多分いらない
def save_conversation_log(user_input, log_label, score, log_response):
    log_file = "conversation_log.csv"
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 追記モードでCSVに書き込み
    with open(log_file, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([now, user_input, log_label, f"{score:.2f}", log_response])
        
import requests

# Teams Webhook URL teamsは動かせている？
TEAMS_WEBHOOK_URL = "https://utokai.webhook.office.com/webhookb2/442834dd-3d07-4e81-8059-b4352e75bd0c@8283096f-bcce-44d0-8f54-e57aa84d1a22/IncomingWebhook/03c1777ddb7542ccb1161190bfc1581a/aad18c1b-d1c6-46b2-adcc-3c163218c4d5/V2EqcJ0hRlkvsr1ECTerA_IHrpZ5crAXa1CVZGeJ7RKto1"

def send_conversation_to_teams(user_input, log_label, score, log_response):
    log_text = (
        f"**ユーザー入力:** {user_input}\n"
        f"**判定ラベル:** {log_label} (score={score:.2f})\n"
        f"**AI応答:** {log_response}"
    )

    payload = {
        "text": log_text  # Teamsは"text"キーで送る
    }

    requests.post(TEAMS_WEBHOOK_URL, json=payload)
# ====== Gemini APIキー設定 ======
# あなたのAPIキーを直接書かず、環境変数から取得するのが安全です
# 例: setx GEMINI_API_KEY "AIzaSyXXXXX..." （Windows PowerShellで設定）
os.environ["GEMINI_API_KEY"] = os.getenv("GEMINI_API_KEY", "AIzaSyDHaZ0T9vm5KSqbJgKt93yYiAdQJQ_K1xI")

# OpenAI互換エンドポイントを指定 OpenAIモジュールでやっているけどgoogleのやつとの違いは？
client = OpenAI(
    api_key=os.environ["GEMINI_API_KEY"],
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

# ====== SentenceTransformer & Chroma 設定 ======
embedder = SentenceTransformer("all-MiniLM-L6-v2")

chroma_client = chromadb.Client()
# get_or_create_collection()の引数は何？
collection = chroma_client.get_or_create_collection("school_pdf_docs")

print("✅ Gemini API と Chroma 初期化完了")

def gemini_answer_from_pdf(question):
    query_vec = embedder.encode(question).tolist()
    results = collection.query(query_embeddings=[query_vec], n_results=3)
    context = "\n".join(results["documents"][0])

    # promptの冒頭に「東海大学」としているけどこれはドキュメントから回収できるようにしたほうが良い？
    prompt = f"""
あなたは「東海大学」の教師です。
以下の学校情報に基づいて、ユーザーの質問に丁寧に答えてください。
情報がない場合は「分かりません」と返してください。

【学校情報】
{context}

【質問】
{question}
"""

    try:
        response = client.chat.completions.create(
            model="gemini-2.5-flash",
            messages=[
                {"role": "system", "content": "あなたは教育者です。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=512,
        )

        # ✅ content が None の場合に備えてフォールバック処理を追加
        answer = None
        if hasattr(response.choices[0].message, "content") and response.choices[0].message.content:
            answer = response.choices[0].message.content.strip()
        elif hasattr(response, "output_text") and response.output_text:
            answer = response.output_text.strip()
        else:
            answer = "すみません、回答を生成できませんでした。"

    except Exception as e:
        answer = f"エラーが発生しました: {str(e)}"

    # ===== 音声出力 =====
    print(f"\n=== Geminiの回答 ===\n{answer}")
    tts = gTTS(text=answer, lang='ja')
    tts.save("answer.mp3")
    os.system("start answer.mp3")

    return answer




# ===== CSVから学習データを読み込む =====
df = pd.read_csv("C:/Users/naoma/Downloads/senior_thesis/bunrui_test/gakusyudata.csv")  # ファイル名に注意

# ===== 一時的な fastText 形式ファイルに変換（__label__付き） =====
with open("train.txt", "w", encoding="utf-8") as f:
    for _, row in df.iterrows():
        label = row["label"]
        text = row["text"]
        f.write(f"__label__{label} {text}\n") # 結局後で__label__をreplace()使って外しているけど__label__って必要?

# ===== モデル学習 =====
model = fasttext.train_supervised(
    input="train.txt",
    epoch=800,      # 多すぎると過学習することも
    lr=1,         # 学習率は1.5→0.5くらいが安定
    wordNgrams=2,    # 2-gram推奨
    minn=2,           # 文字n-gram最小
    maxn=5,           # 文字n-gram最大（日本語には効果的）
    verbose=2
)

# ===== 応答テンプレート（ラベルごと） =====
# 応答テンプレは事前に出力したボイス使った方が良い？
template_responses = {
    "欠席": "欠席ですね。かしこまりました。",
    "遅刻": "遅刻ですね。気をつけてお越しください。",
}

# ===== 推論対象（ユーザー入力） =====
# 実際には認識結果が入るようにすればいいのかな？
user_input = "部活動はありますか"

# ===== 推論処理 =====
labels, scores = model.predict(user_input)
label = labels[0].replace("__label__", "")
score = scores[0]
print("score:", score)

# 上と下両方必要？

# ===== 推論（上位2件） =====
labels, scores = model.predict(user_input, k=2)  # 上位2件まで取得
label1, score1 = labels[0].replace("__label__", ""), scores[0]
label2, score2 = labels[1].replace("__label__", ""), scores[1]

# ===== 分岐処理 =====
if label1 == "その他": # label1がその他だったらlabel2を参照しないのは？
    print(f"[非定型処理] → ラベルが 'その他' のため Gemini へ (score={score1:.2f})")
    answer = gemini_answer_from_pdf(user_input)
    print("→ Gemini応答:", answer)
    # ログ用ラベルを上書き
    log_label = "その他(Gemini)"
    log_response = answer
    save_conversation_log(user_input, log_label, score1, answer)

elif score1 >= 0.7 and (score1 - score2) >= 0.2: # score1とscore2を絶対値で比較しなくても大丈夫？
    response = template_responses.get(label1, "内容を確認しました。")
    print(f"[定型処理] → ラベル: {label1} (score={score1:.2f})")
    print("→ 応答:", response)
    
    log_label = label1
    log_response = response
    
    save_conversation_log(user_input, log_label, score1, response)

else:
    print(f"[非定型処理] → 曖昧または未知 (score={score1:.2f}, 次点との差={score1 - score2:.2f})")
    answer = gemini_answer_from_pdf(user_input)
    print("→ Gemini応答:", answer)
    
    log_label = "曖昧(Gemini)"
    log_response = answer
    save_conversation_log(user_input, log_label, score1, answer)
#teams送信用
response = template_responses.get(log_label, "内容を確認しました。")
send_conversation_to_teams(user_input, log_label, score1, log_response)

