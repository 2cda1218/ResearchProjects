import fasttext
import os
import pandas as pd
from sentence_transformers import SentenceTransformer as ST
import chromadb
from google import genai as gemini
from google.genai import types
from dotenv import load_dotenv
import PyPDF2
import uuid
import logging
import time

logging.basicConfig(level=logging.DEBUG, format='[%(asctime)s] [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger(__name__)
logger.info("loggingを開始します")

logger.info("パスを初期化します")
script_dir = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(script_dir, "ft_model.bin")
data_path = os.path.join(script_dir, "train.txt")
pdf_path = os.path.join(script_dir, "school_test.pdf")

logger.info("SentenceTransformerとchromaを初期化します")
embedder = ST("all-MiniLM-L6-v2")
chroma_client = chromadb.Client()

logger.info(".envのロードを行います")
load_dotenv()
GEMINI_TOKEN = os.getenv("GEMINI_TOKEN")

logger.info("Geminiのセットアップを行います")
gemini_client = gemini.Client(api_key=GEMINI_TOKEN)
gemini_model = "gemini-2.5-flash-lite"
gemini_config = types.GenerateContentConfig(temperature=0.7, max_output_tokens=512)

logger.info("chromaの設定を行います")
try:
    chroma_client.delete_collection("schooltest.pdf")
except:
    logger.info("該当するものが見つかりませんでした")
    pass

collection = chroma_client.get_or_create_collection("school_test.pdf")

def gemini_answer(input_txt:str):
    querry_vec = embedder.encode(input_txt).tolist()
    results = collection.query(query_embeddings=[querry_vec], n_results=3)
    context = "\n".join(results["documents"][0])
    prompt = (
        "あなたは学校情報に示された学校の事務員とする．\n"
        "以下の学校情報に従って連絡セクションの内容に対して丁寧な回答をしてもらう．\n"
        "学校情報から回答に必要な情報が得られない場合は，「すみません，その質問にはお答えすることができません．」と必ず回答すること．\n"
        "答える事が可能な場合には，丁寧な2文の文章を作成して回答すること\n"
        "宛名は含めないこと"
        "【学校情報】\n"
        f"{context}\n"
        "【連絡】\n"
        f"{input_txt}"
    )

    try:
        response = gemini_client.models.generate_content(
            model = gemini_model,
            contents = prompt,
            config = gemini_config
        )
        if not (response.text or "").strip():
            return "回答を生成することができませんでした"
        return response.text.strip()
    
    except Exception as e:
        print(e)
        return f"エラーが発生しました:"

def load_pdf():
    print("pdf to chroma")
    with open(pdf_path,"rb") as f:
        reader = PyPDF2.PdfReader(f)
        texts = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                texts.append(text.strip())
    chunks = []
    for text in texts:
        while len(text) > 500:
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

def train_model():
    df = pd.read_csv(os.path.join(script_dir, "gakusyudata.csv"))

    with open(data_path,"w",encoding="utf-8") as f:
        for _, row in df.iterrows():
            label = row["label"]
            text = row["text"]
            f.write(f"__label__{label} {text}\n")

    model = fasttext.train_supervised(
        input = data_path,
        epoch = 800,
        lr = 1,
        wordNgrams = 2,
        minn = 2,
        maxn = 5,
        verbose = 2
    )
    model.save_model(model_path)

def main():
    logger.info("分類モデルを確認します")
    if not os.path.exists(model_path):
        logger.info("モデルが見つからないので作成を行います")
        start_time = time.perf_counter()
        train_model()
        end_time = time.perf_counter()
        logger.info(f"学習時間：{end_time - start_time}")
    logger.info("回答用pdfのロードを行います")
    start_time = time.perf_counter()
    load_pdf()
    end_time = time.perf_counter()
    logger.info(f"PDFロード時間：{end_time - start_time}")
    logger.info("分類モデルのロードを行います")
    start_time = time.perf_counter()
    model = fasttext.load_model(model_path)
    end_time = time.perf_counter()
    logger.info(f"モデルロード時間：{end_time - end_time}")
    user_input = "病院に行ってから登校します"
    logger.info(f"input > {user_input}")
    start_time = time.perf_counter()
    labels, scores = model.predict(user_input, k=2)
    end_time = time.perf_counter()
    label1, score1 = labels[0].replace("__label__",""), scores[0]
    label2, score2 = labels[1].replace("__label__",""), scores[1]

    logger.info(f"分類結果\nLabels: Label1 [{label1}], Label2 [{label2}]\nScores: Score1 [{score1}], Score2 [{score2}]\n分類時間: {end_time - start_time}")

    if 0.7 <= score1 and 0.2 <= abs(score1 - score2):
        pattern = "定型"
        logger.info(label1)
    else:
        pattern = "非定型"
        logger.info((gemini_answer(user_input)))


if __name__ == "__main__":
    main()