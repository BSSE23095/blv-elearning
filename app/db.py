"""
System Storage (SQLite) — as shown in Figure 1 of the paper.

Tables:
  - users: captured name from logic-puzzle login (personalized greetings)
  - courses / modules: course structure, either hardcoded seed data or
    dynamically ingested via the teacher dashboard (Section 3.5)
  - content_blocks: text blocks keyed by course_id, module_id, sequence,
    each pre-processed through text_simplifier.py before storage
  - progress: per-user module completion flags (mirrors the localStorage
    behaviour described in the paper, but persisted server-side too so
    it survives across devices)
  - diagram_uploads: log of classified diagrams + generated descriptions
"""
import sqlite3
import click
from flask import current_app, g


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(
            current_app.config["DATABASE"],
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    info TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS modules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    sequence INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS content_blocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    module_id INTEGER NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
    sequence INTEGER NOT NULL,
    raw_text TEXT NOT NULL,
    simplified_text TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS quiz_questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id INTEGER NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
    question TEXT NOT NULL,
    choice_a TEXT NOT NULL,
    choice_b TEXT NOT NULL,
    choice_c TEXT NOT NULL,
    correct_choice TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    module_id INTEGER NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
    completed INTEGER NOT NULL DEFAULT 0,
    completed_at TIMESTAMP,
    UNIQUE(user_id, module_id)
);

CREATE TABLE IF NOT EXISTS diagram_uploads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    predicted_class TEXT NOT NULL,
    confidence REAL NOT NULL,
    description TEXT NOT NULL,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS teachers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL
);
"""

SEED_DATA = """
INSERT INTO courses (id, title, info) VALUES
    (1, 'Introduction to Algebra', 'Covers linear equations, variables, and basic problem solving.'),
    (2, 'Foundations of Biology', 'Covers cells, tissues, and the basics of human anatomy.')
ON CONFLICT(id) DO NOTHING;

INSERT INTO modules (id, course_id, title, sequence) VALUES
    (1, 1, 'What is a Linear Equation?', 1),
    (2, 1, 'Solving for X', 2),
    (3, 2, 'Introduction to Cells', 1),
    (4, 2, 'Human Anatomy Basics', 2)
ON CONFLICT(id) DO NOTHING;

INSERT INTO content_blocks (course_id, module_id, sequence, raw_text, simplified_text) VALUES
    (1, 1, 1,
     'A linear equation is an equation of the first degree, meaning it has no exponents greater than one.',
     'A linear equation is an equation of the first degree, meaning it has no exponents greater than one.'),
    (1, 2, 1,
     'To solve for x, isolate the variable by performing the same operation on both sides of the equation.',
     'To solve for x, get the letter alone. Do the same thing to both sides of the equation.'),
    (2, 3, 1,
     'A cell is the basic structural and functional unit of all known living organisms.',
     'A cell is the basic building block of all living things.'),
    (2, 4, 1,
     'The human body is composed of several organ systems that work together to maintain homeostasis.',
     'The human body has several organ systems. They work together to keep the body balanced.');

INSERT INTO quiz_questions (module_id, question, choice_a, choice_b, choice_c, correct_choice) VALUES
    (1, 'What is the highest exponent allowed in a linear equation?', '1', '2', '3', 'a'),
    (2, 'What should you do to both sides of an equation when solving for x?', 'Nothing', 'The same operation', 'Different operations', 'b'),
    (3, 'What is the basic unit of all living organisms?', 'Atom', 'Cell', 'Tissue', 'b'),
    (4, 'What do organ systems work together to maintain?', 'Chaos', 'Homeostasis', 'Growth only', 'b');
"""


def init_db(app):
    with app.app_context():
        db = get_db()
        db.executescript(SCHEMA)

        # Seed data is only inserted once, on a genuinely empty database.
        # Without this guard, restarting the app would re-run the
        # unconditional content_blocks/quiz_questions inserts every time
        # and silently duplicate all seeded course content.
        already_seeded = db.execute("SELECT COUNT(*) AS c FROM courses").fetchone()["c"] > 0
        if not already_seeded:
            db.executescript(SEED_DATA)
            db.commit()

    app.teardown_appcontext(close_db)

    @app.cli.command("reset-db")
    def reset_db_command():
        """Drop and recreate all tables with seed data. Run: flask reset-db"""
        db = get_db()
        db.executescript("""
            DROP TABLE IF EXISTS progress;
            DROP TABLE IF EXISTS quiz_questions;
            DROP TABLE IF EXISTS content_blocks;
            DROP TABLE IF EXISTS modules;
            DROP TABLE IF EXISTS courses;
            DROP TABLE IF EXISTS diagram_uploads;
            DROP TABLE IF EXISTS users;
            DROP TABLE IF EXISTS teachers;
        """)
        db.executescript(SCHEMA)
        db.executescript(SEED_DATA)
        db.commit()
        click.echo("Database reset with seed data.")
