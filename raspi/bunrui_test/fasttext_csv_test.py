import fasttext
import pandas as pd
import os
import chromadb
from sentence_transformers import SentenceTransformer as ST
from dotenv import load_dotenv
from gtts import gTTS
import PyPDF2
import uuid
from google import genai as gemini
from google.genai import types
import requests

# Teams Webhook URL 動いているみたいだから.envからウェブフックURLを取得できるようにして実装するのはあり
#TEAMS_WEBHOOK_URL = "https://utokai.webhook.office.com/webhookb2/442834dd-3d07-4e81-8059-b4352e75bd0c@8283096f-bcce-44d0-8f54-e57aa84d1a22/IncomingWebhook/03c1777ddb7542ccb1161190bfc1581a/aad18c1b-d1c6-46b2-adcc-3c163218c4d5/V2EqcJ0hRlkvsr1ECTerA_IHrpZ5crAXa1CVZGeJ7RKto1"

#def send_conversation_to_teams(user_input, log_label, score, log_response):
#    log_text = (
#        f"**ユーザー入力:** {user_input}\n"
#        f"**判定ラベル:** {log_label} (score={score:.2f})\n"
#        f"**AI応答:** {log_response}"
#    )

#    payload = {
#        "text": log_text  # Teamsは"text"キーで送る
#    }

#    requests.post(TEAMS_WEBHOOK_URL, json=payload)

# ====== Gemini 設定 ======
load_dotenv()
GEMINI_TOKEN = os.getenv("GEMINI_TOKEN")

gemini_client = gemini.Client(api_key=GEMINI_TOKEN)
gemini_model = "gemini-2.5-flash-lite"
gemini_config = types.GenerateContentConfig(temperature=0.7,max_output_tokens=512)

# ====== SentenceTransformer & Chroma 設定 ======
embedder = ST("all-MiniLM-L6-v2")

chroma_client = chromadb.Client()

# ====== 既存コレクションがあれば削除（重複登録防止） ======
try:
    chroma_client.delete_collection("school_test.pdf")
except:
    pass

# ====== 新規コレクション作成 ======
collection = chroma_client.get_or_create_collection("school_test.pdf")

# ====== PDF を Chroma に登録 ======

def load_pdf_into_chroma(pdf_path):
    print("📘 PDF から Chroma へデータ登録中...")

    # PDF 読み込み
    with open(pdf_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        texts = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                texts.append(text.strip())

    # チャンク分割（500文字ごと）
    chunks = []
    for text in texts:
        while len(text) > 500:
            chunks.append(text[:500])
            text = text[500:]
        if text:
            chunks.append(text)

    # Chroma に追加
    for chunk in chunks:
        emb = embedder.encode(chunk).tolist()
        collection.add(
            ids=[str(uuid.uuid4())],
            documents=[chunk],
            embeddings=[emb]
        )

    print(f"📚 登録完了！ {len(chunks)} チャンク追加しました")

# ====== PDF 読み込み実行 ======
load_pdf_into_chroma("school_test.pdf")

print("📦 Chroma コレクション文書数：", collection.count())
print("✅ Gemini API と Chroma 初期化完了")


def gemini_answer_from_pdf(question):
    query_vec = embedder.encode(question).tolist()
    results = collection.query(query_embeddings=[query_vec], n_results=3)
    context = "\n".join(results["documents"][0])
    print(context)

    prompt = f"""
あなたは「東海大学」の教師です。
以下の学校情報に基づいて、先ほど読み込んだPDFからユーザーの質問に丁寧に答えてください。
情報がない場合は「すいません、その質問にはお答えできません。」とだけ返してください。アドバイスなどはしなくていいですし、前置きもいりません。
もし、答えれる内容がある場合、単語で答えず主語と述語はいれて答えてください。

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
        f.write(f"__label__{label} {text}\n")

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
template_responses = {
    "欠席": "欠席ですね。かしこまりました。",
    "遅刻": "遅刻ですね。気をつけてお越しください。",
}

# ===== 推論対象（ユーザー入力） =====
user_input = "病院から登校します"

# ===== 推論処理 =====
labels, scores = model.predict(user_input)
label = labels[0].replace("__label__", "")
score = scores[0]
print("score:", score)

# ===== 推論（上位2件） =====
labels, scores = model.predict(user_input, k=2)  # 上位2件まで取得
label1, score1 = labels[0].replace("__label__", ""), scores[0]
label2, score2 = labels[1].replace("__label__", ""), scores[1] # よく見たらlabel2ってどこも参照してなくない？

# ===== 分岐処理 =====
if label1 == "その他":
    print(f"[非定型処理] → ラベルが 'その他' のため Gemini へ (score={score1:.2f})")
    answer = gemini_answer_from_pdf(user_input)
    print("→ Gemini応答:", answer)
    # ログ用ラベルを上書き
    log_label = "その他(Gemini)"
    log_response = answer
    save_conversation_log(user_input, log_label, score1, answer)

elif score1 >= 0.7 and (score1 - score2) >= 0.2:
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
    
    # ===== 最終確認（"その他" の場合は行わない） =====
if log_label not in ["その他(Gemini)", "曖昧(Gemini)"]:
    confirm = input(f"\n最終確認です。\n\nあなたの申告は「{log_label}」で間違いありませんか？\n「はい」または「いいえ」でお答えください: ")

    if confirm.lower() == "はい":
        print("了解しました。記録しておきます。")
    else:
        print("\n失礼しました。では改めて教えてください。")
        
        # 欠席 or 遅刻 のどちらかを直接入力
        while True:
            fixed = input("「欠席」か「遅刻」で入力してください: ").strip()

            if fixed in ["欠席", "遅刻"]:
                print(f"\nありがとうございます。「{fixed}」として記録します。")
                log_label = fixed               # ← 正しいラベルに上書き
                log_response = template_responses.get(fixed, "内容を確認しました。")
                break
            else:
                print("入力が正しくありません。'欠席' または '遅刻' を入力してください。")

#teams送信用
response = template_responses.get(log_label, "内容を確認しました。")
#send_conversation_to_teams(user_input, log_label, score1, log_response)

