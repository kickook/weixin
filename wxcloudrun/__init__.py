from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import pymysql

import config

pymysql.install_as_MySQLdb()

app = Flask(__name__, instance_relative_config=True, template_folder="templates")
app.config.from_object('config')

app.config.setdefault('JSON_SORT_KEYS', False)

# Initialize database
app.config['SQLALCHEMY_DATABASE_URI'] = config.SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = config.SQLALCHEMY_TRACK_MODIFICATIONS

db = SQLAlchemy(app)

# Import views and models after db initialization to avoid circular imports
from wxcloudrun import views  # noqa: E402,F401

with app.app_context():
    from wxcloudrun import model  # noqa: F401
    db.create_all()
    if hasattr(model, 'ensure_default_admin'):
        model.ensure_default_admin()
