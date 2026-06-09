# Using Flask for Web Interface (GUI)

from flask import Flask, render_template, request, redirect, session, url_for
from database import get_db
from decimal import Decimal
from datetime import datetime   # Converting CSV timestamp into readable format

import random
import string                   # For generating randomized tracking number

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
        viewer_role=session["role"],
        viewer_login=session["login"]
    )

# Function for creating an Auction
@app.route("/create_auction", methods=["POST"])
def create_auction():
    if "login" not in session:
        return redirect("/login")

    seller_login = session["login"]
    seller_role = session["role"]

    # Gather form data
    item_id = request.form["item_id"]
    end_time_str = request.form["end_time"]

    # Only sellers can create auctions
    if seller_role != "Seller":
        return redirect(url_for("manage_items", item_id=item_id, message="", error="Only sellers can create auctions."))

    # Parse datetime-local formats
    end_time_str = request.form["end_time"]

    # Accept all date formats
    parsed = None
    formats = [
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
    ]

    for fmt in formats:
        try:
            parsed = datetime.strptime(end_time_str, fmt)
            break
        except ValueError:
            continue

    if parsed is None:
        return redirect(url_for("manage_items", item_id=item_id, message="", error="Invalid date format."))

    end_time = parsed

    # Validate time range
    now = datetime.now()
    if end_time <= now:
        return redirect(url_for("manage_items", item_id=item_id, message="", error="End time must be in the future."))

    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Ensure the item belongs to this seller
    cur.execute("""
        SELECT item_id
        FROM item
        WHERE item_id = %s AND seller_login = %s;
    """, (item_id, seller_login))
    owned = cur.fetchone()

    if not owned:
        return redirect(url_for("manage_items", item_id=item_id, message="", error="You do not own this item."))

    # Ensure the item does not already have an auction
    cur.execute("""
        SELECT auction_id
        FROM auction
        WHERE item_id = %s;
    """, (item_id,))
    existing = cur.fetchone()

    if existing:
        return redirect(url_for("manage_items", item_id=item_id, message="", error="This item already has an auction."))

    # Get next auction_id
    cur.execute("SELECT nextval('auction_id_seq') AS next_id;")
    next_auction_id = cur.fetchone()["next_id"]

    # Insert auction
    try:
        cur.execute("""
            INSERT INTO auction (
                auction_id, item_id, seller_login, seller_role, current_highest_bid, auction_status, end_time
            )
            VALUES (%s, %s, %s, 'Seller', 0, 'Active', %s);
        """, (next_auction_id, item_id, seller_login, end_time))

        conn.commit()

    except Exception as e:
        conn.rollback()
        return redirect(url_for("manage_items", item_id=item_id, message="", error="Failed to create auction."))

    return redirect(url_for("manage_items", item_id=item_id, message="Auction has been successfully published.", error=""))

# Function for removing an Auction
@app.route("/remove_auction", methods=["POST"])
def remove_auction():
    if "login" not in session:
        return redirect("/login")

    seller_login = session["login"]
    seller_role = session["role"]

    auction_id = request.form["auction_id"]
    item_id = request.form["item_id"]

    # Sellers or Admins can remove auctions
    if seller_role not in ("Seller", "Admin"):
        return redirect(url_for("manage_items", item_id=item_id,
                                error="Only sellers or admins can remove auctions."))

    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Ownership check for sellers
    if seller_role == "Seller":
        cur.execute("""
            SELECT auction_id
            FROM auction
            WHERE auction_id = %s AND seller_login = %s;
        """, (auction_id, seller_login))

        if cur.fetchone() is None:
            return redirect(url_for("manage_items", item_id=item_id, error="You do not own this auction."))

    # Admins skip ownership check entirely

    try:
        # Delete the auction
        cur.execute("""
            DELETE FROM auction
            WHERE auction_id = %s;
        """, (auction_id,))

        conn.commit()

    except Exception:
        conn.rollback()
        return redirect(url_for("manage_items", item_id=item_id, error="Failed to remove auction."))

    return redirect(url_for("manage_items", item_id=item_id, message="Auction removed successfully."))

# Function for updating an Auction
@app.route("/update_auction", methods=["POST"])
def update_auction():
    if "login" not in session:
        return redirect("/login")

    seller_login = session["login"]
    seller_role = session["role"]

    # Gather identifiers
    auction_id = request.form["auction_id"]
    item_id = request.form["item_id"]

    # Gather item fields
    item_name = request.form["item_name"]
    category = request.form["category"]
    item_condition = request.form["item_condition"] or None
    description = request.form["description"] or None
    image_url = request.form["image_url"] or None
    starting_price = request.form["starting_price"]

    # Gather auction field
    end_time_str = request.form["end_time"]

    # Parse datetime-local formats
    parsed = None
    formats = [
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
    ]

    for fmt in formats:
        try:
            parsed = datetime.strptime(end_time_str, fmt)
            break
        except ValueError:
            continue

    if parsed is None:
        return redirect(url_for(
            "view_auction",
            auction_id=auction_id,
            error="Invalid date format."
        ))

    end_time = parsed

    # Validate end time
    if end_time <= datetime.now():
        return redirect(url_for(
            "view_auction",
            auction_id=auction_id,
            error="End time must be in the future."
        ))

    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Ensure seller owns this item
    cur.execute("""
        SELECT item_id
        FROM item
        WHERE item_id = %s AND seller_login = %s;
    """, (item_id, seller_login))

    if cur.fetchone() is None:
        return redirect(url_for(
            "view_auction",
            auction_id=auction_id,
            error="You don't own this item."
        ))

    try:
        # Update item
        cur.execute("""
            UPDATE item
            SET item_name = %s,
                category = %s,
                starting_price = %s,
                image_url = %s,
                item_condition = %s,
                description = %s
            WHERE item_id = %s;
        """, (item_name, category, starting_price, image_url, item_condition, description, item_id))

        # Update auction
        cur.execute("""
            UPDATE auction
            SET end_time = %s
            WHERE auction_id = %s;
        """, (end_time, auction_id))

        conn.commit()

    except Exception as e:
        conn.rollback()
        return redirect(url_for(
            "view_auction",
            auction_id=auction_id,
            error="Failed to update Auction."
        ))

    return redirect(url_for(
        "view_auction",
        auction_id=auction_id,
        message="Auction updated successfully."
    ))

# Helper function for ending an Auction (allows manual and time to end an auction)
def end_auction_logic(auction_id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Get item_id and seller
    cur.execute("""
        SELECT item_id, seller_login
        FROM auction
        WHERE auction_id = %s;
    """, (auction_id,))
    auction = cur.fetchone()

    # No auction found
    if not auction:
        return False, "Auction not found."

    item_id = auction["item_id"]

    # Get highest bid
    cur.execute("""
        SELECT buyer_login, buyer_role, bid_amount
        FROM bid
        WHERE auction_id = %s
        ORDER BY bid_amount DESC
        LIMIT 1;
    """, (auction_id,))
    highest = cur.fetchone()

    try:
        if highest:
            # If there was at least one bid; close auction permanently
            cur.execute("""
                UPDATE auction
                SET auction_status = 'Closed',
                    winner_login = %s,
                    winner_role = %s,
                    end_time = NOW()
                WHERE auction_id = %s;
            """, (highest["buyer_login"], highest["buyer_role"], auction_id))

            # Create payment row
            cur.execute("""
                INSERT INTO payment (payment_id, auction_id, buyer_login, buyer_role, amount, payment_status)
                VALUES (nextval('payment_id_seq'), %s, %s, 'Buyer', %s, 'Pending');
            """, (auction_id, highest["buyer_login"], highest["bid_amount"]))

            conn.commit()
            return True, "Auction closed with a winner."

        else:
            # No bids, delete auction and allow item to be reauctioned
            cur.execute("DELETE FROM auction WHERE auction_id = %s;", (auction_id,))
            conn.commit()
            return True, "Auction ended with no bids and was removed."

    except Exception as e:
        conn.rollback()
        return False, "Failed to end auction."

# Function for ending an Auction
@app.route("/end_auction", methods=["POST"])
def end_auction():
    if "login" not in session:
        return redirect("/login")

    auction_id = request.form["auction_id"]
    item_id = request.form["item_id"]

    success, msg = end_auction_logic(auction_id)

    if success:
        # If auction was deleted, redirect to item page
        if "no bids" in msg:
            return redirect(url_for("manage_items", item_id=item_id, message=msg))
        else:
            return redirect(url_for("view_auction", auction_id=auction_id, message=msg))

    return redirect(url_for("view_auction", auction_id=auction_id, error=msg))

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

    # Search only for Items not auctioned
    cur.execute("""
        SELECT I.*
        FROM item I
        LEFT JOIN auction A ON I.item_id = A.item_id
        WHERE A.item_id IS NULL;
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
        viewer_role=session["role"],
        viewer_login=session["login"]
    )

# Function for calling Items (for a seller)
@app.route("/items_seller")
def items_seller():
    # Make sure user is logged in
    if "login" not in session:
        return redirect("/login")

    login = session["login"]
        
    # Get database information (connection)
    conn = get_db()
    # Grab cursor (selector)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Search for all items/auctions owned by this user
    # but remove the double item/auction if an item is in an auction
    cur.execute("""
        SELECT 
            I.*,
            A.auction_id,
            A.current_highest_bid,
            A.auction_status,
            A.start_time,
            A.end_time,
            A.winner_login,
            A.winner_role
        FROM item I
        LEFT JOIN auction A ON I.item_id = A.item_id
        WHERE I.seller_login = %s;
    """, (login,))

    # Get all matching results
    results = cur.fetchall()

    # Add missing high_threshold for auctions
    for row in results:
        if row["auction_id"]:
            row["high_threshold"] = row["starting_price"] * Decimal("1.3")

    # Close connection and cursor
    cur.close()
    conn.close()

    # Return results
    return render_template(
        "items.html",
        title="Your Items & Auctions",
        results=results,
        viewer_role=session["role"],
        viewer_login=session["login"]
    )

# Function for calling Items (for an admin)
@app.route("/items_admin")
def items_admin():
    # Make sure user is logged in
    if "login" not in session:
        return redirect("/login")

    login = session["login"]
        
    # Get database information (connection)
    conn = get_db()
    # Grab cursor (selector)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Search for all items/auctions owned by this user
    # but remove the double item/auction if an item is in an auction
    cur.execute("""
        SELECT 
            I.*,
            A.auction_id,
            A.current_highest_bid,
            A.auction_status,
            A.start_time,
            A.end_time,
            A.winner_login,
            A.winner_role
        FROM item I
        LEFT JOIN auction A ON I.item_id = A.item_id
    """)

    # Get all matching results
    results = cur.fetchall()

    # Add missing high_threshold for auctions
    for row in results:
        if row["auction_id"]:
            row["high_threshold"] = row["starting_price"] * Decimal("1.3")

    # Close connection and cursor
    cur.close()
    conn.close()

    # Return results
    return render_template(
        "items.html",
        title="All Items & Auctions",
        results=results,
        viewer_role=session["role"],
        viewer_login=session["login"]
    )

# Function for adding an Item
@app.route("/add_item", methods=["POST"])
def add_item():
    if "login" not in session:
        return redirect("/login")

    # Gather data
    item_name = request.form["item_name"]
    category = request.form["category"]
    starting_price = request.form["starting_price"]
    # If user filled out these field(s)
    image_url = request.form["image_url"] if request.form["image_url"] else None
    item_condition = request.form["item_condition"] if request.form["item_condition"] else None
    description = request.form["description"] if request.form["description"] else None
    login = session["login"]

    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Insert item
    # Get the next item_id in sequence
    cur.execute("SELECT nextval('item_id_seq') AS next_id;")
    next_item_id = cur.fetchone()["next_id"]

    # Try to insert query
    cur.execute("""
        INSERT INTO item (
            item_id, item_name, category, starting_price,
            image_url, item_condition, description,
            seller_login, seller_role
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'Seller');
    """, (next_item_id, item_name, category, starting_price,
        image_url, item_condition, description, login))

    conn.commit()

    return redirect("/items")

# Function for updating an Item
@app.route("/update_item", methods=["POST"])
def update_item():
    # Make sure user is logged in
    if "login" not in session:
        return redirect("/login")

    login = session["login"]
    item_id = request.form["item_id"]

    # Gather data
    item_name = request.form["item_name"]
    category = request.form["category"]
    starting_price = request.form["starting_price"]
    # If user filled out these field(s)
    image_url = request.form["image_url"] if request.form["image_url"] else None
    item_condition = request.form["item_condition"] if request.form["item_condition"] else None
    description = request.form["description"] if request.form["description"] else None

    conn = get_db()
    cur = conn.cursor()

    # Execute query for updating item information
    cur.execute("""
            UPDATE item
            SET item_name = %s,
                category = %s,
                starting_price = %s,
                image_url = %s,
                item_condition = %s,
                description = %s
            WHERE item_id = %s AND seller_login = %s;
        """, (item_name, category, starting_price, image_url,
            item_condition, description, item_id, login))

    conn.commit()

    return redirect(url_for(
        "manage_items",
        item_id=item_id,
        message="Your changes have been successfully saved."
    ))

# Function for removing an Item
@app.route("/remove_item", methods=["POST"])
def remove_item():
    if "login" not in session:
        return redirect("/login")

    seller_login = session["login"]
    seller_role = session["role"]

    item_id = request.form["item_id"]

    # Only sellers can remove items
    if seller_role not in ("Seller", "Admin"):
        return redirect(url_for("manage_items", item_id=item_id, error="Only sellers or admins can remove items."))

    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Execute query for this sellers item
    # Only enforce ownership for sellers, not admins
    if seller_role == "Seller":
        cur.execute("""
            SELECT item_id
            FROM item
            WHERE item_id = %s AND seller_login = %s;
        """, (item_id, seller_login))

        if cur.fetchone() is None:
            return redirect(url_for("manage_items", item_id=item_id, error="You do not own this item."))

    # Double-check: Item not in an auction
    cur.execute("""
        SELECT auction_id
        FROM auction
        WHERE item_id = %s;
    """, (item_id,))
    auction = cur.fetchone()

    if auction:
        return redirect(url_for("manage_items", item_id=item_id, error="Cannot remove an item that is in an auction."))

    # Delete the item
    try:
        cur.execute("DELETE FROM item WHERE item_id = %s;", (item_id,))
        conn.commit()

    except Exception:
        conn.rollback()
        return redirect(url_for("manage_items", item_id=item_id, error="Failed to remove item."))

    return redirect(url_for("items_seller", message="Item removed successfully."))

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

# Function for removing user
@app.route("/remove_user/<login>", methods=["POST"])
def remove_user(login):
    if "login" not in session or session["role"] != "Admin":
        return redirect("/")

    conn = get_db()
    cur = conn.cursor()

    # Check if user exists
    cur.execute("SELECT role FROM users WHERE login = %s;", (login,))
    row = cur.fetchone()

    if not row:
        return redirect(url_for("manageUsers", error="User does not exist.", message=""))

    role = row[0]

    # Check blocking dependencies
    # Seller dependencies
    if role == "Seller":
        cur.execute("SELECT 1 FROM item WHERE seller_login = %s;", (login,))
        if cur.fetchone():
            return redirect(url_for("manageUsers", error="Cannot delete seller with items.", message=""))

        cur.execute("SELECT 1 FROM auction WHERE seller_login = %s;", (login,))
        if cur.fetchone():
            return redirect(url_for("manageUsers", error="Cannot delete seller with auctions.", message=""))

    # Buyer dependencies
    if role == "Buyer":
        cur.execute("SELECT 1 FROM bid WHERE buyer_login = %s;", (login,))
        if cur.fetchone():
            return redirect(url_for("manageUsers", error="Cannot delete buyer with bids.", message=""))

        cur.execute("SELECT 1 FROM payment WHERE buyer_login = %s;", (login,))
        if cur.fetchone():
            return redirect(url_for("manageUsers", error="Cannot delete buyer with payments.", message=""))

    # If safe to delete, delete the user
    cur.execute("DELETE FROM users WHERE login = %s;", (login,))
    conn.commit()

    cur.close()
    conn.close()

    return redirect(url_for("manage_users", message="User removed successfully.", error=""))
    
# Function for calling Payments Page
@app.route("/payments")
def payments():
    if "login" not in session:
        return redirect("/login")

    buyer_login = session["login"]

    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Execute query to get all payments, auctions, and items for the session user
    cur.execute("""
        SELECT P.*, A.*, I.*
        FROM payment P
        JOIN auction A ON P.auction_id = A.auction_id
        JOIN item I ON A.item_id = I.item_id
        WHERE P.buyer_login = %s
        ORDER BY P.payment_id DESC;
    """, (buyer_login,))

    payments = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        "payments.html",
        results=payments,
        viewer_login=session["login"],
        viewer_role=session["role"]
    )

# Function for calling Payments Page
@app.route("/pay", methods=["POST"])
def pay():
    if "login" not in session:
        return redirect("/login")

    payment_id = request.form.get("payment_id")
    buyer_login = session["login"]

    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Update payment status and get auction_id
    cur.execute("""
        UPDATE payment
        SET payment_status = 'Completed'
        WHERE payment_id = %s AND buyer_login = %s
        RETURNING auction_id;
    """, (payment_id, buyer_login))

    row = cur.fetchone()

    # If payment doesn't exist
    if not row:
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for("payments"))

    auction_id = row["auction_id"]

    # Get buyer address
    cur.execute("""
        SELECT address
        FROM users
        WHERE login = %s;
    """, (buyer_login,))
    user_row = cur.fetchone()

    # Generate random tracking number
    tracking_number = "TRK-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))

    # Insert shipment using sequence
    cur.execute("""
        INSERT INTO shipment (shipment_id, auction_id, address, shipment_status, tracking_number)
        VALUES (nextval('shipment_id_seq'), %s, %s, 'Pending', %s);
    """, (auction_id, user_row["address"], tracking_number))

    conn.commit()
    cur.close()
    conn.close()

    return redirect(url_for("payments"))

# Function for calling Shipment Page
@app.route("/shipments")
def shipments():
    if "login" not in session:
        return redirect("/login")

    username = session["login"]

    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Grab shipment status for this user
    cur.execute("""
        SELECT S.*, A.*, I.*
        FROM shipment S
        JOIN auction A ON S.auction_id = A.auction_id
        JOIN item I ON A.item_id = I.item_id
        WHERE A.winner_login = %s
        ORDER BY S.shipment_id DESC;
    """, (username,))

    results = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        "shipment.html",
        title="View Shipments",
        results=results
    )

@app.route("/manage_items/<int:item_id>")
def manage_items(item_id):
    # Make sure user is logged in
    if "login" not in session:
        return redirect("/login")

    # Grab user
    username = session["login"]
    role = session["role"]

    # Get database information (connection)
    conn = get_db()
    # Grab cursor (selector)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # If Seller, they must own the item
    if role == "Seller":
        cur.execute("""
            SELECT I.*
            FROM item I
            WHERE I.item_id = %s AND I.seller_login = %s;
        """, (item_id, username))

    # If Admin, view any item
    else:
        cur.execute("""
            SELECT I.*
            FROM item I
            WHERE I.item_id = %s;
        """, (item_id,))

    item = cur.fetchone()

    message = request.args.get("message")
    error = request.args.get("error")

    return render_template(
        "manage_items.html",
        item=item,
        message=message,
        error=error
    )

    
# Function for calling ManageUsers Page
@app.route("/manage_users")
def manageUsers():
    if "login" not in session:
        return redirect("/login")

    # Only admins should access this page
    if session["role"] != "Admin":
        return redirect("/")

    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Grab all users
    cur.execute("""
        SELECT *
        FROM users
        ORDER BY login ASC;
    """)

    users = cur.fetchall()

    cur.close()
    conn.close()

    error = request.args.get("error")
    message = request.args.get("message")
    return render_template(
        "manage_users.html",
        title="Manage Users",
        results=users,
        viewer_login=session["login"],
        message=message,
        error=error
    )

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
        viewer_role=session["role"],
        viewer_login=session["login"]
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

    # Grab info
    seller_login = auction["seller_login"]
    item_id = auction["item_id"]

    # Automatically close expired auction
    if auction["auction_status"] == "Active" and auction["end_time"] <= datetime.now():
        success, msg = end_auction_logic(auction_id)

        # Re-fetch auction
        cur.execute("""
            SELECT A.*, I.*
            FROM auction A
            JOIN item I ON A.item_id = I.item_id
            WHERE A.auction_id = %s;
        """, (auction_id,))
        auction = cur.fetchone()

         # If auction ended with no bids, send sellers to manage_items and buyers to auction page
        if auction is None:
            if session["role"] == "Seller" and session["login"] == seller_login:
                return redirect(url_for("manage_items", item_id=item_id, message="Auction ended with no bids and was removed."))
            else:
                return redirect(url_for("auctions", message="That auction ended with no bids and was removed."))

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
        total_seconds = int(remaining.total_seconds())

        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600
        minutes = (total_seconds % 3600) // 60

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

    message = request.args.get("message")
    error = request.args.get("error")
    return render_template(
        "bid.html", 
        auction=auction, 
        bids=bids, 
        highest_bid=highest_bid, 
        message=message,
        error=error, 
        return_url=request.referrer,
        viewer_role=session["role"],
        viewer_login=session["login"]
    )

# Function for adding a bid
@app.route("/add_bid", methods=["POST"])
def add_bid():
    if "login" not in session:
        return redirect("/login")

    bid_amount = Decimal(request.form["bid"])
    auction_id = request.form["auction_id"]
    bidder = session["login"]

    if session["role"] != "Buyer":
        error = "Only Buyers are allowed to place bids."
        return redirect(url_for("view_auction", auction_id=auction_id, error=error))

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