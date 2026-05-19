"""
Run once to remove duplicate DetectionHistory records from the database.
Keeps only the LATEST record per (user_id, article_snippet, prediction) group.
"""
from app import create_app
from extensions import db
from models.detection import DetectionHistory
from sqlalchemy import func

app = create_app()

with app.app_context():
    # Find the max(id) — latest — per unique group
    subq = (
        db.session.query(func.max(DetectionHistory.id).label('keep_id'))
        .group_by(
            DetectionHistory.user_id,
            DetectionHistory.article_snippet,
            DetectionHistory.prediction,
        )
        .subquery()
    )

    keep_ids = [row.keep_id for row in db.session.execute(subq)]

    deleted = (
        DetectionHistory.query
        .filter(DetectionHistory.id.notin_(keep_ids))
        .delete(synchronize_session='fetch')
    )
    db.session.commit()

    total = DetectionHistory.query.count()
    print(f"Removed {deleted} duplicate record(s). {total} record(s) remaining.")
