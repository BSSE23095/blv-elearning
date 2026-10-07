"""
tts_engine.py

Dual TTS engine as described in Section 3.2 ("Neural TTS") of the paper:
  - Primary: gTTS (Google neural TTS). Audio is synthesized, returned as
    base64-encoded MP3, and streamed directly to the browser — nothing is
    written to disk on the server.
  - Fallback: pyttsx3 (offline, concatenative synthesis) used automatically
    when gTTS raises a connection error (e.g. no internet — the paper
    specifically calls out offline environments such as Pakistani schools).

Playback speed (0.5x-2.0x) is applied client-side via the HTML5 <audio>
element's playbackRate, matching the paper's "students choose their
preferred speed" behaviour — gTTS/pyttsx3 don't need to bake speed into
the audio file itself.
"""
import base64
import io
import logging

from gtts import gTTS
from gtts.tts import gTTSError

logger = logging.getLogger(__name__)

MIN_SPEED = 0.5
MAX_SPEED = 2.0


class TTSResult:
    def __init__(self, audio_base64: str, engine_used: str, mime_type: str):
        self.audio_base64 = audio_base64
        self.engine_used = engine_used
        self.mime_type = mime_type

    def to_dict(self):
        return {
            "audio_base64": self.audio_base64,
            "engine_used": self.engine_used,
            "mime_type": self.mime_type,
        }


def _synthesize_gtts(text: str, lang: str = "en") -> bytes:
    buf = io.BytesIO()
    tts = gTTS(text=text, lang=lang)
    tts.write_to_fp(buf)
    buf.seek(0)
    return buf.read()


def _synthesize_pyttsx3(text: str) -> bytes:
    import pyttsx3
    import tempfile
    import os as _os

    engine = pyttsx3.init()
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        engine.save_to_file(text, tmp_path)
        engine.runAndWait()
        with open(tmp_path, "rb") as f:
            data = f.read()
    finally:
        if _os.path.exists(tmp_path):
            _os.remove(tmp_path)
    return data


def synthesize(text: str, lang: str = "en") -> TTSResult:
    """
    Try neural TTS (gTTS) first; fall back to offline pyttsx3 on any
    network-related failure. Returns base64 audio ready to hand straight
    to an <audio src="data:...;base64,..."> tag.
    """
    if not text or not text.strip():
        text = "There is no content to read for this section."

    try:
        audio_bytes = _synthesize_gtts(text, lang=lang)
        return TTSResult(
            audio_base64=base64.b64encode(audio_bytes).decode("utf-8"),
            engine_used="gtts",
            mime_type="audio/mpeg",
        )
    except (gTTSError, ConnectionError, OSError) as e:
        logger.warning("gTTS failed (%s); falling back to pyttsx3 offline engine.", e)
        try:
            audio_bytes = _synthesize_pyttsx3(text)
            return TTSResult(
                audio_base64=base64.b64encode(audio_bytes).decode("utf-8"),
                engine_used="pyttsx3",
                mime_type="audio/wav",
            )
        except Exception as fallback_error:
            logger.error("pyttsx3 fallback also failed: %s", fallback_error)
            raise RuntimeError(
                "Both gTTS and the offline pyttsx3 fallback failed to synthesize audio."
            ) from fallback_error


def clamp_speed(speed: float) -> float:
    """Clamp a requested playback speed to the paper's 0.5x-2.0x range."""
    try:
        speed = float(speed)
    except (TypeError, ValueError):
        return 1.0
    return max(MIN_SPEED, min(MAX_SPEED, speed))
