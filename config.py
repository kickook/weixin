import os
from pathlib import Path

# Whether to run Flask in debug mode
DEBUG = os.environ.get("FLASK_DEBUG", "true").lower() == "true"

BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / "instance"
INSTANCE_DIR.mkdir(exist_ok=True)

# Database configuration
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    mysql_user = os.environ.get("MYSQL_USERNAME")
    mysql_password = os.environ.get("MYSQL_PASSWORD")
    mysql_address = os.environ.get("MYSQL_ADDRESS")
    if mysql_user and mysql_password and mysql_address:
        DATABASE_URL = f"mysql://{mysql_user}:{mysql_password}@{mysql_address}/flask_demo"
    else:
        DATABASE_URL = f"sqlite:///{INSTANCE_DIR / 'app.db'}"

SQLALCHEMY_DATABASE_URI = DATABASE_URL
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Dify integration
DIFY_API_URL = os.environ.get("DIFY_API_URL", "")
DIFY_API_KEY = os.environ.get("DIFY_API_KEY", "")
DIFY_TIMEOUT = float(os.environ.get("DIFY_TIMEOUT", 15))

# Basic security defaults
DEFAULT_ADMIN_USERNAME = os.environ.get("DEFAULT_ADMIN_USERNAME", "admin")
DEFAULT_ADMIN_PASSWORD = os.environ.get("DEFAULT_ADMIN_PASSWORD", "admin123")
DEFAULT_ADMIN_ROLE = os.environ.get("DEFAULT_ADMIN_ROLE", "administrator")
