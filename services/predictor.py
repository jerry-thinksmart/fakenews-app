import os
import re
import numpy as np
import joblib
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from config import Config

# ---------------------------------------------------------------------------
# Load model and vectorizer ONCE at module level
# ---------------------------------------------------------------------------
_model = None
_vectorizer = None
_load_error = None

try:
    _model = joblib.load(Config.MODEL_PATH)
    _vectorizer = joblib.load(Config.VECTORIZER_PATH)
except Exception as e:
    _load_error = str(e)

# ---------------------------------------------------------------------------
# NLP helpers
# ---------------------------------------------------------------------------
_lemmatizer = WordNetLemmatizer()
try:
    _stop_words = set(stopwords.words('english'))
except LookupError:
    nltk.download('stopwords', quiet=True)
    _stop_words = set(stopwords.words('english'))


def preprocess_text(text: str) -> str:
    """Lowercase, strip URLs, remove non-alpha chars, remove stopwords, lemmatize."""
    text = text.lower()
    text = re.sub(r'https?://\S+|www\.\S+', '', text)
    text = re.sub(r'[^a-z\s]', '', text)
    tokens = text.split()
    tokens = [
        _lemmatizer.lemmatize(token)
        for token in tokens
        if token not in _stop_words and len(token) > 1
    ]
    return ' '.join(tokens)


# ---------------------------------------------------------------------------
# Public prediction function
# ---------------------------------------------------------------------------
def predict_news(article_text: str) -> dict:
    """
    Analyse the supplied article text and return a dict with keys:
        prediction  (str)  : 'Fake' | 'Real' | 'Uncertain' | 'Invalid' | 'Error'
        message     (str)  : human-readable explanation
        confidence  (float): probability of the predicted class (0.0 – 1.0)
    """
    # Model failed to load
    if _load_error:
        return {
            'prediction': 'Error',
            'message': f'Model failed to load: {_load_error}',
            'confidence': 0.0,
        }

    # Empty input
    if not article_text or not article_text.strip():
        return {
            'prediction': 'Invalid',
            'message': 'Please enter some text to analyse.',
            'confidence': 0.0,
        }

    # Too short
    stripped = article_text.strip()
    word_count = len(stripped.split())
    if word_count < 20 or len(stripped) < 80:
        return {
            'prediction': 'Invalid',
            'message': (
                'Article is too short. Please provide at least 20 words '
                'and 80 characters for an accurate result.'
            ),
            'confidence': 0.0,
        }

    try:
        processed = preprocess_text(stripped)

        # Reject if preprocessing strips everything
        if not processed.strip():
            return {
                'prediction': 'Invalid',
                'message': 'Please paste a news article or headline.',
                'confidence': 0.0,
            }

        vectorized = _vectorizer.transform([processed])
        pred = _model.predict(vectorized)[0]

        # Get fake probability — class index 1 = Fake
        if hasattr(_model, 'predict_proba'):
            fake_prob = float(_model.predict_proba(vectorized)[0][1])
        elif hasattr(_model, 'decision_function'):
            score = float(_model.decision_function(vectorized)[0])
            fake_prob = float(1 / (1 + np.exp(-score)))
        else:
            fake_prob = float(pred)

        real_prob = 1.0 - fake_prob
        confidence = max(fake_prob, real_prob)

        # Only flag truly ambiguous predictions (nearly 50/50)
        if confidence < 0.52:
            return {
                'prediction': 'Uncertain',
                'message': (
                    'The model is not confident enough to classify this text. '
                    'Please paste a clearer and more complete news article.'
                ),
                'confidence': round(confidence, 4),
            }

        # pred=1 → Fake, pred=0 → Real
        if int(pred) == 1:
            return {
                'prediction': 'Fake',
                'message': 'The news is Fake.',
                'confidence': round(fake_prob, 4),
            }
        else:
            return {
                'prediction': 'Real',
                'message': 'The news is Real.',
                'confidence': round(real_prob, 4),
            }

    except Exception as e:
        return {
            'prediction': 'Error',
            'message': f'Prediction failed: {str(e)}',
            'confidence': 0.0,
        }
