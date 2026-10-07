"""
Diagram accessibility tool (Section 3.2).

User uploads an image; the backend classifies it into one of seven
categories using the trained MobileNetV2 model and returns a structured
natural language description, which the frontend sends to /tts/speak to
read aloud.
"""
import os
import uuid
from flask import Blueprint, render_template, request, jsonify, current_app, session

from ..diagram_classifier import classify_image, is_using_trained_weights
from ..db import get_db

diagram_bp = Blueprint("diagram", __name__, url_prefix="/diagram")

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp"}


@diagram_bp.route("/", methods=["GET"])
def diagram_upload_page():
    return render_template("diagram.html", using_trained_weights=is_using_trained_weights())


@diagram_bp.route("/classify", methods=["POST"])
def classify():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in."}), 401

    if "image" not in request.files:
        return jsonify({"error": "No image uploaded."}), 400

    file = request.files["image"]
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({"error": f"Unsupported file type: {ext}"}), 400

    filename = f"{uuid.uuid4().hex}{ext}"
    save_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
    file.save(save_path)

    try:
        predicted_class, confidence, description = classify_image(save_path)
    except Exception as e:
        return jsonify({"error": f"Classification failed: {e}"}), 500

    db = get_db()
    db.execute(
        """INSERT INTO diagram_uploads (filename, predicted_class, confidence, description)
           VALUES (?, ?, ?, ?)""",
        (filename, predicted_class, confidence, description),
    )
    db.commit()

    return jsonify({
        "predicted_class": predicted_class,
        "confidence": round(confidence, 4),
        "description": description,
        "using_trained_weights": is_using_trained_weights(),
    })
