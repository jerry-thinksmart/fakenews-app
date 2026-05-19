"""
clear_db.py — Clears detection_history, news_records, and system_logs.
User accounts are NOT touched.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from extensions import db
from models.detection import DetectionHistory
from models.article import NewsRecord
from models.log import SystemLog

app = create_app()

with app.app_context():
    d = db.session.query(DetectionHistory).delete()
    r = db.session.query(NewsRecord).delete()
    l = db.session.query(SystemLog).delete()
    db.session.commit()
    print(f"Cleared {d} detection history record(s).")
    print(f"Cleared {r} news record(s).")
    print(f"Cleared {l} system log(s).")
    print("User accounts untouched.")
