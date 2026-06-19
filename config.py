"""
config.py
Central configuration for the Face Recognition Attendance System.
"""

import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    # Flask
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-this-super-secret-key-in-production")
    SESSION_TYPE = "filesystem"
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 8  # 8 hours

    # Database
    DATABASE_PATH = os.path.join(BASE_DIR, "instance", "attendance.db")

    # Uploads / face data
    KNOWN_FACES_DIR = os.path.join(BASE_DIR, "known_faces")
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}

    # Face recognition
    FACE_MATCH_TOLERANCE = 0.5   # lower = stricter
    FACE_DETECTION_MODEL = "hog"  # 'hog' (CPU) or 'cnn' (GPU)

    # Attendance rules
    MIN_MINUTES_BETWEEN_CHECKIN_CHECKOUT = 1  # avoid double scan in same minute

    # Admin bootstrap credentials (used only if no admin exists yet)
    DEFAULT_ADMIN_USERNAME = "admin"
    DEFAULT_ADMIN_PASSWORD = "Admin@123"
    DEFAULT_ADMIN_EMAIL = "admin@company.com"

    DEBUG = True
