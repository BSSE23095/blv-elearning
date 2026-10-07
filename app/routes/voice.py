"""
Voice command navigation endpoint. Receives a recorded audio blob from
the browser MediaRecorder API, transcribes it via Google Speech
Recognition, and returns the matched intent for the frontend JS to act on.
"""
from flask import Blueprint, request, jsonify

from ..voice_nav import process_voice_command, transcript_to_intent, INTENTS

voice_bp = Blueprint("voice", __name__, url_prefix="/voice")


@voice_bp.route("/command", methods=["POST"])
def voice_command():
    if "audio" not in request.files:
        return jsonify({"error": "No audio uploaded."}), 400

    try:
        result = process_voice_command(request.files["audio"])
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 502

    return jsonify(result)


@voice_bp.route("/command-text", methods=["POST"])
def voice_command_text():
    """
    Typed command fallback for when the microphone is unavailable or
    permission is denied (Section 3.2: "a typed command fallback is
    provided in case the microphone fails"). Runs the exact same
    transcript-to-intent matching — including the Levenshtein
    fallback — as the audio path, just skipping speech recognition.
    """
    data = request.get_json(silent=True) or {}
    text = data.get("text", "")

    intent, matched_phrase, distance = transcript_to_intent(text)
    return jsonify({
        "transcript": text,
        "intent": intent,
        "matched_phrase": matched_phrase,
        "edit_distance": distance,
        "recognized": intent is not None,
    })


@voice_bp.route("/intents", methods=["GET"])
def list_intents():
    """Used by the 'Hear Commands' / help feature."""
    return jsonify(INTENTS)
