"""
TTS endpoint: takes arbitrary text (already passed through
text_simplifier.simplify() by the caller, or raw for ad-hoc reads),
synthesizes speech via the dual TTS engine, and returns base64 audio
for the frontend audio control bar to play.
"""
from flask import Blueprint, request, jsonify

from ..tts_engine import synthesize, clamp_speed
from ..text_simplifier import simplify

tts_bp = Blueprint("tts", __name__, url_prefix="/tts")


@tts_bp.route("/speak", methods=["POST"])
def speak():
    data = request.get_json(silent=True) or {}
    text = data.get("text", "")
    should_simplify = data.get("simplify", True)
    speed = clamp_speed(data.get("speed", 1.0))

    if should_simplify:
        text = simplify(text)

    try:
        result = synthesize(text)
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 502

    response = result.to_dict()
    response["speed"] = speed  # applied client-side via audio.playbackRate
    response["simplified_text"] = text
    return jsonify(response)
