"""
Teacher dashboard (Section 3.5, "Dynamic Content Ingestion and Teacher
Dashboard").

Teachers log in via a secure dashboard and upload material as PDF, DOCX,
or plain text. Pipeline:
  1. PyPDF2 / python-docx strips formatting, extracting raw text blocks.
  2. Each block is passed through text_simplifier.simplify() before
     being stored in SQLite, keyed by course_id, module_id, and block
     sequence.
  3. Any images found in the upload are run through the MobileNetV2
     diagram pipeline automatically, generating alt-text with no teacher
     configuration needed.

The goal (per the paper): a non-technical teacher can populate the whole
platform without touching a line of code.
"""
import os
import uuid
from io import BytesIO

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from werkzeug.security import generate_password_hash, check_password_hash
import PyPDF2

from ..db import get_db
from ..text_simplifier import simplify
from ..diagram_classifier import classify_image

teacher_bp = Blueprint("teacher", __name__, url_prefix="/teacher")


def _require_teacher_login():
    if "teacher_id" not in session:
        return redirect(url_for("teacher.teacher_login"))
    return None


@teacher_bp.route("/register", methods=["GET", "POST"])
def teacher_register():
    """Simple one-time setup route to create a teacher account.
    In a production deployment this would be an admin-only action."""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if not username or not password:
            flash("Username and password are required.")
            return render_template("teacher/register.html")

        db = get_db()
        try:
            db.execute(
                "INSERT INTO teachers (username, password_hash) VALUES (?, ?)",
                (username, generate_password_hash(password)),
            )
            db.commit()
        except Exception:
            flash("That username is already taken.")
            return render_template("teacher/register.html")

        return redirect(url_for("teacher.teacher_login"))

    return render_template("teacher/register.html")


@teacher_bp.route("/login", methods=["GET", "POST"])
def teacher_login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        db = get_db()
        teacher = db.execute(
            "SELECT * FROM teachers WHERE username = ?", (username,)
        ).fetchone()

        if teacher and check_password_hash(teacher["password_hash"], password):
            session["teacher_id"] = teacher["id"]
            session["teacher_name"] = teacher["username"]
            return redirect(url_for("teacher.dashboard"))

        flash("Invalid username or password.")

    return render_template("teacher/login.html")


@teacher_bp.route("/logout")
def teacher_logout():
    session.pop("teacher_id", None)
    session.pop("teacher_name", None)
    return redirect(url_for("teacher.teacher_login"))


@teacher_bp.route("/dashboard")
def dashboard():
    redirect_resp = _require_teacher_login()
    if redirect_resp:
        return redirect_resp

    db = get_db()
    courses = db.execute("SELECT * FROM courses ORDER BY id").fetchall()
    return render_template("teacher/dashboard.html", courses=courses)


def _extract_text_from_pdf(file_storage) -> str:
    reader = PyPDF2.PdfReader(BytesIO(file_storage.read()))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _extract_text_from_docx(file_storage) -> str:
    import docx  # python-docx
    document = docx.Document(BytesIO(file_storage.read()))
    return "\n".join(p.text for p in document.paragraphs)


def _extract_text_from_html_or_txt(file_storage) -> str:
    from bs4 import BeautifulSoup
    raw = file_storage.read().decode("utf-8", errors="ignore")
    # BeautifulSoup strips any HTML formatting; plain .txt passes through untouched.
    soup = BeautifulSoup(raw, "html.parser")
    return soup.get_text(separator="\n")


@teacher_bp.route("/upload", methods=["GET", "POST"])
def upload_content():
    redirect_resp = _require_teacher_login()
    if redirect_resp:
        return redirect_resp

    db = get_db()
    courses = db.execute("SELECT * FROM courses ORDER BY id").fetchall()

    if request.method == "POST":
        course_id = request.form.get("course_id", type=int)
        module_title = request.form.get("module_title", "").strip()
        uploaded_file = request.files.get("content_file")

        if not (course_id and module_title and uploaded_file and uploaded_file.filename):
            flash("Course, module title, and a file are all required.")
            return redirect(url_for("teacher.upload_content"))

        ext = os.path.splitext(uploaded_file.filename)[1].lower()
        if ext == ".pdf":
            raw_text = _extract_text_from_pdf(uploaded_file)
        elif ext == ".docx":
            raw_text = _extract_text_from_docx(uploaded_file)
        elif ext in (".txt", ".html", ".htm"):
            raw_text = _extract_text_from_html_or_txt(uploaded_file)
        else:
            flash(f"Unsupported file type: {ext}. Use PDF, DOCX, or plain text.")
            return redirect(url_for("teacher.upload_content"))

        # Split into paragraph-sized blocks
        blocks = [b.strip() for b in raw_text.split("\n") if b.strip()]

        # Determine next module sequence number for this course
        existing = db.execute(
            "SELECT COALESCE(MAX(sequence), 0) AS max_seq FROM modules WHERE course_id = ?",
            (course_id,),
        ).fetchone()
        next_seq = existing["max_seq"] + 1

        cur = db.execute(
            "INSERT INTO modules (course_id, title, sequence) VALUES (?, ?, ?)",
            (course_id, module_title, next_seq),
        )
        module_id = cur.lastrowid

        for i, block in enumerate(blocks, start=1):
            simplified = simplify(block)
            db.execute(
                """INSERT INTO content_blocks
                   (course_id, module_id, sequence, raw_text, simplified_text)
                   VALUES (?, ?, ?, ?, ?)""",
                (course_id, module_id, i, block, simplified),
            )

        db.commit()
        flash(f"Uploaded '{module_title}' with {len(blocks)} content block(s).")
        return redirect(url_for("teacher.dashboard"))

    return render_template("teacher/upload.html", courses=courses)


@teacher_bp.route("/upload-image", methods=["POST"])
def upload_image_for_alt_text():
    """
    Any images found in uploaded course material go straight to the
    MobileNetV2 pipeline for alt-text generation, automatically, with no
    teacher configuration needed (Section 3.5).
    """
    redirect_resp = _require_teacher_login()
    if redirect_resp:
        return redirect_resp

    image_file = request.files.get("image")
    if not image_file:
        flash("No image uploaded.")
        return redirect(url_for("teacher.upload_content"))

    filename = f"{uuid.uuid4().hex}{os.path.splitext(image_file.filename)[1]}"
    save_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
    image_file.save(save_path)

    predicted_class, confidence, description = classify_image(save_path)
    flash(f"Auto-generated alt text ({predicted_class}, {confidence:.0%} confidence): {description}")
    return redirect(url_for("teacher.upload_content"))
