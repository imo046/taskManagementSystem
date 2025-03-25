import os
import csv
import sqlite3
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

# Initialize the Flask app
app = Flask(__name__)
app.secret_key = 'replace_with_your_secret_key'
DATABASE = 'app.db'

# Configure Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# ----- Database and User Model -----

# User model using UserMixin so it works with Flask-Login
class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def get_user_by_username(username):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, username, password FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    conn.close()
    if row is not None:
        return User(row["id"], row["username"], row["password"])
    return None

def get_user_by_id(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, username, password FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    if row is not None:
        return User(row["id"], row["username"], row["password"])
    return None

@login_manager.user_loader
def load_user(user_id):
    return get_user_by_id(user_id)

def init_db():
    if not os.path.exists(DATABASE):
        conn = get_db_connection()
        conn.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        # Create a default test user: username=testuser, password=password123
        password_hash = generate_password_hash("password123")
        conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", ("testuser", password_hash))
        conn.commit()
        conn.close()

# Initialize database if needed
init_db()

# ----- Routes for User Authentication -----

@app.route("/")
def index():
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = get_user_by_username(username)
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for("upload_csv"))
        else:
            flash("Invalid username or password")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

# ----- Routes for CSV Upload and Viewing -----

@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload_csv():
    if request.method == "POST":
        if "csv_file" not in request.files:
            flash("No file part")
            return redirect(request.url)
        file = request.files["csv_file"]
        if file.filename == "":
            flash("No selected file")
            return redirect(request.url)
        if file:
            # Read CSV content using csv.DictReader
            csv_contents = []
            file_lines = file.stream.read().decode("utf-8").splitlines()
            reader = csv.DictReader(file_lines)
            for row in reader:
                csv_contents.append(row)
            return render_template("csv_view.html", csv_contents=csv_contents)
    return render_template("upload.html")

# ----- Example REST API Endpoint -----

@app.route("/api/csv", methods=["POST"])
@login_required
def api_csv():
    if "csv_file" not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files["csv_file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400
    csv_contents = []
    file_lines = file.stream.read().decode("utf-8").splitlines()
    reader = csv.DictReader(file_lines)
    for row in reader:
        csv_contents.append(row)
    return jsonify(csv_contents), 200

if __name__ == "__main__":
    app.run(debug=True)