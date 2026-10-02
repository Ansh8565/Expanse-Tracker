from flask import Flask, render_template, request, redirect, session
import sqlite3
import os
import traceback
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "expense_tracker_secret_key_12345")


def get_db():
    # Standard SQLite database file for Render deployment
    db_path = "expense.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Ensure database tables exist
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS expenses(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            amount REAL,
            category TEXT,
            user_id INTEGER
        )
    """)
    conn.commit()

    return conn


@app.errorhandler(Exception)
def handle_exception(e):
    tb = traceback.format_exc()
    print("UNHANDLED EXCEPTION:", tb)
    return f"<h2>Application Error</h2><pre>{tb}</pre>", 500


def login_required(route_function):
    @wraps(route_function)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect("/login")
        return route_function(*args, **kwargs)

    return wrapper


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:
            return "Username and password are required", 400

        hashed_password = generate_password_hash(password, method="pbkdf2:sha256")
        conn = get_db()

        try:
            conn.execute(
                "INSERT INTO users(username, password) VALUES (?, ?)",
                (username, hashed_password)
            )
            conn.commit()
        except sqlite3.IntegrityError:
            return "Username already exists", 400
        finally:
            conn.close()

        return redirect("/login")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE username=?",
            (username,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            return redirect("/")
        else:
            return "Invalid username or password", 401

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/")
@login_required
def index():
    search = request.args.get("search", "")
    category = request.args.get("category", "")

    conn = get_db()

    query = "SELECT * FROM expenses WHERE user_id=?"
    params = [session["user_id"]]

    if search:
        query += " AND title LIKE ?"
        params.append("%" + search + "%")

    if category:
        query += " AND category=?"
        params.append(category)

    expenses = conn.execute(query, params).fetchall()

    summary_data = conn.execute(
        """
        SELECT category, SUM(amount) as total
        FROM expenses
        WHERE user_id=?
        GROUP BY category
        """,
        (session["user_id"],)
    ).fetchall()

    summary = [[item["category"], item["total"]] for item in summary_data]

    conn.close()

    return render_template("index.html", expenses=expenses, summary=summary)


@app.route("/add", methods=["GET", "POST"])
@login_required
def add():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        amount_str = request.form.get("amount", "0")
        category = request.form.get("category", "").strip()

        try:
            amount = float(amount_str)
        except (ValueError, TypeError):
            return "Invalid amount format", 400

        conn = get_db()
        try:
            conn.execute(
                """
                INSERT INTO expenses(title, amount, category, user_id)
                VALUES (?, ?, ?, ?)
                """,
                (title, amount, category, session["user_id"])
            )
            conn.commit()
        finally:
            conn.close()

        return redirect("/")

    return render_template("add.html")


@app.route("/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit(id):
    conn = get_db()

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        amount_str = request.form.get("amount", "0")
        category = request.form.get("category", "").strip()

        try:
            amount = float(amount_str)
        except (ValueError, TypeError):
            conn.close()
            return "Invalid amount format", 400

        conn.execute(
            """
            UPDATE expenses
            SET title=?, amount=?, category=?
            WHERE id=? AND user_id=?
            """,
            (title, amount, category, id, session["user_id"])
        )
        conn.commit()
        conn.close()

        return redirect("/")

    expense = conn.execute(
        "SELECT * FROM expenses WHERE id=? AND user_id=?",
        (id, session["user_id"])
    ).fetchone()
    conn.close()

    if expense is None:
        return "Expense not found", 404

    return render_template("edit.html", expense=expense)


@app.route("/delete/<int:id>")
@login_required
def delete(id):
    conn = get_db()
    conn.execute(
        "DELETE FROM expenses WHERE id=? AND user_id=?",
        (id, session["user_id"])
    )
    conn.commit()
    conn.close()

    return redirect("/")


if __name__ == "__main__":
    print("Running Expense Tracker App...")
    app.run(debug=True)
