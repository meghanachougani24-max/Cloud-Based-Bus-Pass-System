# Cloud-Based Bus Pass System

## What This Project Does
This is an online bus ticket booking system, built as a web API, that
lets passengers view available seats, book a ticket, and look up their
ticket at any time using a unique ticket ID.

## Problem It Solves
Traditional/manual booking systems often suffer from:
- **Ticket loss** — no reliable way to recover proof of a booking
- **Ticket theft / duplication** — the same seat being sold to multiple
  people
- **Incorrect pricing** — prices manipulated by whoever is entering the
  data
- **Poor handling of high demand** — many people trying to book at the
  same time, causing conflicts

This system solves each of these directly through its design.

## How It Works

### Preventing Ticket Loss
Every booked ticket is stored in the database with a unique `ticket_id`.
As long as a passenger has this ID, they can retrieve their full ticket
details at any time via the `/ticket/<id>` endpoint — the ticket is
never "lost" as long as the database exists.

### Preventing Ticket Theft / Duplication
Each ticket ID is generated using Python's `uuid` library, producing a
massive random 128-bit value. This makes it practically impossible for
anyone to guess or fake another person's ticket ID.
Additionally, the `seat_number` column in the `tickets` table has a
`UNIQUE` constraint tied to the seats table, so the database itself
physically refuses to let the same seat be booked twice — even if two
requests arrive at the exact same moment.

### Preventing Incorrect Pricing
The ticket price is a fixed value decided only by the server
(`TICKET_PRICE` constant in the code). The booking request from the
user never includes a price — it is impossible for a user to submit a
fake or discounted price, since the server ignores any such input and
always applies its own value.

### Handling High Traffic / Scalability
The system uses a real relational database with row-level uniqueness
constraints, meaning it correctly handles many simultaneous booking
attempts without corrupting data — if two people try to book the same
seat at the same time, the database guarantees only one succeeds
(`UniqueViolation` is caught and handled gracefully instead of crashing
or double-booking).

## Technology Used
- **Python + Flask** — lightweight web server / booking API
- **PostgreSQL** — relational database enforcing booking rules at the
  data layer (originally tested on Supabase's cloud database; also
  demonstrated running locally due to free-tier project limits)
- **psycopg2** — safe, parameterized database access
- **uuid** — for generating unguessable, unique ticket IDs

## API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/seats` | View all seats and their booking status |
| POST | `/book` | Book a ticket for a given seat |
| GET | `/ticket/<ticket_id>` | Look up a booked ticket by its ID |

## How to Run
1. Install dependencies:
   ```
   pip install flask psycopg2-binary
   ```
2. Update `DB_CONFIG` in `bus_system.py` with your database connection
   string (cloud or local PostgreSQL).
3. Run the server:
   ```
   python bus_system.py
   ```
4. The server will be live at `http://127.0.0.1:5000`

## How to Test

**View seats:**
```
curl http://127.0.0.1:5000/seats
```

**Book a ticket:**
```
curl -X POST http://127.0.0.1:5000/book -H "Content-Type: application/json" -d "{\"passenger_name\": \"Meghana\", \"seat_number\": 3}"
```
Result: returns a unique `ticket_id` and fixed price of ₹50.

**Attempt to double-book the same seat (should fail):**
```
curl -X POST http://127.0.0.1:5000/book -H "Content-Type: application/json" -d "{\"passenger_name\": \"Rahul\", \"seat_number\": 3}"
```
Result: `{"error": "Seat already booked. Choose another seat."}`

**Look up a ticket:**
```
curl http://127.0.0.1:5000/ticket/<ticket_id>
```
Result: returns full booking details, proving the ticket can always be
recovered.

## Result
- Seats cannot be double-booked, solving ticket theft/duplication.
- Prices cannot be faked, since they are decided entirely server-side.
- Tickets can always be retrieved via their unique ID, solving ticket
  loss.
- The system reliably handles concurrent booking attempts using
  database-level constraints, addressing the scalability and
  reliability goals of the task.
