"""
app.py
Application entry point for the Face Recognition Employee Attendance System.

Run with:
    pip install -r requirements.txt
    python app.py
"""

from flask import Flask

try:
    from flask_session import Session
    FLASK_SESSION_AVAILABLE = True
except Exception:
    FLASK_SESSION_AVAILABLE = False

from config import Config
from database import init_db
from routes import bp as main_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    if FLASK_SESSION_AVAILABLE:
        Session(app)
    else:
        print("[WARN] Flask-Session not installed - falling back to Flask's built-in "
              "signed-cookie sessions. Run 'pip install Flask-Session' for server-side sessions.")

    # Initialize database & seed default admin
    init_db()

    app.register_blueprint(main_bp)

    # Make 'now' available in all templates
    @app.context_processor
    def inject_now():
        from datetime import datetime
        return {"current_year": datetime.now().year}

    return app


app = create_app()


if __name__ == "__main__":
    print("=" * 70)
    print(" Face Recognition Employee Attendance System")
    print(" Running at: http://127.0.0.1:5000")
    print(" Default admin -> username: admin | password: Admin@123")
    print("=" * 70)
    app.run(host="0.0.0.0", port=5000, debug=Config.DEBUG)
