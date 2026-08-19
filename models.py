# models.py
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Asset(db.Model):
    __tablename__ = 'assets'
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(300), nullable=False)  # stored path relative to uploads/assets/
    asset_type = db.Column(db.String(32), nullable=False)  # 'music' or 'bg_video'
    original_name = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Setting(db.Model):
    """
    Key/value for counters like 'music_counter' and 'bg_video_counter'.
    """
    __tablename__ = 'settings'
    key = db.Column(db.String(100), primary_key=True)
    value = db.Column(db.String(300), nullable=False)
