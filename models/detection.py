from datetime import datetime
from extensions import db


class DetectionHistory(db.Model):
    __tablename__ = 'detection_history'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    article_snippet = db.Column(db.Text, nullable=True)
    full_article = db.Column(db.Text, nullable=True)
    prediction = db.Column(db.String(20), nullable=False)  # Fake / Real / Uncertain / Invalid
    confidence = db.Column(db.Float, nullable=True)
    message = db.Column(db.String(300), nullable=True)
    detected_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f'<DetectionHistory id={self.id} prediction={self.prediction}>'
