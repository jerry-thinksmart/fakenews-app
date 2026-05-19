"""
clean_errors.py — Removes Error and Invalid records from detection_history.
All other records (Fake, Real, Uncertain) are kept intact.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from extensions import db
from models.detection import DetectionHistory

app = create_app()

with app.app_context():
    removed = (
        db.session.query(DetectionHistory)
        .filter(DetectionHistory.prediction.in_(['Error', 'Invalid']))
        .delete(synchronize_session=False)
    )
    db.session.commit()
    print(f"Removed {removed} Error/Invalid record(s).")
    remaining = db.session.query(DetectionHistory).count()
    print(f"{remaining} record(s) remaining.")
