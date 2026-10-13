# RollBook – Student Management System

Micro project built with **Python, Flask, Jinja2, Werkzeug, SQLite, HTML and CSS**.

## Features
- Admin login (password stored as a Werkzeug hash)
- Dashboard: total students, per-course and per-year counts, recent additions
- Add, view, edit and delete students
- Search by name / roll number / email and filter by course
- Form validation, unique roll numbers, flash messages

## Run it
```bash
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000 and sign in with **admin / admin123**.
The database file `students.db` is created automatically on first run.

## Structure
```
student_management/
├── app.py              # routes, database, validation
├── requirements.txt
├── templates/          # Jinja2 templates (base.html is the layout)
│   ├── base.html  login.html  dashboard.html
│   ├── students.html  student_form.html  404.html
└── static/style.css
```
