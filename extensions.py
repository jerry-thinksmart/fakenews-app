"""
extensions.py – Flask extension instances.
Defined here (not in app.py) to prevent circular imports when models/routes
do `from extensions import db`.
"""
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_mail import Mail

db            = SQLAlchemy()
login_manager = LoginManager()
csrf          = CSRFProtect()
mail          = Mail()
