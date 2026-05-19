import os
from flask import Flask
from config import Config
from extensions import db, login_manager, csrf, mail


def _migrate_db(database):
    """Add any columns that were introduced after the initial DB creation."""
    engine = database.engine
    with engine.connect() as conn:
        # detection_history: message + full_article added after first release
        existing = {row[1] for row in conn.execute(
            database.text('PRAGMA table_info(detection_history)')
        )}
        if 'message' not in existing:
            conn.execute(database.text(
                'ALTER TABLE detection_history ADD COLUMN message VARCHAR(300)'
            ))
        if 'full_article' not in existing:
            conn.execute(database.text(
                'ALTER TABLE detection_history ADD COLUMN full_article TEXT'
            ))
        # users: profile_photo added after initial release
        user_cols = {row[1] for row in conn.execute(
            database.text('PRAGMA table_info(users)')
        )}
        if 'profile_photo' not in user_cols:
            conn.execute(database.text(
                'ALTER TABLE users ADD COLUMN profile_photo VARCHAR(256)'
            ))
        if 'reset_token' not in user_cols:
            conn.execute(database.text(
                'ALTER TABLE users ADD COLUMN reset_token VARCHAR(100)'
            ))
        if 'reset_token_expiry' not in user_cols:
            conn.execute(database.text(
                'ALTER TABLE users ADD COLUMN reset_token_expiry DATETIME'
            ))
        # subscribers: phone added after initial release
        sub_cols = {row[1] for row in conn.execute(
            database.text('PRAGMA table_info(subscribers)')
        )}
        if 'phone' not in sub_cols:
            conn.execute(database.text(
                'ALTER TABLE subscribers ADD COLUMN phone VARCHAR(20)'
            ))
        conn.commit()


@login_manager.user_loader
def load_user(user_id):
    from models.user import User
    return db.session.get(User, int(user_id))


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure database directory exists before SQLAlchemy tries to create the file
    os.makedirs(os.path.join(app.root_path, 'database'), exist_ok=True)

    # Initialise extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)

    # Flask-Login settings
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'warning'

    # Register blueprints (imported lazily to avoid circular imports)
    from routes.public import public_bp
    from routes.auth import auth_bp
    from routes.dashboard import dashboard_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')

    # Create all database tables
    with app.app_context():
        from models import user, detection, article, log, subscriber  # noqa: F401 – ensures models are registered
        db.create_all()

        # Auto-migrate: add any columns that were added after the DB was first created
        _migrate_db(db)

    # Security headers on every response
    @app.after_request
    def add_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        return response

    return app


if __name__ == '__main__':
    application = create_app()
    application.run(debug=True)
