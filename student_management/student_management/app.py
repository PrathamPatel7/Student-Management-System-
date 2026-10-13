"""Student Management System - Flask + SQLite + Jinja2 + Werkzeug"""
import os
import re
import sqlite3
from functools import wraps

from flask import (Flask, flash, g, redirect, render_template, request,
                   session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = "change-this-secret-key-before-deploying"
DATABASE = os.path.join(app.root_path, "students.db")

COURSES = ["Computer Engineering", "Information Technology",
           "Mechanical Engineering", "Civil Engineering",
           "Electrical Engineering", "Electronics & Communication"]
YEARS = [1, 2, 3, 4]


# ---------------------------------------------------------------- database
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_error):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Create tables and a default admin account on first run."""
    db = sqlite3.connect(DATABASE)
    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS students (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            roll_no    TEXT NOT NULL UNIQUE,
            name       TEXT NOT NULL,
            email      TEXT NOT NULL,
            phone      TEXT,
            course     TEXT NOT NULL,
            year       INTEGER NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """)
    exists = db.execute("SELECT 1 FROM users WHERE username = 'admin'").fetchone()
    if not exists:
        db.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)",
                   ("admin", generate_password_hash("admin123")))
    db.commit()
    db.close()


# ------------------------------------------------------------------- auth
def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please sign in to continue.", "error")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


@app.route("/", methods=["GET"])
def index():
    return redirect(url_for("dashboard" if "user_id" in session else "login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = get_db().execute("SELECT * FROM users WHERE username = ?",
                                (username,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect(url_for("dashboard"))
        flash("Wrong username or password.", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been signed out.", "success")
    return redirect(url_for("login"))


# -------------------------------------------------------------- dashboard
@app.route("/dashboard")
@login_required
def dashboard():
    db = get_db()
    total = db.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    by_course = db.execute(
        "SELECT course, COUNT(*) AS n FROM students GROUP BY course ORDER BY n DESC"
    ).fetchall()
    by_year = db.execute(
        "SELECT year, COUNT(*) AS n FROM students GROUP BY year ORDER BY year"
    ).fetchall()
    recent = db.execute(
        "SELECT * FROM students ORDER BY id DESC LIMIT 5").fetchall()
    biggest = max((r["n"] for r in by_course), default=1)
    return render_template("dashboard.html", total=total, by_course=by_course,
                           by_year=by_year, recent=recent, biggest=biggest)


# --------------------------------------------------------------- students
def validate(form):
    data = {
        "roll_no": form.get("roll_no", "").strip().upper(),
        "name": form.get("name", "").strip(),
        "email": form.get("email", "").strip().lower(),
        "phone": form.get("phone", "").strip(),
        "course": form.get("course", "").strip(),
        "year": form.get("year", "").strip(),
    }
    errors = []
    if not data["roll_no"]:
        errors.append("Roll number is required.")
    if len(data["name"]) < 2:
        errors.append("Enter the student's full name.")
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", data["email"]):
        errors.append("Enter a valid email address.")
    if data["phone"] and not re.match(r"^\+?[0-9]{10,13}$", data["phone"]):
        errors.append("Phone must be 10 to 13 digits.")
    if data["course"] not in COURSES:
        errors.append("Choose a course from the list.")
    if not data["year"].isdigit() or int(data["year"]) not in YEARS:
        errors.append("Choose a year between 1 and 4.")
    return data, errors


@app.route("/students")
@login_required
def students():
    q = request.args.get("q", "").strip()
    course = request.args.get("course", "").strip()
    sql = "SELECT * FROM students WHERE 1=1"
    params = []
    if q:
        sql += " AND (name LIKE ? OR roll_no LIKE ? OR email LIKE ?)"
        params += [f"%{q}%"] * 3
    if course:
        sql += " AND course = ?"
        params.append(course)
    sql += " ORDER BY roll_no"
    rows = get_db().execute(sql, params).fetchall()
    return render_template("students.html", students=rows, q=q,
                           course=course, courses=COURSES)


@app.route("/students/add", methods=["GET", "POST"])
@login_required
def add_student():
    data = {"roll_no": "", "name": "", "email": "", "phone": "",
            "course": "", "year": ""}
    if request.method == "POST":
        data, errors = validate(request.form)
        if not errors:
            try:
                db = get_db()
                db.execute(
                    "INSERT INTO students (roll_no, name, email, phone, course, year)"
                    " VALUES (?, ?, ?, ?, ?, ?)",
                    (data["roll_no"], data["name"], data["email"], data["phone"],
                     data["course"], int(data["year"])))
                db.commit()
                flash(f"{data['name']} was added.", "success")
                return redirect(url_for("students"))
            except sqlite3.IntegrityError:
                errors.append(f"Roll number {data['roll_no']} already exists.")
        for e in errors:
            flash(e, "error")
    return render_template("student_form.html", student=data, courses=COURSES,
                           years=YEARS, editing=False)


@app.route("/students/<int:student_id>/edit", methods=["GET", "POST"])
@login_required
def edit_student(student_id):
    db = get_db()
    student = db.execute("SELECT * FROM students WHERE id = ?",
                         (student_id,)).fetchone()
    if student is None:
        flash("That student no longer exists.", "error")
        return redirect(url_for("students"))
    if request.method == "POST":
        data, errors = validate(request.form)
        if not errors:
            try:
                db.execute(
                    "UPDATE students SET roll_no=?, name=?, email=?, phone=?,"
                    " course=?, year=? WHERE id=?",
                    (data["roll_no"], data["name"], data["email"], data["phone"],
                     data["course"], int(data["year"]), student_id))
                db.commit()
                flash(f"{data['name']} was updated.", "success")
                return redirect(url_for("students"))
            except sqlite3.IntegrityError:
                errors.append(f"Roll number {data['roll_no']} already exists.")
        for e in errors:
            flash(e, "error")
        student = data
    return render_template("student_form.html", student=student, courses=COURSES,
                           years=YEARS, editing=True, student_id=student_id)


@app.route("/students/<int:student_id>/delete", methods=["POST"])
@login_required
def delete_student(student_id):
    db = get_db()
    row = db.execute("SELECT name FROM students WHERE id = ?",
                     (student_id,)).fetchone()
    if row:
        db.execute("DELETE FROM students WHERE id = ?", (student_id,))
        db.commit()
        flash(f"{row['name']} was deleted.", "success")
    return redirect(url_for("students"))


# ----------------------------------------------------------------- errors
@app.errorhandler(404)
def not_found(_e):
    return render_template("404.html"), 404


init_db()

if __name__ == "__main__":
    app.run(debug=True)
