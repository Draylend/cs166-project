# Using Flask for Web Interface (GUI)

from flask import Flask, render_template, request, redirect, session
from database import get_db
from decimal import Decimal
from datetime import datetime   # Converting CSV timestamp into readable format

import psycopg2
import psycopg2.extras

# Initialize Flask application
app = Flask(__name__)
app.secret_key = "cs166"    # For verifying sessions

# Function for calling Home Page
@app.route("/")
def home():
    return render_template("index.html", title="Home Page")

# Logging Users Out
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

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
    # Make sure user is logged in
    if "login" not in session:
        return redirect("/login")

    # Grab user
    username = session["login"]

    # Get database information (connection)
    conn = get_db()
    # Grab cursor (selector)
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Search for logged in user
    cur.execute("""
        SELECT login, role
        FROM users
        WHERE login = %s;
    """, (username,))

    # Grab data for logged in user
    user = cur.fetchone()

    # Close connection and cursor
    cur.close()
    conn.close()

    # Return user info
    return render_template(
        "dashboard.html", 
        title="Dashboard", 
        user=user
    )

# Function for calling Auctions Page
@app.route("/auctions")
def auctions():
    # Make sure user is logged in
    if "login" not in session:
        return redirect("/login")

    # Get database information (connection)
    conn = get_db()
    # Grab cursor (selector)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Search for auctions whose name contains the query
    cur.execute("""
        SELECT *
        FROM auction A, item I
        WHERE A.item_id = I.item_id
    """)

    # Get all matching results
    results = cur.fetchall()

    # Add values to external values to return results
    for auction in results:
        auction["high_threshold"] = auction["starting_price"] * Decimal("1.3")

        # Format timestamp
        start_dt = auction["start_time"]
        end_dt = auction["end_time"]

        readable_start = start_dt.strftime("%b %d, %Y at %I:%M %p")
        readable_end = end_dt.strftime("%b %d, %Y at %I:%M %p")

        # Compute time remaining
        end_time = auction["end_time"]
        now = datetime.now()

        remaining = end_time - now

        # Format string
        if remaining.total_seconds() <= 0:
            time_left = None
        else:
            days = remaining.days
            seconds = remaining.seconds
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60

            # Cleaner Formatting
            if days > 0:
                time_left = f"{days}d {hours}h remaining"
            elif hours > 0:
                time_left = f"{hours}h {minutes}m remaining"
            else:
                time_left = f"{minutes}m remaining"

        auction["readable_start"] = readable_start
        auction["readable_end"] = readable_end
        auction["time_left"] = time_left

    # Close connection and cursor
    cur.close()
    conn.close()

    # Return results
    return render_template(
        "auctions.html",
        title="Browse Auctions",
        results=results,
    )

# Function for calling Items Page
@app.route("/items")
def items():
    # Make sure user is logged in
    if "login" not in session:
        return redirect("/login")
        
    # Get database information (connection)
    conn = get_db()
    # Grab cursor (selector)
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Search for items whose name contains the query
    cur.execute("""
        SELECT *
        FROM item
    """)

    # Get all matching results
    results = cur.fetchall()

    # Close connection and cursor
    cur.close()
    conn.close()

    # Return results
    return render_template(
        "items.html",
        title="Browse Items",
        results=results,
    )

# Function for calling Profile Page
@app.route("/profile")
def profile():
    # Make sure user is logged in
    if "login" not in session:
        return redirect("/login")

    # Grab user
    username = session["login"]

    # Get database information (connection)
    conn = get_db()
    # Grab cursor (selector)
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Search for logged in user
    cur.execute("""
        SELECT *
        FROM users
        WHERE login = %s;
    """, (username,))

    # Grab data for logged in user
    user = cur.fetchone()

    # Close connection and cursor
    cur.close()
    conn.close()

    # Return user info
    return render_template(
        "profile.html", 
        title="View Profile", 
        user=user
    )
    
# Function for calling Bid Page
@app.route("/bid")
def bid():
    return render_template("bid.html", title="Bid")
    
# Function for calling Shipment Page
@app.route("/shipment")
def shipment():
    # Make sure user is logged in
    if "login" not in session:
        return redirect("/login")

    # Grab user
    username = session["login"]

    # Get database information (connection)
    conn = get_db()
    # Grab cursor (selector)
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Search for logged in user
    cur.execute("""
        SELECT login, role
        FROM users U, shipment S, auction A, item I
        WHERE U.login = %s AND S.auction_id = A.auction_id AND U.login = A.winner_login AND A.item_id = I.item_id;
    """, (username,))

    # Grab data for logged in user
    results = cur.fetchone()

    # Close connection and cursor
    cur.close()
    conn.close()

    # Return user info
    return render_template(
        "shipment.html", 
        title="View Shipments", 
        results=results
    )

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
        FROM item I
        WHERE item_name ILIKE %s;
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