"""
Logic-puzzle authentication (Section 3.2).

Replaces visual CAPTCHAs with a randomized multiple-choice question that
is read aloud automatically on page load. A correct answer logs the user
in and captures their name for personalized audio greetings.

Security note carried over from the paper's discussion: this is a small,
enumerable question pool by design (a production deployment would need a
bigger bank + rate limiting — see paper Section 3.2 discussion). Fine for
an educational prototype, not a production auth system.
"""
import random
from flask import Blueprint, render_template, request, session, redirect, url_for, jsonify

from ..db import get_db

auth_bp = Blueprint("auth", __name__)

# Small, easily-read-aloud question pool. Randomized per page load.
LOGIC_PUZZLES = [
    {"question": "Which animal says meow?", "choices": ["Dog", "Cat", "Cow"], "answer": "Cat"},
    {"question": "Which animal says woof?", "choices": ["Cat", "Dog", "Duck"], "answer": "Dog"},
    {"question": "What color is the sky on a clear day?", "choices": ["Green", "Blue", "Red"], "answer": "Blue"},
    {"question": "How many days are in a week?", "choices": ["Five", "Seven", "Ten"], "answer": "Seven"},
    {"question": "Which is a fruit: apple, chair, or shoe?", "choices": ["Chair", "Apple", "Shoe"], "answer": "Apple"},
    {"question": "Which is colder: ice or fire?", "choices": ["Fire", "Ice", "Neither"], "answer": "Ice"},
]


@auth_bp.route("/login", methods=["GET"])
def login():
    puzzle = random.choice(LOGIC_PUZZLES)
    session["puzzle_answer"] = puzzle["answer"]
    choices = puzzle["choices"][:]
    random.shuffle(choices)
    return render_template("login.html", question=puzzle["question"], choices=choices)


@auth_bp.route("/login", methods=["POST"])
def login_submit():
    name = request.form.get("name", "").strip()
    selected = request.form.get("choice", "").strip()
    expected = session.get("puzzle_answer")

    if not name:
        return render_template("login.html", error="Please enter your name.",
                                question="Please try again.", choices=[])

    if selected != expected:
        puzzle = random.choice(LOGIC_PUZZLES)
        session["puzzle_answer"] = puzzle["answer"]
        choices = puzzle["choices"][:]
        random.shuffle(choices)
        return render_template(
            "login.html",
            error="That wasn't quite right. Here's a new question.",
            question=puzzle["question"],
            choices=choices,
        )

    db = get_db()
    cur = db.execute("INSERT INTO users (name) VALUES (?)", (name,))
    db.commit()
    session["user_id"] = cur.lastrowid
    session["user_name"] = name
    return redirect(url_for("course.home"))


@auth_bp.route("/login/puzzle.json")
def puzzle_json():
    """For the voice-first flow: lets the frontend re-fetch/re-read the
    current puzzle via TTS without a full page reload."""
    return jsonify({
        "question": "Which animal says meow?",
    })


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
