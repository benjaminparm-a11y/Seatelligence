from flask import Flask, request, jsonify, render_template, redirect, url_for, session
import json
import os
from datetime import datetime
import math
import copy
from pathlib import Path

# Import availability logic from app.py
import app as booking_app

# Setup data directory paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)  # Create data directory if it doesn't exist

TABLES_FILE = DATA_DIR / "tables.json"
CONSTRAINTS_FILE = DATA_DIR / "restaurant_constraints.json"

# super simple user store for now
USERS = {
    "admin": "password123",
    "host": "host123"
}

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-me-in-prod")  # needed for sessions

def load_tables():
    if TABLES_FILE.exists():
        with open(TABLES_FILE, "r") as f:
            return json.load(f)
    return []

def load_constraints():
    if CONSTRAINTS_FILE.exists():
        with open(CONSTRAINTS_FILE, "r") as f:
            return json.load(f)
    return {}

def bookings_file_for_date(date_str):
    return DATA_DIR / f"bookings_{date_str}.json"

def load_bookings_for_date(date_str):
    filename = bookings_file_for_date(date_str)
    if filename.exists():
        with open(filename, "r") as f:
            return json.load(f)
    return []

def save_bookings_for_date(date_str, bookings):
    filename = bookings_file_for_date(date_str)
    with open(filename, "w") as f:
        json.dump(bookings, f, indent=4)


# -------------------------
# Layout helper functions
# -------------------------
def save_layout(tables):
    """Persist the given tables list to tables.json."""
    with open(TABLES_FILE, "w") as f:
        json.dump(tables, f, indent=4)


def _rects_overlap(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return not (ax + aw <= bx or bx + bw <= ax or ay + ah <= by or by + bh <= ay)


def validate_layout(tables, constraints):
    """Validate candidate layout against constraints and current table IDs.

    Checks:
    - Table IDs are unique and preserved (match current tables.json IDs)
    - Tables are inside room bounds
    - Tables do not overlap

    Returns: { valid: bool, errors: [str], warnings: [str] }
    """
    errors = []
    warnings = []

    # Basic structure
    if not isinstance(tables, list) or len(tables) == 0:
        return {"valid": False, "errors": ["Tables must be a non-empty list"], "warnings": []}

    # Room bounds
    room = (constraints or {}).get("room", {})
    room_w = float(room.get("width", 0))
    room_h = float(room.get("height", 0))

    # ID checks
    candidate_ids = []
    seen = set()
    rects = []
    for i, t in enumerate(tables):
        try:
            tid = int(t.get("id"))
            seats = int(t.get("seats", 0))
            x = float(t.get("x", 0))
            y = float(t.get("y", 0))
            w = float(t.get("width", 0))
            h = float(t.get("height", 0))
        except (TypeError, ValueError):
            errors.append(f"Table {i}: invalid field types")
            continue

        if tid in seen:
            errors.append(f"Duplicate table id {tid}")
        seen.add(tid)
        candidate_ids.append(tid)

        if seats <= 0 or w <= 0 or h <= 0:
            errors.append(f"Table {tid}: seats/width/height must be positive")

        # Bounds check (only if room dimensions are defined)
        if room_w > 0 and room_h > 0:
            if x < 0 or y < 0 or x + w > room_w or y + h > room_h:
                errors.append(f"Table {tid}: out of room bounds {room_w}x{room_h}")

        rects.append((x, y, w, h, tid))

    # Overlap checks
    for i in range(len(rects)):
        ax, ay, aw, ah, aid = rects[i]
        for j in range(i + 1, len(rects)):
            bx, by, bw, bh, bid = rects[j]
            if _rects_overlap((ax, ay, aw, ah), (bx, by, bw, bh)):
                errors.append(f"Tables {aid} and {bid} overlap")

    # ID preservation: compare with current tables.json ids
    current = load_tables() or []
    current_ids = sorted([int(t.get("id")) for t in current if "id" in t])
    cand_ids_sorted = sorted(candidate_ids)
    if current_ids and cand_ids_sorted != current_ids:
        errors.append("Table IDs changed; IDs must be preserved")

    return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}


def optimize_layout(bookings, tables, constraints):
    """Rule-based layout optimization with deterministic behavior.

    Goals:
    - If the largest party doesn't fit on any single table, bring two smaller
      tables close together near the center (side-by-side) to accommodate them,
      choosing the pair that minimizes wasted seats deterministically.
    - Maintain basic constraints: room bounds, minimum wall clearance, and try
      to maintain a minimum gap between all tables. Preserve table IDs.

    Returns a new list of tables (deep-copied and modified). If no action is
    needed, returns the original tables list unchanged.
    """
    if not tables:
        return tables

    # Determine if optimization is needed (oversized parties)
    max_table_seats = max((int(t.get("seats", 0)) for t in tables), default=0)
    max_party = max((int(b.get("party_size", 0)) for b in (bookings or [])), default=0)
    needs_pairing = max_party > max_table_seats

    # Constraints and defaults
    room = (constraints or {}).get("room", {})
    room_width = int(room.get("width", 800))
    room_height = int(room.get("height", 600))
    rules = (constraints or {}).get("layout_rules", {})
    min_gap = int(rules.get("min_gap_between_tables", 20))
    min_wall_clearance = int(rules.get("min_wall_clearance", 10))

    # Working copy of tables
    new_tables = copy.deepcopy(tables)

    # Helper: clamp within room bounds respecting wall clearance
    def clamp_to_room(x, y, w, h):
        x = max(min_wall_clearance, min(x, room_width - min_wall_clearance - w))
        y = max(min_wall_clearance, min(y, room_height - min_wall_clearance - h))
        return x, y

    # Center point
    cx, cy = room_width / 2.0, room_height / 2.0

    # If pairing is required, choose a deterministic best pair and place them near center
    if needs_pairing:
        # Build candidate pairs whose combined seats can accommodate the party
        # Prefer the pair with the smallest seats sum (less wasted seats), then
        # the shortest current distance to minimize movement, then by (id1,id2).
        def table_info(t):
            return (
                int(t.get("id")),
                float(t.get("x", 0.0)),
                float(t.get("y", 0.0)),
                float(t.get("width", 60.0)),
                float(t.get("height", 60.0)),
                int(t.get("seats", 0)),
            )

        infos = [table_info(t) for t in new_tables]

        def center_of(info):
            _id, x, y, w, h, _s = info
            return (x + w / 2.0, y + h / 2.0)

        def dist(a, b):
            ax, ay = center_of(a)
            bx, by = center_of(b)
            return math.hypot(ax - bx, ay - by)

        best_pair = None
        best_key = None
        for i in range(len(infos)):
            for j in range(i + 1, len(infos)):
                id1, x1, y1, w1, h1, s1 = infos[i]
                id2, x2, y2, w2, h2, s2 = infos[j]
                total = s1 + s2
                if total < max_party:
                    continue
                pair_dist = dist(infos[i], infos[j])
                key = (total, pair_dist, (min(id1, id2), max(id1, id2)))
                if best_key is None or key < best_key:
                    best_key = key
                    best_pair = (infos[i], infos[j])

        if best_pair is None:
            # No feasible pair; nothing we can do beyond keeping existing layout
            return tables

        # Try to place the pair side-by-side horizontally near center.
        (id1, x1, y1, w1, h1, s1), (id2, x2, y2, w2, h2, s2) = best_pair

        def place_pair_horiz():
            total_w = w1 + min_gap + w2
            total_h = max(h1, h2)
            px = cx - total_w / 2.0
            py = cy - total_h / 2.0
            # Clamp the pair as a block
            px = max(min_wall_clearance, min(px, room_width - min_wall_clearance - total_w))
            py = max(min_wall_clearance, min(py, room_height - min_wall_clearance - total_h))
            t1x = px
            t1y = py + (total_h - h1) / 2.0
            t2x = px + w1 + min_gap
            t2y = py + (total_h - h2) / 2.0
            return (int(round(t1x)), int(round(t1y))), (int(round(t2x)), int(round(t2y)))

        def place_pair_vert():
            total_w = max(w1, w2)
            total_h = h1 + min_gap + h2
            px = cx - total_w / 2.0
            py = cy - total_h / 2.0
            px = max(min_wall_clearance, min(px, room_width - min_wall_clearance - total_w))
            py = max(min_wall_clearance, min(py, room_height - min_wall_clearance - total_h))
            t1x = px + (total_w - w1) / 2.0
            t1y = py
            t2x = px + (total_w - w2) / 2.0
            t2y = py + h1 + min_gap
            return (int(round(t1x)), int(round(t1y))), (int(round(t2x)), int(round(t2y)))

        # Check if horizontal placement fits as a block, else try vertical
        can_horiz = (w1 + min_gap + w2 + 2 * min_wall_clearance) <= room_width
        can_vert = (h1 + min_gap + h2 + 2 * min_wall_clearance) <= room_height

        if can_horiz:
            (nx1, ny1), (nx2, ny2) = place_pair_horiz()
        elif can_vert:
            (nx1, ny1), (nx2, ny2) = place_pair_vert()
        else:
            # If neither orientation fits within bounds, keep layout unchanged
            return tables

        # Apply the new positions to the chosen pair, preserve others
        for t in new_tables:
            if int(t.get("id")) == id1:
                t["x"], t["y"] = nx1, ny1
            elif int(t.get("id")) == id2:
                t["x"], t["y"] = nx2, ny2

        # Idempotence guard: Only push other tables outward if they are still
        # relatively close to center (distance less than threshold). This
        # prevents cumulative drifting on repeated optimization calls.
        spread_step = max(10, min_gap // 2)
        distance_threshold = min(room_width, room_height) * 0.15  # 15% of smaller dimension
        for t in new_tables:
            tid = int(t.get("id"))
            if tid in (id1, id2):
                continue
            w = float(t.get("width", 60))
            h = float(t.get("height", 60))
            x = float(t.get("x", 0))
            y = float(t.get("y", 0))
            tcx = x + w / 2.0
            tcy = y + h / 2.0
            dist = math.hypot(tcx - cx, tcy - cy)
            if dist >= distance_threshold:
                continue  # already sufficiently outward
            dx = (tcx - cx)
            dy = (tcy - cy)
            if dist == 0:
                ux, uy = 1.0, 0.0
            else:
                ux, uy = dx / dist, dy / dist
            nx = x + ux * spread_step
            ny = y + uy * spread_step
            nx, ny = clamp_to_room(nx, ny, w, h)
            t["x"], t["y"] = int(round(nx)), int(round(ny))
    else:
        # No large party needing pairing; keep current layout unchanged
        return tables

    # 2) Light overlap resolution to try to maintain min_gap
    # We iterate a few times and separate pairs that are too close
    def rect_with_gap(table):
        x = float(table.get("x", 0))
        y = float(table.get("y", 0))
        w = float(table.get("width", 60))
        h = float(table.get("height", 60))
        half_gap = min_gap / 2.0
        return (x - half_gap, y - half_gap, x + w + half_gap, y + h + half_gap)

    for _ in range(4):  # a few relaxation iterations
        moved_any = False
        for i in range(len(new_tables)):
            for j in range(i + 1, len(new_tables)):
                ti = new_tables[i]
                tj = new_tables[j]
                x1, y1, w1, h1 = float(ti.get("x", 0)), float(ti.get("y", 0)), float(ti.get("width", 60)), float(ti.get("height", 60))
                x2, y2, w2, h2 = float(tj.get("x", 0)), float(tj.get("y", 0)), float(tj.get("width", 60)), float(tj.get("height", 60))
                # Expanded rectangles (include min_gap)
                l1, t1, r1, b1 = x1, y1, x1 + w1, y1 + h1
                l2, t2, r2, b2 = x2, y2, x2 + w2, y2 + h2
                # Overlap including gap requirement
                half_gap = min_gap / 2.0
                l1g, t1g, r1g, b1g = l1 - half_gap, t1 - half_gap, r1 + half_gap, b1 + half_gap
                l2g, t2g, r2g, b2g = l2 - half_gap, t2 - half_gap, r2 + half_gap, b2 + half_gap
                overlap_x = min(r1g, r2g) - max(l1g, l2g)
                overlap_y = min(b1g, b2g) - max(t1g, t2g)
                if overlap_x > 0 and overlap_y > 0:
                    # Push apart along the smaller overlap axis
                    if overlap_x < overlap_y:
                        push = overlap_x / 2.0
                        c1x = x1 + w1 / 2.0
                        c2x = x2 + w2 / 2.0
                        if c1x <= c2x:
                            x1n = x1 - push
                            x2n = x2 + push
                        else:
                            x1n = x1 + push
                            x2n = x2 - push
                        x1n, y1 = clamp_to_room(x1n, y1, w1, h1)
                        x2n, y2 = clamp_to_room(x2n, y2, w2, h2)
                        ti["x"], tj["x"] = int(round(x1n)), int(round(x2n))
                    else:
                        push = overlap_y / 2.0
                        c1y = y1 + h1 / 2.0
                        c2y = y2 + h2 / 2.0
                        if c1y <= c2y:
                            y1n = y1 - push
                            y2n = y2 + push
                        else:
                            y1n = y1 + push
                            y2n = y2 - push
                        x1, y1n = clamp_to_room(x1, y1n, w1, h1)
                        x2, y2n = clamp_to_room(x2, y2n, w2, h2)
                        ti["y"], tj["y"] = int(round(y1n)), int(round(y2n))
                    moved_any = True
        if not moved_any:
            break

    # 3) Nudge away from no-go zones if overlapping (best-effort)
    zones = (constraints or {}).get("no_go_zones", [])
    for t in new_tables:
        tx, ty, tw, th = float(t.get("x", 0)), float(t.get("y", 0)), float(t.get("width", 60)), float(t.get("height", 60))
        for z in zones:
            zx, zy = float(z.get("x", 0)), float(z.get("y", 0))
            zw, zh = float(z.get("width", 0)), float(z.get("height", 0))
            # Check overlap
            if not (tx + tw <= zx or tx >= zx + zw or ty + th <= zy or ty >= zy + zh):
                # Nudge out minimally towards nearest edge
                # Compute overlaps on each side
                left_overlap = (zx + zw) - tx if tx < zx + zw <= tx + tw else 0
                right_overlap = (tx + tw) - zx if zx < tx + tw <= zx + zw else 0
                top_overlap = (zy + zh) - ty if ty < zy + zh <= ty + th else 0
                bottom_overlap = (ty + th) - zy if zy < ty + th <= zy + zh else 0
                # Choose axis with greatest overlap
                candidates = [(left_overlap, 1, 0), (right_overlap, -1, 0), (top_overlap, 0, 1), (bottom_overlap, 0, -1)]
                # Default nudge
                dx, dy = 0.0, 0.0
                if any(val > 0 for val, _, _ in candidates):
                    val, sx, sy = max(candidates, key=lambda c: c[0])
                    dx = sx * (val + min_gap)
                    dy = sy * (val + min_gap)
                nx, ny = clamp_to_room(tx + dx, ty + dy, tw, th)
                t["x"], t["y"] = int(round(nx)), int(round(ny))

    return new_tables

@app.route("/tables", methods=["GET"])
def get_tables():
    tables = load_tables()
    return jsonify(tables)

@app.route("/bookings", methods=["GET"])
def get_bookings():
    date = request.args.get("date")
    if not date:
        return jsonify({"error": "date query param is required, e.g. ?date=2025-11-09"}), 400
    bookings = load_bookings_for_date(date)
    return jsonify(bookings)

@app.route("/bookings", methods=["POST"])
def create_booking():
    """
    Expects JSON like:
    {
        "date": "2025-11-09",
        "name": "Anna",
        "party_size": 4,
        "start_time": "19:00",
        "end_time": "21:00"
    }
    OR with duration_minutes instead of end_time:
    {
        "date": "2025-11-09",
        "name": "Anna",
        "party_size": 4,
        "start_time": "19:00",
        "duration_minutes": 120
    }
    
    Finds an available table automatically. Returns 400 if no table available.
    """
    data = request.get_json()
    
    # Validate required fields
    required = ["date", "name", "party_size", "start_time"]
    missing = [r for r in required if r not in data]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400
    
    date_str = data["date"]
    name = data["name"]
    party_size = data["party_size"]
    start_time = data["start_time"]
    
    # Calculate duration
    if "duration_minutes" in data:
        duration_minutes = data["duration_minutes"]
    elif "end_time" in data:
        # Calculate duration from start_time and end_time
        start_mins = booking_app.time_to_minutes(start_time)
        end_mins = booking_app.time_to_minutes(data["end_time"])
        duration_minutes = end_mins - start_mins
        if duration_minutes <= 0:
            return jsonify({"error": "end_time must be after start_time"}), 400
    else:
        return jsonify({"error": "Must provide either 'end_time' or 'duration_minutes'"}), 400
    
    # Load tables and bookings for the specified date
    booking_app.load_tables()
    booking_app.load_bookings(date_str)
    
    # Find an available table using app.py logic
    table = booking_app.find_available_table(party_size, start_time, duration_minutes)
    
    if table is None:
        return jsonify({
            "error": "No table available",
            "details": f"No table found for party of {party_size} at {start_time} for {duration_minutes} minutes"
        }), 400
    
    # Calculate end time
    start_mins = booking_app.time_to_minutes(start_time)
    end_mins = start_mins + duration_minutes
    end_time = booking_app.minutes_to_time(end_mins)
    
    # Create the booking object
    new_booking = {
        "name": name,
        "party_size": party_size,
        "date": date_str,
        "start_time": start_time,
        "end_time": end_time,
        "table_id": table["id"]
    }
    
    # Load existing bookings and append the new one
    bookings = load_bookings_for_date(date_str)
    bookings.append(new_booking)
    save_bookings_for_date(date_str, bookings)
    
    return jsonify({
        "status": "ok",
        "message": f"Booking created for {name}, party of {party_size}",
        "booking": new_booking,
        "table": {
            "id": table["id"],
            "seats": table["seats"]
        }
    }), 201

@app.route("/bookings", methods=["DELETE"])
def delete_booking():
    """Delete a booking by date and index.

    Accepts parameters via query string or JSON body:
      - date: YYYY-MM-DD
      - index: integer index within that day's bookings array
    Returns the updated list of bookings for that date on success.
    """
    # Read from query params first
    date_str = request.args.get("date")
    idx_val = request.args.get("index")

    # Also allow JSON body
    if request.is_json:
        payload = request.get_json(silent=True) or {}
        if not date_str:
            date_str = payload.get("date")
        if idx_val is None:
            idx_val = payload.get("index")

    if not date_str:
        return jsonify({"error": "Missing 'date' parameter"}), 400
    try:
        idx = int(idx_val)
    except (TypeError, ValueError):
        return jsonify({"error": "'index' must be an integer"}), 400

    # Load and validate bookings for the date
    bookings = load_bookings_for_date(date_str)
    if idx < 0 or idx >= len(bookings):
        return jsonify({"error": "Index out of range", "count": len(bookings)}), 400

    removed = bookings.pop(idx)
    save_bookings_for_date(date_str, bookings)

    return jsonify({
        "date": date_str,
        "removed": removed,
        "bookings": bookings
    }), 200

@app.route("/bookings", methods=["PUT"])
def update_booking():
    """Update an existing booking for a given date by index.

    Expected JSON body:
    {
      "date": "YYYY-MM-DD",
      "index": <int>,
      "name": <str>,
      "party_size": <int>,
      "start_time": "HH:MM",
      "end_time": "HH:MM"  // or provide duration_minutes instead
      // optional: table_id to request keeping the same table
    }
    Reuses availability/time-overlap checks similar to create.
    Returns updated list of bookings for that date on success.
    """
    data = request.get_json(silent=True) or {}
    required = ["date", "index", "name", "party_size", "start_time"]
    missing = [r for r in required if r not in data]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    date_str = data["date"]
    try:
        idx = int(data["index"])
    except (TypeError, ValueError):
        return jsonify({"error": "'index' must be an integer"}), 400
    name = data["name"]
    party_size = data["party_size"]
    start_time = data["start_time"]

    # Compute duration
    if "duration_minutes" in data:
        duration_minutes = int(data["duration_minutes"])  # may raise if invalid, fine
    elif "end_time" in data:
        start_mins = booking_app.time_to_minutes(start_time)
        end_mins = booking_app.time_to_minutes(data["end_time"])
        duration_minutes = end_mins - start_mins
        if duration_minutes <= 0:
            return jsonify({"error": "end_time must be after start_time"}), 400
    else:
        return jsonify({"error": "Must provide either 'end_time' or 'duration_minutes'"}), 400

    # Load context
    booking_app.load_tables()
    tables_list = booking_app.tables
    bookings_list = load_bookings_for_date(date_str)
    if idx < 0 or idx >= len(bookings_list):
        return jsonify({"error": "Index out of range", "count": len(bookings_list)}), 400

    # Prepare a working copy of bookings without the one being edited for availability checks
    working = [b for i, b in enumerate(bookings_list) if i != idx]

    # Helper to test availability of a specific table
    def is_table_available(table_id: int) -> bool:
        # capacity
        tbl = next((t for t in tables_list if t.get("id") == table_id), None)
        if not tbl or tbl.get("seats", 0) < party_size:
            return False
        s = booking_app.time_to_minutes(start_time)
        e = s + duration_minutes
        for b in working:
            if b.get("table_id") != table_id:
                continue
            bs = booking_app.time_to_minutes(b.get("start_time"))
            be = booking_app.time_to_minutes(b.get("end_time"))
            if booking_app.times_overlap(s, e, bs, be):
                return False
        return True

    # Determine target table
    requested_table_id = data.get("table_id")
    chosen_table = None
    if requested_table_id is not None:
        if is_table_available(int(requested_table_id)):
            chosen_table = next((t for t in tables_list if t.get("id") == int(requested_table_id)), None)
    else:
        # try to keep the same table if possible
        current_table_id = bookings_list[idx].get("table_id")
        if current_table_id is not None and is_table_available(int(current_table_id)):
            chosen_table = next((t for t in tables_list if t.get("id") == int(current_table_id)), None)

    # If no table chosen yet, find any available one
    if chosen_table is None:
        # temporarily set booking_app globals for reuse of find_available_table
        booking_app.bookings = working
        booking_app.tables = tables_list
        chosen_table = booking_app.find_available_table(party_size, start_time, duration_minutes)

    if chosen_table is None:
        return jsonify({
            "error": "No table available",
            "details": f"No table found for party of {party_size} at {start_time} for {duration_minutes} minutes"
        }), 400

    # Build updated booking
    new_start_mins = booking_app.time_to_minutes(start_time)
    new_end_mins = new_start_mins + duration_minutes
    end_time = booking_app.minutes_to_time(new_end_mins)

    updated = {
        "name": name,
        "party_size": party_size,
        "date": date_str,
        "start_time": start_time,
        "end_time": end_time,
        "table_id": chosen_table["id"],
    }

    # Save
    bookings_list[idx] = updated
    save_bookings_for_date(date_str, bookings_list)

    return jsonify({
        "date": date_str,
        "updated": updated,
        "bookings": bookings_list
    }), 200

@app.route("/optimize", methods=["POST"])
def optimize():
    """Optimize table layout for a given date.

    Request JSON: {"date": "YYYY-MM-DD"}
    Uses: selected date's bookings, current tables, restaurant_constraints.json
    Behavior: run optimize_layout(bookings, tables, constraints), validate and apply if changed.
    """
    payload = request.get_json(silent=True) or {}
    date_str = payload.get("date")
    if not date_str:
        return jsonify({"error": "Missing 'date' in JSON body"}), 400

    # Build layout request data
    try:
        tables = load_tables() or []
        bookings = load_bookings_for_date(date_str) or []
        constraints = load_constraints() or {}
    except Exception as e:
        return jsonify({"error": f"Failed to load inputs: {e}"}), 500

    # Execute optimization
    try:
        optimized_tables = optimize_layout(bookings, tables, constraints)
    except Exception as e:
        return jsonify({"error": f"Optimization error: {e}"}), 500

    # Validate optimization output type
    if not isinstance(optimized_tables, list):
        return jsonify({"error": "Optimization did not return a tables list"}), 500

    # Early exit if nothing changed
    def tables_positions(tlst):
        return sorted([(t.get('id'), t.get('x'), t.get('y')) for t in tlst])

    changed = tables_positions(optimized_tables) != tables_positions(tables)
    if not changed:
        return jsonify({
            "date": date_str,
            "optimized": False,
            "message": "No optimization needed",
            "tables": optimized_tables
        })

    # Validate with local helper and save if valid
    try:
        validation = validate_layout(optimized_tables, constraints)
    except Exception as e:
        return jsonify({"error": f"Validation error: {e}"}), 500

    if not validation.get("valid"):
        return jsonify({
            "date": date_str,
            "optimized": False,
            "message": "Layout validation failed",
            "errors": validation.get("errors", []),
            "warnings": validation.get("warnings", []),
        }), 400

    try:
        save_layout(optimized_tables)
    except Exception as e:
        return jsonify({"error": f"Failed to save layout: {e}"}), 500

    return jsonify({
        "date": date_str,
        "optimized": True,
        "message": "Optimization applied",
        "warnings": validation.get("warnings", []),
        "tables": optimized_tables
    })

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if username in USERS and USERS[username] == password:
            session["user"] = username
            return redirect(url_for("index"))
        else:
            return render_template("login.html", error="Invalid credentials")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))

@app.route("/healthz")
def healthz():
    return {"status": "ok"}, 200

@app.route("/theme-preview")
def theme_preview():
    return render_template("theme_preview.html")

@app.route("/")
def index():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("index.html", user=session["user"])

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5001, use_reloader=False)
