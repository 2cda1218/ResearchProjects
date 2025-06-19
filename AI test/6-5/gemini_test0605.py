import google.generativeai as genai
from gtts import gTTS
import os
import re

# APIキー設定（安全な管理を推奨）
genai.configure(api_key='AIzaSyDWMDthIS2VuelPtNHhlEI0kQVkT0AawUA')

# モデルを初期化
model = genai.GenerativeModel(model_name='gemini-1.5-flash')

# プロンプトを送信
prompt = "こんにちは！"
response = model.generate_content(prompt)

# 生成されたテキスト
text = response.text
print("生成されたテキスト:", text)

# Markdown記号を削除
clean_text = re.sub(r"[*_`#>\[\]()\-!]", "", response.text)

# gTTSで音声合成
tts = gTTS(text=text, lang='ja')
tts.save("output.mp3")

# 音声を再生
os.system("start output.mp3")  



