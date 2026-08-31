"""
Task 3: Cloud-Based Bus Pass System
----------------------------------------------------------------
An online ticket booking system hosted on a cloud database that:
1. Lets users view available bus seats
2. Books a ticket with a unique, server-generated ticket ID
3. Prevents ticket theft/loss by making the server (not the user)
   decide the price and generate the ticket ID
4. Prevents double-booking of the same seat (handles "high traffic"
   safely using a database-level UNIQUE constraint)
5. Lets users verify/view their booked ticket

SETUP:
1. pip install flask psycopg2-binary
2. Update DB_CONFIG below with your Supabase connection string
3. Run this script
"""

from flask import Flask, request, jsonify
import psycopg2
import uuid

app = Flask(__name__)

# -------------------------------------------------
# 1. CLOUD DATABASE CONNECTION
# -------------------------------------------------
DB_CONFIG = {
    "dsn": "postgresql://postgres.YOUR_PROJECT_ID:postgres@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres"
}

def get_connection():
    return psycopg2.connect(DB_CONFIG["dsn"])


# -------------------------------------------------
# 2. FIXED SERVER-SIDE PRICING (user can never fake this)
# -------------------------------------------------
# Real system: price could depend on route/distance. Kept simple here.
TICKET_PRICE = 50  # in rupees, decided ONLY by the server


# -------------------------------------------------
# 3. CREATE TABLES (run once)
# -------------------------------------------------
def setup_tables():
    conn = get_connection()
    cur = conn.cursor()

    # Bus seats available for booking
    cur.execute("""
        CREATE TABLE IF NOT EXISTS bus_seats (
            seat_number INT PRIMARY KEY,
            route TEXT NOT NULL,
            is_booked BOOLEAN DEFAULT FALSE
        );
    """)

    # Tickets issued to passengers
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            ticket_id TEXT PRIMARY KEY,
            passenger_name TEXT NOT NULL,
            seat_number INT UNIQUE REFERENCES bus_seats(seat_number),
            price INT NOT NULL,
            booked_at TIMESTAMP DEFAULT NOW()
        );
    """)

    # Pre-fill 10 seats on one route, only if table is empty
    cur.execute("SELECT COUNT(*) FROM bus_seats;")
    count = cur.fetchone()[0]
    if count == 0:
        for seat in range(1, 11):
            cur.execute(
                "INSERT INTO bus_seats (seat_number, route) VALUES (%s, %s)",
                (seat, "Hyderabad - Vijayawada")
            )

    conn.commit()
    cur.close()
    conn.close()
    print("Tables ready with 10 seats loaded.")


# -------------------------------------------------
# 4. VIEW AVAILABLE SEATS
# -------------------------------------------------
@app.route("/seats", methods=["GET"])
def view_seats():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT seat_number, route, is_booked FROM bus_seats ORDER BY seat_number;")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    seats = [
        {"seat_number": r[0], "route": r[1], "is_booked": r[2]}
        for r in rows
    ]
    return jsonify(seats)


# -------------------------------------------------
# 5. BOOK A TICKET (prevents double-booking + fake pricing)
# -------------------------------------------------
@app.route("/book", methods=["POST"])
def book_ticket():
    data = request.get_json()
    passenger_name = data.get("passenger_name")
    seat_number = data.get("seat_number")

    if not passenger_name or not seat_number:
        return jsonify({"error": "passenger_name and seat_number are required"}), 400

    conn = get_connection()
    cur = conn.cursor()

    # Check seat exists and is not already booked
    cur.execute("SELECT is_booked FROM bus_seats WHERE seat_number = %s;", (seat_number,))
    row = cur.fetchone()

    if row is None:
        cur.close()
        conn.close()
        return jsonify({"error": "Seat does not exist"}), 404

    if row[0] is True:
        cur.close()
        conn.close()
        return jsonify({"error": "Seat already booked. Choose another seat."}), 409

    # Generate a unique, unguessable ticket ID (prevents ticket theft/duplication)
    ticket_id = str(uuid.uuid4())

    try:
        # Mark seat as booked
        cur.execute("UPDATE bus_seats SET is_booked = TRUE WHERE seat_number = %s;", (seat_number,))

        # Insert ticket. Price comes from the SERVER constant, never from user input
        cur.execute(
            "INSERT INTO tickets (ticket_id, passenger_name, seat_number, price) VALUES (%s, %s, %s, %s)",
            (ticket_id, passenger_name, seat_number, TICKET_PRICE)
        )
        conn.commit()
        return jsonify({
            "message": "Ticket booked successfully",
            "ticket_id": ticket_id,
            "seat_number": seat_number,
            "price": TICKET_PRICE
        }), 201

    except psycopg2.errors.UniqueViolation:
        # This triggers if two people try to book the same seat at the EXACT same time
        conn.rollback()
        return jsonify({"error": "Seat was just booked by someone else. Try another seat."}), 409

    finally:
        cur.close()
        conn.close()


# -------------------------------------------------
# 6. VERIFY / VIEW A TICKET (prevents ticket loss - can always look it up)
# -------------------------------------------------
@app.route("/ticket/<ticket_id>", methods=["GET"])
def view_ticket(ticket_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT ticket_id, passenger_name, seat_number, price, booked_at FROM tickets WHERE ticket_id = %s;",
        (ticket_id,)
    )
    row = cur.fetchone()
    cur.close()
    conn.close()

    if row is None:
        return jsonify({"error": "Ticket not found"}), 404

    return jsonify({
        "ticket_id": row[0],
        "passenger_name": row[1],
        "seat_number": row[2],
        "price": row[3],
        "booked_at": str(row[4])
    })


# -------------------------------------------------
# 7. RUN THE SERVER
# -------------------------------------------------
if __name__ == "__main__":
    setup_tables()
    app.run(host="0.0.0.0", port=5000, debug=True)
