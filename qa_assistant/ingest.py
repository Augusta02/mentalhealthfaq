import os
import pandas as pd
import pickle
import minsearch
from config import DATA_PATH

# DATA_PATH = os.getenv("DATA_PATH", "../mentalhealthqa/data/Mental_Health_FAQ.csv")


def load_index(data_path=DATA_PATH):
    df = pd.read_csv(data_path)
    documents = df.to_dict(orient="records")

    index = minsearch.Index(
        text_fields=['Questions', 'Answers'],
        keyword_fields=["Question_ID"],
    )

    index.fit(documents)
    return index