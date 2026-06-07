# Using Flask for Web Interface (GUI)

from flask import Flask, render_template, request, redirect, session
from database import get_db

import psycopg2
import psycopg2.extras

# Initialize Flask application
app = Flask(__name__)
app.secret_key = "cs166"    # For verifying sessions

# Function for calling Home Page
@app.route("/")
def home():
    return render_template("index.html", title="Home Page")

# Function for calling Login Page
@app.route("/login", methods=["GET", "POST"])
def login():
    # If the request was a submission (POST)
    if request.method == "POST":
        # Gather data
        login = request.form["login"]
        password = request.form["password"]

        # Get database information (connection)
        conn = get_db()
        # Grab cursor (selector)
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # Execute query
        cur.execute("""
            SELECT login, role, password
            FROM users
            WHERE login = %s;
        """, (login,))

        # Grab user and close connection/cursor
        user = cur.fetchone()
        cur.close()
        conn.close()

        # If there was a user, check password
        if user and user["password"] == password:
            # Store login and role, send to dashboard page
            session["login"] = user["login"]
            session["role"] = user["role"]
            return redirect("/dashboard")

        # If no user was found with this login or password didn't match
        return render_template("login.html", title="Login Page", error="Invalid login")

    # Load login page
    return render_template("login.html", title="Login")

# Function for calling Dashboard Page
@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html", title="Dashboard")

# Run app locally
if __name__ == "__main__":
    app.run(debug=True, port=5001)