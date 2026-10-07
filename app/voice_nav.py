"""
voice_nav.py

Voice command navigation, as described in Section 3.2 ("Voice command
navigation") and the discussion in Section 4.7.

Pipeline:
  1. Audio captured client-side via the browser MediaRecorder API is
     POSTed to /voice/command.
  2. Sent to Google Speech Recognition (via the `SpeechRecognition`
     package) to get a transcript.
  3. Transcript mapped to one of 14 intents (Table II in the paper).
  4. If the transcript doesn't exactly match a registered trigger phrase,
     an offline Levenshtein-distance check finds the closest registered
     phrase (Section 4.7 / 6: this is the fix that improved voice command
     responsiveness to 4.5/5 in the usability study).

No internet-dependent NLU service is used for the fallback — just string
matching, exactly as described in the paper.
"""
import io
import speech_recognition as sr

# Table II: Voice Command Intent Vocabulary (14 intents)
INTENTS = {
    "go_home": ["home", "go home"],
    "list_courses": ["courses", "show courses"],
    "open_course": ["open course", "start course"],
    "next_module": ["next", "continue"],
    "previous_module": ["back", "previous module"],
    "read_content": ["read", "play content"],
    "stop_audio": ["stop", "pause"],
    "start_quiz": ["quiz", "test me"],
    "repeat": ["repeat", "say again"],
    "describe_diagram": ["describe", "what is this"],
    "help": ["help", "commands"],
    "increase_speed": ["faster", "speed up"],
    "decrease_speed": ["slower", "slow down"],
    "read_info": ["read info", "course info"],
}

# Flat list of (phrase, intent) pairs for Levenshtein matching
_ALL_PHRASES = [
    (phrase, intent) for intent, phrases in INTENTS.items() for phrase in phrases
]

LEVENSHTEIN_MAX_DISTANCE = 4  # tolerate small mispronunciations/typos
# (distance 3 rejected the paper's own worked example, "prev module" ->
# "previous module", which sits at distance 4 with a 3-point margin to the
# next-closest phrase, "open course" at distance 7 — safe to allow.)


def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if len(a) == 0:
        return len(b)
    if len(b) == 0:
        return len(a)

    prev_row = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        curr_row = [i]
        for j, cb in enumerate(b, start=1):
            cost = 0 if ca == cb else 1
            curr_row.append(
                min(
                    prev_row[j] + 1,       # deletion
                    curr_row[j - 1] + 1,   # insertion
                    prev_row[j - 1] + cost,  # substitution
                )
            )
        prev_row = curr_row
    return prev_row[-1]


def transcript_to_intent(transcript: str):
    """
    Returns (intent_name, matched_phrase, distance) or (None, None, None)
    if nothing is close enough.
    """
    transcript = transcript.strip().lower()
    if not transcript:
        return None, None, None

    # 1. Exact match first
    for phrase, intent in _ALL_PHRASES:
        if transcript == phrase:
            return intent, phrase, 0

    # 2. Substring match (handles "please go home now" etc.)
    for phrase, intent in _ALL_PHRASES:
        if phrase in transcript:
            return intent, phrase, 0

    # 3. Levenshtein fallback — closest registered phrase within tolerance
    best_phrase, best_intent, best_distance = None, None, float("inf")
    for phrase, intent in _ALL_PHRASES:
        d = _levenshtein(transcript, phrase)
        if d < best_distance:
            best_phrase, best_intent, best_distance = phrase, intent, d

    if best_distance <= LEVENSHTEIN_MAX_DISTANCE:
        return best_intent, best_phrase, best_distance

    return None, None, None


def recognize_from_audio(audio_file_storage) -> str:
    """
    Takes a Flask FileStorage (uploaded audio blob) and returns the
    transcript from Google Speech Recognition.
    """
    recognizer = sr.Recognizer()
    audio_bytes = audio_file_storage.read()

    with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
        audio_data = recognizer.record(source)

    try:
        return recognizer.recognize_google(audio_data)
    except sr.UnknownValueError:
        return ""
    except sr.RequestError as e:
        raise RuntimeError(f"Google Speech Recognition request failed: {e}")


def process_voice_command(audio_file_storage):
    """
    Full pipeline: audio -> transcript -> intent (with Levenshtein
    fallback). Returns a dict ready for a JSON API response.
    """
    transcript = recognize_from_audio(audio_file_storage)
    intent, matched_phrase, distance = transcript_to_intent(transcript)
    return {
        "transcript": transcript,
        "intent": intent,
        "matched_phrase": matched_phrase,
        "edit_distance": distance,
        "recognized": intent is not None,
    }
