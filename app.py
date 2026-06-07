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

# Function for calling Sign-Up Page
@app.route("/signup", methods=["GET", "POST"])
def signup():
    # If the request was a submission (POST)
    if request.method == "POST":
        # Gather data
        login = request.form["login"]
        password = request.form["password"]
        phone = request.form["phone"]
        address = request.form["address"]
        # If user filled out this field
        fav_category = request.form["fav_category"] if request.form["fav_category"] else None

        # Get database information (connection)
        conn = get_db()
        # Grab cursor (selector)
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # Input validation for login (primary key)
        cur.execute("SELECT login FROM users WHERE login = %s;", (login,))
        existing = cur.fetchone()

        if existing:
            return render_template("signup.html", title="Sign Up", error="Username already exists")

        # Execute query
        cur.execute("""
            INSERT INTO users
                (login, password, phone_num, address, role, favorite_category)
            VALUES
                (%s, %s, %s, %s, 'Buyer', %s);
        """, (login, password, phone, address, fav_category))

        # Save insertion and close connection/cursor
        conn.commit()
        cur.close()
        conn.close()

        return redirect("/dashboard")

    # Load signup page
    return render_template("signup.html", title="Sign Up")

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

# Function for calling Auctions Page
@app.route("/auctions")
def auctions():
    return render_template("auctions.html", title="Browse Auctions")

# Function for calling Items Page
@app.route("/items")
def items():
    return render_template("items.html", title="Browse Items")

# Function for calling Profile Page
@app.route("/profile")
def profile():
    return render_template("profile.html", title="Profile")
    
# Function for calling Bid Page
@app.route("/bid")
def bid():
    return render_template("bid.html", title="Bid")
    
# Function for calling Shipment Page
@app.route("/shipment")
def shipment():
    return render_template("shipment.html", title="Shipment")

# Function for calling ManageItems Page
@app.route("/manageItems")
def manageItems():
    return render_template("manageItems.html", title="Manage Items")
    
# Function for calling ManageUsers Page
@app.route("/manageUsers")
def manageUsers():
    return render_template("manageUsers.html", title="Manage Users")

# Function for searching indexes of items
@app.route("/search", methods=["GET"]) # Query is added to URL itself and not body 
def search():
    query = request.args.get("query", "").strip()

    # No query so go back to dashboard
    if not query:
        return render_template("dashboard.html", title="Dashboard")

    # Get database information (connection)
    conn = get_db()
    # Grab cursor (selector)
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Search for items whose name contains the query
    cur.execute("""
        SELECT *
        FROM auction A, item I
        WHERE I.item_id = A.item_id AND item_name ILIKE %s;
    """, (f"%{query}%",))

    # Get all matching results
    results = cur.fetchall()

    # Close connection and cursor
    cur.close()
    conn.close()

    # Return results
    return render_template(
        "results.html",
        title="Search Results",
        query=query,
        results=results,
    )

# Run app locally
if __name__ == "__main__":
    app.run(debug=True, port=5001)