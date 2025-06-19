import os
import chromadb
from sentence_transformers import SentenceTransformer
import google.generativeai as genai
from gtts import gTTS
import PyPDF2


# === 1. PDF読み込み関数 ===
file_path = r"C:\Users\naoma\Downloads\senior_thesis\AI_test\gemini_test0619\school_test.pdf"
def load_pdf_text(file_path):
    text = ""
    with open(file_path, 'rb') as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            text += page.extract_text() + "\n"
    return text

# === 2. テキストをチャンク（分割） ===
def split_text(text, chunk_size=300, overlap=50):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk.strip())
        start += chunk_size - overlap
    return chunks

# === 3. Chroma ベクトルDB 初期化 ===
client = chromadb.Client()
collection = client.get_or_create_collection("school_pdf_docs")  # ← これがコレクション名（DB名）

# === 4. 埋め込みモデル準備 ===
embedder = SentenceTransformer("all-MiniLM-L6-v2")

# === 5. 登録するPDFファイル名 ===
pdf_path = file_path  # ← あなたのPDFファイル名に変更

# === 6. 読み込み・分割・登録 ===
raw_text = load_pdf_text(pdf_path)
chunks = split_text(raw_text)

print(f"読み込んだチャンク数: {len(chunks)}")

for i, chunk in enumerate(chunks):
    vector = embedder.encode(chunk).tolist()
    collection.add(
        documents=[chunk],
        embeddings=[vector],
        ids=[f"doc_{i}"]
    )

print("PDFからベクトルDBへの登録が完了しました。")

# ===== 初期設定 =====
genai.configure(api_key="AIzaSyDWMDthIS2VuelPtNHhlEI0kQVkT0AawUA")
model = genai.GenerativeModel(model_name='gemini-1.5-flash')
embedder = SentenceTransformer("all-MiniLM-L6-v2")
client = chromadb.Client()
collection = client.get_or_create_collection("school_pdf_docs")  # 登録済のベクトルDB名

# ===== 質問入力 =====
question = input("質問を入力してください: ")

# ===== [Step 1] ベクトル検索 =====
query_vec = embedder.encode(question).tolist()
results = collection.query(query_embeddings=[query_vec], n_results=3)
context = "\n".join(results['documents'][0])

#テスト用(確認)
#print("==== 検索された文書 ====")
#for i, doc in enumerate(results["documents"][0]):
#    print(f"{i+1}: {doc}")

# ===== [Step 2] Geminiで回答生成 =====
prompt = f"""
あなたは「東海大学」の教師です。
以下の学校情報に基づいて、ユーザーの質問に丁寧に答えてください。
情報がない場合は「分かりません」と返してください。

【学校情報】
{context}

【質問】
{question}
"""

response = model.generate_content(prompt)
answer = response.text.strip()
print("Geminiの回答:", answer)

# ===== [Step 3] 音声出力（gTTS）=====
tts = gTTS(text=answer, lang='ja')
tts.save("answer.mp3")
os.system("start answer.mp3")  # Windowsの場合。他OSなら変更要
