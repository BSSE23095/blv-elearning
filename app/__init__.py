"""
Audio-First E-Learning Interface for Blind and Low-Vision Students
Flask application factory.

Matches the architecture described in the paper:
"Audio-First E-Learning Interface for Blind and Low-Vision Students"
(Khan, Bilal, Asif)
"""
import os
from flask import Flask
from .db import init_db


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-secret-change-me"),
        DATABASE=os.path.join(app.instance_path, "system_storage.sqlite"),
        UPLOAD_FOLDER=os.path.join(app.root_path, "uploads"),
        MAX_CONTENT_LENGTH=25 * 1024 * 1024,  # 25 MB upload cap
    )

    if test_config:
        app.config.update(test_config)

    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    init_db(app)

    # Blueprints — one per pipeline described in Section 3 of the paper
    from .routes import auth_bp, course_bp, diagram_bp, voice_bp, tts_bp, teacher_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(course_bp)
    app.register_blueprint(diagram_bp)
    app.register_blueprint(voice_bp)
    app.register_blueprint(tts_bp)
    app.register_blueprint(teacher_bp)

    return app
