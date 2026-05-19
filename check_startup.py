"""Quick startup check — run with: python check_startup.py"""
import sys
import traceback

print(f"Python: {sys.executable}")
print("--- Testing imports ---")

try:
    from extensions import db, login_manager, csrf
    print("OK: extensions")
except Exception as e:
    print(f"FAIL extensions: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    from config import Config
    print("OK: config")
    print(f"   MODEL_PATH exists: ", end="")
    import os
    print(os.path.exists(Config.MODEL_PATH))
    print(f"   VECTORIZER_PATH exists: ", end="")
    print(os.path.exists(Config.VECTORIZER_PATH))
except Exception as e:
    print(f"FAIL config: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    from models.user import User
    from models.detection import DetectionHistory
    from models.article import NewsRecord
    from models.log import SystemLog
    print("OK: models")
except Exception as e:
    print(f"FAIL models: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    from services.predictor import predict_news, _load_error
    if _load_error:
        print(f"WARN predictor: model load error (non-fatal): {_load_error}")
    else:
        print("OK: predictor (model loaded)")
except Exception as e:
    print(f"FAIL predictor: {e}")
    traceback.print_exc()

try:
    from routes.public import public_bp
    from routes.auth import auth_bp
    from routes.dashboard import dashboard_bp
    print("OK: routes/blueprints")
except Exception as e:
    print(f"FAIL routes: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    from app import create_app
    app = create_app()
    print("OK: create_app()")
    print(f"\nAll good! Run:  python app.py")
    print(f"Then open:     http://127.0.0.1:5000")
except Exception as e:
    print(f"FAIL create_app: {e}")
    traceback.print_exc()
