import fasttext
import pandas as pd
import logging
import os

logger = logging.getLogger(__name__)
script_dir = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(script_dir, "ft_model.bin")

def train_model():
    df = pd.read_csv(f"{script_dir}/gakusyudata.csv")

    with open("train.txt","w",encoding="utf-8") as f:
        for _, row in df.iterrows():
            label = row["label"]
            text = row["text"]
            f.write(f"__label__{label} {text}\n")
    
    model = fasttext.train_supervised(
        input = "train.txt",
        epoch = 800,
        lr = 1,
        wordNgrams = 2,
        minn = 2,
        maxn = 5,
        verbose = 2
    )
    model.save_model(model_path)

train_model()