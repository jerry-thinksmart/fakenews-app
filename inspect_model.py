"""
Run this to inspect exactly what the model's classes are and how it predicts.
This tells us the correct label-to-index mapping.
"""
import joblib
import numpy as np
from config import Config

model = joblib.load(Config.MODEL_PATH)
vectorizer = joblib.load(Config.VECTORIZER_PATH)

print("=== MODEL INFO ===")
print(f"Model type: {type(model).__name__}")
print(f"Classes:    {model.classes_}")
print(f"Classes dtype: {model.classes_.dtype}")

# Test with obvious fake news sample
test_texts = [
    ("FAKE SAMPLE", "Scientists discover that drinking bleach cures cancer. Global conspiracy by doctors to hide this cure. Share before deleted!"),
    ("REAL SAMPLE", "The Federal Reserve raised interest rates by 25 basis points on Wednesday, citing persistent inflation concerns. Chairman Jerome Powell stated the committee remains committed to bringing inflation back to the 2 percent target."),
]

import re
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer

nltk.download('stopwords', quiet=True)
nltk.download('wordnet', quiet=True)
_lemmatizer = WordNetLemmatizer()
_stop_words = set(stopwords.words('english'))

def preprocess(text):
    text = text.lower()
    text = re.sub(r'https?://\S+|www\.\S+', '', text)
    text = re.sub(r'[^a-z\s]', '', text)
    tokens = text.split()
    tokens = [_lemmatizer.lemmatize(t) for t in tokens if t not in _stop_words and len(t) > 1]
    return ' '.join(tokens)

print("\n=== PREDICTIONS ===")
for label, text in test_texts:
    processed = preprocess(text)
    vec = vectorizer.transform([processed])
    pred = model.predict(vec)[0]
    proba = model.predict_proba(vec)[0]
    print(f"\n[{label}]")
    print(f"  raw pred:    {pred!r}  (type: {type(pred).__name__})")
    print(f"  probabilities: {dict(zip(model.classes_, proba))}")
    print(f"  class[0]={model.classes_[0]} prob={proba[0]:.4f}")
    print(f"  class[1]={model.classes_[1]} prob={proba[1]:.4f}")
