# Using Flask for Web Interface (GUI)

from flask import Flask, render_template, request, redirect, session, url_for
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
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

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
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

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
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

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
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

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

    # Grab viewer
    viewer_role = session["role"]

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

    # Check if the user is clicking on their own profile
    isHost = True if user["login"] == username else False

    # Close connection and cursor
    cur.close()
    conn.close()

    # Return user info
    return render_template(
        "profile.html", 
        title="View Profile", 
        user=user,
        isHost=isHost,
        viewer_role=viewer_role
    )

# Function for viewing Profiles
@app.route("/profile/<string:login>")
def view_profile(login):
    # Make sure user is logged in
    if "login" not in session:
        return redirect("/login")

    # Grab user
    username = session["login"]

    # Grab viewer
    viewer_role = session["role"]

    # Get database information (connection)
    conn = get_db()
    # Grab cursor (selector)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Search for logged in user
    cur.execute("""
        SELECT *
        FROM users
        WHERE login = %s;
    """, (login,))

    # Grab data for logged in user
    user = cur.fetchone()

    # Check if the user is clicking on their own profile
    isHost = True if user["login"] == username else False

    # Close connection and cursor
    cur.close()
    conn.close()

    message = request.args.get("message")
    error = request.args.get("error")

    # Return user info
    return render_template(
        "profile.html", 
        title="View Profile", 
        user=user,
        isHost=isHost,
        message=message,
        error=error,
        viewer_role=viewer_role
    )

# Function for updating Profile
@app.route("/update_profile", methods=["POST"])
def update_profile():
    # Make sure user is logged in
    if "login" not in session:
        return redirect("/login")

    # Grab viewer role to check for privileges
    viewer_role = session["role"]
    login = request.form["login"]

    # Grab form data
    password = request.form["password"]
    phone = request.form["phone_num"]
    address = request.form["address"]
    favorite_category = request.form["favorite_category"]

    # Only admins can change roles
    if viewer_role == "Admin" and "role" in request.form:
        new_role = request.form["role"]
    else:
        new_role = None

    conn = get_db()
    cur = conn.cursor()

    try:
        # If role was changed by admin
        if new_role:
            cur.execute("""
                UPDATE users
                SET password = %s,
                    phone_num = %s,
                    address = %s,
                    favorite_category = %s,
                    role = %s
                WHERE login = %s;
            """, (password, phone, address, favorite_category, new_role, login))
        else:
            cur.execute("""
                UPDATE users
                SET password = %s,
                    phone_num = %s,
                    address = %s,
                    favorite_category = %s
                WHERE login = %s;
            """, (password, phone, address, favorite_category, login))

        conn.commit()

        return redirect(url_for(
            "view_profile",
            login=login,
            message="Your changes have been successfully saved.",
            error=""
        ))
    # Error Message (most likely invalid role)
    except Exception as e:
        conn.rollback()
        error_msg = "Update failed. Invalid role, field values, or outstanding listings prevent update."

        return redirect(url_for(
            "view_profile",
            login=login,
            message="",
            error=error_msg
        ))

    
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
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

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
    # Make sure user is logged in
    if "login" not in session:
        return redirect("/login")

    query = request.args.get("query", "").strip()

    # No query so go back to dashboard
    if not query:
        return redirect("/dashboard")

    # Get database information (connection)
    conn = get_db()
    # Grab cursor (selector)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Search for items whose name, category, or description is similar
    # Left join to get all Items despite not being in auction
    cur.execute("""
        SELECT I.*, A.*
        FROM item I
        LEFT JOIN auction A ON I.item_id = A.item_id
        WHERE I.item_name ILIKE %s
        OR I.category ILIKE %s
        OR I.description ILIKE %s;
    """, (f"%{query}%", f"%{query}%", f"%{query}%"))

    # Get all matching results
    results = cur.fetchall()

    # Add values to external values to return results
    for auction in results:
        # If this is an auction
        if auction["auction_id"]:
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
        "results.html",
        title="Search Results",
        query=query,
        results=results,
    )

# Function for viewing an Auction (bidding)
@app.route("/bid/<int:auction_id>")
def view_auction(auction_id):
    # Make sure user is logged in
    if "login" not in session:
        return redirect("/login")

    # Get database information (connection)
    conn = get_db()
    # Grab cursor (selector)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Get auction info for this auction
    cur.execute("""
        SELECT A.*, I.*
        FROM auction A
        JOIN item I ON A.item_id = I.item_id
        WHERE A.auction_id = %s;
    """, (auction_id,))
    auction = cur.fetchone()

    # Execute query for all bidding information
    cur.execute("""
        SELECT *
        FROM bid
        WHERE auction_id = %s
        ORDER BY bid_timestamp DESC;
    """, (auction_id,))
    bids = cur.fetchall()

    # Execute query for highest bidder
    cur.execute("""
        SELECT *
        FROM bid
        WHERE auction_id = %s
        ORDER BY bid_amount DESC
        LIMIT 1;
    """, (auction_id,))
    highest_bid = cur.fetchone()

    # Add values to external values to return results
    auction["high_threshold"] = auction["starting_price"] * Decimal("1.3")

    # Format timestamp
    start_dt = auction["start_time"]
    end_dt = auction["end_time"]

    readable_start = start_dt.strftime("%b %d, %Y at %I:%M %p")
    readable_end = end_dt.strftime("%b %d, %Y at %I:%M %p")

    # Get readable timestamp
    if highest_bid is None:
        readable_timestamp = None
    else:
        readable_timestamp = highest_bid["bid_timestamp"].strftime("%b %d, %Y at %I:%M %p")

    if highest_bid is not None:
        highest_bid["readable_timestamp"] = readable_timestamp

    for bid in bids:
        if bid is not None:
            readable_ts = bid["bid_timestamp"].strftime("%m/%d/%Y at %I:%M %p")
            bid["readable_timestamp"] = readable_ts

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

    error = request.args.get("error")
    return render_template(
        "bid.html", 
        auction=auction, 
        bids=bids, 
        highest_bid=highest_bid, 
        error=error, 
        return_url=request.referrer,
        viewer_role=session["role"],
    )

# Function for adding a bid
@app.route("/add_bid", methods=["POST"])
def add_bid():
    if "login" not in session:
        return redirect("/login")

    if session["role"] != "Buyer":
        error = "Only Buyers are allowed to place bids."
        return redirect(url_for("view_auction", auction_id=auction_id, error=error))

    bid_amount = Decimal(request.form["bid"])
    auction_id = request.form["auction_id"]
    bidder = session["login"]

    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Get highest bid
    cur.execute("""
        SELECT bid_amount
        FROM bid
        WHERE auction_id = %s
        ORDER BY bid_amount DESC
        LIMIT 1;
    """, (auction_id,))
    highest = cur.fetchone()

    # Validate bid
    if highest and bid_amount <= highest["bid_amount"]:
        error = "Your bid must be higher than the current highest bid."
        return redirect(url_for("view_auction", auction_id=auction_id, error=error))

    if bid_amount <= 0:
        error = "Bids must be greater than 0."
        return redirect(url_for("view_auction", auction_id=auction_id, error=error))

    # Insert bid
    try:
        # Get the next bid_id in sequence
        cur.execute("SELECT nextval('bid_id_seq') AS next_id;")
        next_bid_id = cur.fetchone()["next_id"]

        # Try to insert query
        cur.execute("""
            INSERT INTO bid (bid_id, auction_id, buyer_login, buyer_role, bid_amount)
            VALUES (%s, %s, %s, 'Buyer', %s);
        """, (next_bid_id, auction_id, bidder, bid_amount))

        # Update Auction Highest Bid
        cur.execute("""
            UPDATE auction
            SET current_highest_bid = %s
            WHERE auction_id = %s;
        """, (bid_amount, auction_id))

        conn.commit()
    except Exception as e:
        conn.rollback()
        error = "Must be a Buyer to bid on auctions."
        return redirect(url_for("view_auction", auction_id=auction_id, error=error))

    return redirect(f"/bid/{auction_id}")

# Run app locally
if __name__ == "__main__":
    app.run(debug=True, port=5001)