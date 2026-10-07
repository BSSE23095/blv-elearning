"""
Course and module navigation (Section 3.2).

Home screen: course grid with "Open Course" / "Read Info" per card.
Inside a course: modules navigated linearly with progress bar,
breadcrumbs, and Previous/Next — reachable via Tab key and voice
commands (see voice_nav.py for the intent mapping).
"""
from flask import Blueprint, render_template, session, redirect, url_for, g

from ..db import get_db
from ..text_simplifier import simplify

course_bp = Blueprint("course", __name__)


def _require_login():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
    return None


@course_bp.route("/")
def home():
    redirect_resp = _require_login()
    if redirect_resp:
        return redirect_resp

    db = get_db()
    courses = db.execute("SELECT * FROM courses ORDER BY id").fetchall()
    return render_template("home.html", courses=courses, user_name=session.get("user_name"))


@course_bp.route("/course/<int:course_id>")
def course_detail(course_id):
    redirect_resp = _require_login()
    if redirect_resp:
        return redirect_resp

    db = get_db()
    course = db.execute("SELECT * FROM courses WHERE id = ?", (course_id,)).fetchone()
    modules = db.execute(
        "SELECT * FROM modules WHERE course_id = ? ORDER BY sequence", (course_id,)
    ).fetchall()

    progress_rows = db.execute(
        "SELECT module_id, completed FROM progress WHERE user_id = ?",
        (session["user_id"],),
    ).fetchall()
    completed_ids = {row["module_id"] for row in progress_rows if row["completed"]}

    return render_template(
        "course.html", course=course, modules=modules, completed_ids=completed_ids
    )


@course_bp.route("/course/<int:course_id>/module/<int:module_id>")
def module_detail(course_id, module_id):
    redirect_resp = _require_login()
    if redirect_resp:
        return redirect_resp

    db = get_db()
    course = db.execute("SELECT * FROM courses WHERE id = ?", (course_id,)).fetchone()
    module = db.execute("SELECT * FROM modules WHERE id = ?", (module_id,)).fetchone()
    blocks = db.execute(
        "SELECT * FROM content_blocks WHERE module_id = ? ORDER BY sequence", (module_id,)
    ).fetchall()

    modules = db.execute(
        "SELECT * FROM modules WHERE course_id = ? ORDER BY sequence", (course_id,)
    ).fetchall()
    module_ids = [m["id"] for m in modules]
    idx = module_ids.index(module_id)
    prev_id = module_ids[idx - 1] if idx > 0 else None
    next_id = module_ids[idx + 1] if idx < len(module_ids) - 1 else None

    progress_rows = db.execute(
        "SELECT module_id, completed FROM progress WHERE user_id = ?",
        (session["user_id"],),
    ).fetchall()
    completed_ids = {row["module_id"] for row in progress_rows if row["completed"]}

    return render_template(
        "module.html",
        course=course,
        module=module,
        blocks=blocks,
        prev_id=prev_id,
        next_id=next_id,
        progress_percent=int(((idx + 1) / len(module_ids)) * 100),
        module_steps=modules,
        current_index=idx,
        completed_ids=completed_ids,
    )


@course_bp.route("/course/<int:course_id>/module/<int:module_id>/quiz")
def module_quiz(course_id, module_id):
    redirect_resp = _require_login()
    if redirect_resp:
        return redirect_resp

    db = get_db()
    questions = db.execute(
        "SELECT * FROM quiz_questions WHERE module_id = ?", (module_id,)
    ).fetchall()
    return render_template("quiz.html", course_id=course_id, module_id=module_id, questions=questions)


@course_bp.route("/course/<int:course_id>/module/<int:module_id>/quiz/submit", methods=["POST"])
def submit_quiz(course_id, module_id):
    from flask import request

    redirect_resp = _require_login()
    if redirect_resp:
        return redirect_resp

    db = get_db()
    questions = db.execute(
        "SELECT * FROM quiz_questions WHERE module_id = ?", (module_id,)
    ).fetchall()

    correct = 0
    for q in questions:
        answer = request.form.get(f"q{q['id']}")
        if answer == q["correct_choice"]:
            correct += 1

    passed = correct == len(questions) if questions else True
    if passed:
        db.execute(
            """INSERT INTO progress (user_id, module_id, completed, completed_at)
               VALUES (?, ?, 1, CURRENT_TIMESTAMP)
               ON CONFLICT(user_id, module_id)
               DO UPDATE SET completed = 1, completed_at = CURRENT_TIMESTAMP""",
            (session["user_id"], module_id),
        )
        db.commit()

    return render_template(
        "quiz_result.html",
        course_id=course_id,
        module_id=module_id,
        correct=correct,
        total=len(questions),
        passed=passed,
    )
