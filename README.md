# Audio-First E-Learning Interface for Blind and Low-Vision Students

Reference implementation for the paper *"Audio-First E-Learning Interface
for Blind and Low-Vision Students"* (Khan, Bilal, Asif — Department of
Software Engineering, Information Technology University, Lahore).

This repo implements every component described in the paper's
methodology (Section 3), in a single deployable Flask application.

## Feature → code map

| Paper feature (Section 3.2) | Code |
|---|---|
| Logic puzzle authentication | `app/routes/auth.py` |
| Course/module navigation, breadcrumbs, progress bar | `app/routes/course.py`, `app/templates/course.html`, `module.html` |
| NLP text simplification (50-item substitution table, sentence splitting, abbreviation expansion) | `app/text_simplifier.py` |
| Dual-engine neural TTS (gTTS + pyttsx3 offline fallback) | `app/tts_engine.py`, `app/routes/tts.py` |
| MobileNetV2 diagram classifier + template-driven descriptions | `app/diagram_classifier.py`, `train_classifier.py` |
| Voice command navigation (14 intents + Levenshtein fallback) | `app/voice_nav.py`, `app/routes/voice.py`, `app/static/js/voice-nav.js` |
| Touch gesture controls (5 gestures, Pointer Events API) | `app/static/js/gestures.js` |
| High contrast + font scaling (14–28pt) | `app/static/css/main.css`, `app/static/js/accessibility.js` |
| Progress tracking | `app/routes/course.py` (`progress` table) |
| ARIA-compliant HTML5 frontend | `app/templates/*.html` |
| Teacher dashboard / dynamic content ingestion (Section 3.5) | `app/routes/teacher.py` |

## Setup

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

Then open `http://localhost:5000`. The database is created automatically
on first run with two seeded demo courses (matching the paper's "two
course modules" mentioned in Section 3.2).

## Plugging in your real diagram classifier weights

The repo ships with a fully wired classifier pipeline, but it runs with
randomly-initialized weights until you supply trained ones (the paper
reports 84.3% validation accuracy on a 727-image, 7-category dataset —
those weights are not something a fresh clone can reproduce without your
original dataset).

1. Arrange your dataset as an `ImageFolder`:
   ```
   data/diagrams/
       bar_chart/*.jpg
       line_chart/*.jpg
       pie_chart/*.jpg
       flowchart/*.jpg
       anatomical/*.jpg
       geometrical/*.jpg
       circuit/*.jpg
   ```
2. Train:
   ```bash
   python train_classifier.py --data-dir data/diagrams --epochs 30
   ```
   This reproduces the exact methodology in Section 3.3: MobileNetV2
   feature extractor frozen, single FC head, Adam (lr=0.001), 30 epochs,
   cross-entropy loss, with an optional `--weighted-loss` flag to
   reproduce the weighted cross-entropy experiment the paper found did
   *not* help (83.7% vs 84.3%).
3. Weights are saved to `app/models/diagram_classifier.pt` and picked up
   automatically the next time the app starts.

## Plugging in your real substitution table

Drop a flat JSON file (`{"complex_word": "simple_word", ...}`) at
`app/data/substitution_table.json` and `text_simplifier.py` will load it
instead of the small starter table included here.

## Teacher dashboard

Visit `/teacher/register` once to create a teacher account, then
`/teacher/login` → `/teacher/dashboard` to upload PDF/DOCX/plain-text
course material. Content is automatically split into blocks, run through
the same NLP simplification pipeline, and stored — matching Section 3.5.

## What's a placeholder vs. what's real

- **Real, working**: Flask app structure, all routes, logic-puzzle auth,
  dual TTS engine with automatic offline fallback, NLP simplification
  pipeline (splitting/abbreviation logic), voice command intent matching
  + Levenshtein fallback, touch gestures, high contrast/font scaling,
  progress tracking, teacher content ingestion pipeline, MobileNetV2
  model architecture and training script.
- **Needs your data to match the paper's numbers**: the diagram
  classifier's trained weights (84.3% accuracy figure) and the exact
  50-item substitution table (built from Shardlow's list + Oxford 3000
  cross-referencing + manual course review).

## Limitations carried over from the paper

- The logic-puzzle question pool is intentionally small for this
  prototype; a production deployment would need a larger bank and rate
  limiting on repeated failed attempts (see paper Section 3.2).
- Course content is currently seeded/hardcoded plus whatever teachers
  upload — there's no bulk LMS import.
- No formal comparative usability study (Moodle + NVDA baseline) is
  included in this repo; that's future work per Section 4.6 of the paper.
