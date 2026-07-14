import os
from dotenv import load_dotenv

load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Default: SQLite DB in project root
    SQLITE_PATH = os.environ.get('SQLITE_PATH', os.path.join(basedir, 'health.db'))
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', f"sqlite:///{SQLITE_PATH}")

    # Example MySQL URI (if you prefer MySQL, set DATABASE_URL in .env)
    # DATABASE_URL=mysql+pymysql://username:password@host:port/database_name
