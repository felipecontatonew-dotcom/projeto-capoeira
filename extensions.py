# extensions.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

# Instancia as extensões que serão usadas no projeto.
db = SQLAlchemy()
login_manager = LoginManager()