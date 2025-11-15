from flask import Flask, request, jsonify, render_template, redirect, url_for, session
import json
import os
from datetime import date, datetime, timedelta, time
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
LANDMARKS_FILE = os.path.join(DATA_DIR, "landmarks.json")

# Time slot constants
OPENING_TIME = time(17, 0)
LAST_START_TIME = time(21, 0)
SLOT_MINUTES = 30
BOOKING_DURATION_MINUTES = 150  # 2.5 hours default

# Table combination rules for multi-table bookings
# Used for AI/auto-assign and manual table combining
TABLE_COMBINATIONS = [
    [2, 3],          # Tables 2+3
    [1, 2, 3],       # Tables 1+2+3
    [1, 2, 3, 4],    # Tables 1+2+3+4
    [2, 3, 4],       # Tables 2+3+4
    [8, 9],          # Tables 8+9
    [13, 14],        # Tables 13+14
]

# super simple user store for now
USERS = {
    "admin": "password123",
    "host": "host123",
    "lars": "larspistasj69"
}

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-me-in-prod")  # needed for sessions

# Ensure browsers that request /favicon.ico get redirected to the PNG favicon
@app.route('/favicon.ico')
def favicon_redirect():
    return redirect(url_for('static', filename='favicon.png', v=5))

@app.context_processor
def inject_booking_dates():
    """Make today and max_booking_date available to all templates."""
    today = date.today()
    max_booking_date = today + timedelta(days=60)
    return {
        "today": today,
        "max_booking_date": max_booking_date
    }

def load_tables() -> list[dict]:
    """Load tables from tables.json and normalise basic fields.

    - Always returns a list (possibly empty).
    - Sets default flags for bookable / is_landmark.
    - Ensures width/height have sensible defaults.
    """
    try:
        with open(TABLES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return []

    if not isinstance(data, list):
        return []

    for t in data:
        if not isinstance(t, dict):
            continue
        t.setdefault("bookable", True)
        t.setdefault("is_landmark", False)
        t.setdefault("width", 64)
        t.setdefault("height", 64)

    return data

def save_tables(tables):
    """Save tables list to tables.json"""
    with open(TABLES_FILE, "w", encoding="utf-8") as f:
        json.dump(tables, f, indent=2)

def ensure_default_tables():
    """
    If tables.json is missing or empty, write a default layout
    with 14 tables including capacity, shape, and party size rules.
    """
    # If file exists and has at least one table, do nothing
    if TABLES_FILE.exists():
        try:
            with open(TABLES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list) and len(data) > 0:
                return
        except Exception:
            # fall through and re-create file
            pass

    print("⚠️ No tables.json found or file empty. Creating default tables layout (1-14) in", TABLES_FILE)

    default_tables = [
        # Tables 1-9: Square 2-tops for 1-2 people
        {"id": 1, "name": "1", "seats": 2, "capacity": 2, "shape": "square",
         "min_party_size": 1, "max_party_size": 2, "section": "Main",
         "x": 50, "y": 50, "width": 60, "height": 60},
        {"id": 2, "name": "2", "seats": 2, "capacity": 2, "shape": "square",
         "min_party_size": 1, "max_party_size": 2, "section": "Main",
         "x": 150, "y": 50, "width": 60, "height": 60},
        {"id": 3, "name": "3", "seats": 2, "capacity": 2, "shape": "square",
         "min_party_size": 1, "max_party_size": 2, "section": "Main",
         "x": 250, "y": 50, "width": 60, "height": 60},
        {"id": 4, "name": "4", "seats": 2, "capacity": 2, "shape": "square",
         "min_party_size": 1, "max_party_size": 2, "section": "Main",
         "x": 350, "y": 50, "width": 60, "height": 60},
        {"id": 5, "name": "5", "seats": 2, "capacity": 2, "shape": "square",
         "min_party_size": 1, "max_party_size": 2, "section": "Main",
         "x": 50, "y": 150, "width": 60, "height": 60},
        {"id": 6, "name": "6", "seats": 2, "capacity": 2, "shape": "square",
         "min_party_size": 1, "max_party_size": 2, "section": "Main",
         "x": 150, "y": 150, "width": 60, "height": 60},
        {"id": 7, "name": "7", "seats": 2, "capacity": 2, "shape": "square",
         "min_party_size": 1, "max_party_size": 2, "section": "Main",
         "x": 250, "y": 150, "width": 60, "height": 60},
        {"id": 8, "name": "8", "seats": 2, "capacity": 2, "shape": "square",
         "min_party_size": 1, "max_party_size": 2, "section": "Main",
         "x": 350, "y": 150, "width": 60, "height": 60},
        {"id": 9, "name": "9", "seats": 2, "capacity": 2, "shape": "square",
         "min_party_size": 1, "max_party_size": 2, "section": "Main",
         "x": 50, "y": 250, "width": 60, "height": 60},
        
        # Table 10: Large round table for 3-4 people
        {"id": 10, "name": "10", "seats": 4, "capacity": 4, "shape": "round",
         "min_party_size": 3, "max_party_size": 4, "section": "Main",
         "x": 200, "y": 250, "width": 80, "height": 80},
        
        # Table 11: Large round table for 3-5 people
        {"id": 11, "name": "11", "seats": 5, "capacity": 5, "shape": "round",
         "min_party_size": 3, "max_party_size": 5, "section": "Main",
         "x": 320, "y": 250, "width": 90, "height": 90},
        
        # Tables 12-14: Round 2-tops for 1-2 people
        {"id": 12, "name": "12", "seats": 2, "capacity": 2, "shape": "round",
         "min_party_size": 1, "max_party_size": 2, "section": "Main",
         "x": 150, "y": 350, "width": 60, "height": 60},
        {"id": 13, "name": "13", "seats": 2, "capacity": 2, "shape": "round",
         "min_party_size": 1, "max_party_size": 2, "section": "Main",
         "x": 250, "y": 350, "width": 60, "height": 60},
        {"id": 14, "name": "14", "seats": 2, "capacity": 2, "shape": "round",
         "min_party_size": 1, "max_party_size": 2, "section": "Main",
         "x": 350, "y": 350, "width": 60, "height": 60},
    ]

    with open(TABLES_FILE, "w", encoding="utf-8") as f:
        json.dump(default_tables, f, indent=2)

def _default_landmarks() -> dict:
    """Fallback positions + sizes for landmarks."""
    return {
        "entrance": {
            "x": 120,
            "y": 80,
            "width": 140,
            "height": 50,
            "label": "Entrance",
        },
        "bar": {
            "x": 520,
            "y": 180,
            "width": 200,
            "height": 70,
            "label": "Bar",
        },
        "wc": {
            "x": 820,
            "y": 300,
            "width": 120,
            "height": 60,
            "label": "WC",
        },
    }


def load_landmarks() -> dict:
    """
    Load landmarks.json and normalise format.

    - New format: dict keyed by id ("entrance", "bar", "wc") with
      {x, y, width, height, label}.
    - Old format (e.g. list of objects) is auto-migrated to the new one.
    """
    if not os.path.exists(LANDMARKS_FILE):
        return _default_landmarks()

    try:
        with open(LANDMARKS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return _default_landmarks()

    # Already in the new dict format
    if isinstance(data, dict):
        for key, lm in list(data.items()):
            if not isinstance(lm, dict):
                data.pop(key)
                continue

            # Normalise keys
            if key not in ("entrance", "bar", "wc"):
                # Try to infer from label/type if someone renamed keys
                lm_type = (lm.get("type") or lm.get("label") or "").lower()
                if "entrance" in lm_type:
                    new_key = "entrance"
                elif "bar" in lm_type:
                    new_key = "bar"
                elif "wc" in lm_type or "toilet" in lm_type:
                    new_key = "wc"
                else:
                    # Unknown landmark; drop it for now
                    data.pop(key)
                    continue
                data[new_key] = lm
                if new_key != key:
                    data.pop(key, None)

        # Ensure required fields exist
        for key, lm in data.items():
            if key == "entrance":
                default_label = "Entrance"
            elif key == "bar":
                default_label = "Bar"
            else:
                default_label = "WC"

            lm.setdefault("label", default_label)
            lm.setdefault("x", 0)
            lm.setdefault("y", 0)
            lm.setdefault("width", 140 if key != "wc" else 120)
            lm.setdefault("height", 50 if key != "bar" else 70)

        return data

    # Old list-style format → migrate
    if isinstance(data, list):
        result = _default_landmarks()
        for lm in data:
            if not isinstance(lm, dict):
                continue

            lm_type = (lm.get("type") or lm.get("label") or "").lower()
            if "entrance" in lm_type:
                key = "entrance"
            elif "bar" in lm_type:
                key = "bar"
            elif "wc" in lm_type or "toilet" in lm_type:
                key = "wc"
            else:
                continue

            dest = result[key]
            dest["x"] = lm.get("x", dest["x"])
            dest["y"] = lm.get("y", dest["y"])
            dest["width"] = lm.get("width", dest["width"])
            dest["height"] = lm.get("height", dest["height"])
        return result

    # Anything weird → default
    return _default_landmarks()


def save_landmarks(landmarks: dict) -> None:
    """Persist landmarks to landmarks.json in the normalised dict format."""
    if not isinstance(landmarks, dict):
        return

    try:
        with open(LANDMARKS_FILE, "w", encoding="utf-8") as f:
            json.dump(landmarks, f, indent=2)
    except OSError:
        # Fail silently in production; you can log if you like
        pass


def load_constraints():
    if CONSTRAINTS_FILE.exists():
        with open(CONSTRAINTS_FILE, "r") as f:
            return json.load(f)
    return {}

def bookings_file_for_date(date_str):
    return DATA_DIR / f"bookings_{date_str}.json"

def normalize_booking_tables(booking):
    """Normalize booking data to ensure tables is always a list.
    
    - If 'tables' exists as a list, use it.
    - If 'tables' exists as a string, parse it as comma-separated ints.
    - Otherwise, migrate from 'table_id' to 'tables' list.
    - Maintains backward compatibility by keeping table_id as first table.
    
    Args:
        booking: Dictionary containing booking data
        
    Returns:
        The same booking dict with normalized 'tables' list
    """
    if "tables" in booking:
        # Already has tables field
        if isinstance(booking["tables"], str):
            # Parse comma-separated string
            booking["tables"] = [int(x.strip()) for x in booking["tables"].split(",") if x.strip()]
        elif not isinstance(booking["tables"], list):
            # Convert single value to list
            booking["tables"] = [int(booking["tables"])]
    else:
        # Migrate from table_id
        table_id = booking.get("table_id")
        if table_id is not None:
            booking["tables"] = [int(table_id)]
        else:
            booking["tables"] = []
    
    # Ensure all table IDs are integers
    booking["tables"] = [int(t) for t in booking["tables"]]
    
    # Maintain backward compatibility: set table_id to first table
    if booking["tables"]:
        booking["table_id"] = booking["tables"][0]
    
    return booking

def load_bookings_for_date(date_str):
    filename = bookings_file_for_date(date_str)
    if filename.exists():
        with open(filename, "r") as f:
            bookings = json.load(f)
            # Normalize all bookings to support multiple tables
            return [normalize_booking_tables(b) for b in bookings]
    return []

def save_bookings_for_date(date_str, bookings):
    filename = bookings_file_for_date(date_str)
    with open(filename, "w") as f:
        json.dump(bookings, f, indent=4)


def get_bookings_for_day(current_date: date):
    """Return list of bookings for a given date with normalized convenience fields.
    Existing JSON uses start_time/end_time (not ISO 'start'/'end'), so we adapt.
    Adds booking_index for template interactions (edit, drag & drop).
    """
    date_str = current_date.isoformat()
    raw = load_bookings_for_date(date_str)
    bookings_for_day = []
    for idx, b in enumerate(raw):
        b_copy = dict(b)
        # Ensure required derived fields
        b_copy["date"] = b_copy.get("date", date_str)
        b_copy["start_time"] = b_copy.get("start_time", "")
        b_copy["end_time"] = b_copy.get("end_time", "")
        b_copy["booking_index"] = idx
        bookings_for_day.append(b_copy)
    return bookings_for_day


# -------------------------
# Time slot helpers
# -------------------------
def generate_time_slots(day):
    """Generate all 30-minute time slots from 17:00 to 21:00 for the given date."""
    slots = []
    current = datetime.combine(day, OPENING_TIME)
    end = datetime.combine(day, LAST_START_TIME)
    
    while current <= end:
        slots.append(current)
        current += timedelta(minutes=SLOT_MINUTES)
    
    return slots


def overlaps(start1, end1, start2, end2):
    """Check if two time ranges overlap."""
    return start1 < end2 and start2 < end1


def slot_has_free_table(slot_start, guests, tables, bookings_for_day):
    """
    Check if there's at least one table free for the given slot and guest count.
    Returns True if a table is available, False otherwise.
    """
    slot_end = slot_start + timedelta(minutes=BOOKING_DURATION_MINUTES)
    
    # Filter tables that can accommodate the guests AND are bookable (exclude landmarks)
    suitable_tables = [
        t for t in tables 
        if t.get("seats", 0) >= guests and t.get("bookable", True)
    ]
    
    if not suitable_tables:
        return False
    
    # Check each suitable table
    for table in suitable_tables:
        table_id = table.get("id")
        table_is_free = True
        
        # Check all bookings for this table
        for booking in bookings_for_day:
            if booking.get("table_id") != table_id:
                continue
            
            # Parse booking times
            try:
                booking_start_str = booking.get("start_time", "")
                booking_end_str = booking.get("end_time", "")
                
                # Handle different time formats
                if "T" in booking_start_str:
                    # ISO datetime format
                    booking_start = datetime.fromisoformat(booking_start_str.replace("Z", "+00:00"))
                else:
                    # Time-only format - combine with date
                    booking_date = booking.get("date", slot_start.date().isoformat())
                    booking_start = datetime.fromisoformat(f"{booking_date}T{booking_start_str}")
                
                if "T" in booking_end_str:
                    booking_end = datetime.fromisoformat(booking_end_str.replace("Z", "+00:00"))
                else:
                    booking_date = booking.get("date", slot_start.date().isoformat())
                    booking_end = datetime.fromisoformat(f"{booking_date}T{booking_end_str}")
                
                # Check for overlap
                if overlaps(slot_start, slot_end, booking_start, booking_end):
                    table_is_free = False
                    break
                    
            except (ValueError, KeyError):
                # If we can't parse the booking time, assume it conflicts to be safe
                table_is_free = False
                break
        
        if table_is_free:
            return True
    
    return False


@app.route("/api/available-times")
def available_times():
    """
    Get available time slots for a given date and guest count.
    Query params: date (YYYY-MM-DD), guests (int)
    Returns: [{"time": "17:00", "available": true}, ...]
    """
    date_str = request.args.get("date")
    guests_str = request.args.get("guests")
    
    if not date_str or not guests_str:
        return jsonify({"error": "Missing date or guests parameter"}), 400
    
    try:
        selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        guests = int(guests_str)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid date or guests format"}), 400
    
    # Load tables and bookings
    ensure_default_tables()
    tables = load_tables()
    bookings = load_bookings_for_date(date_str)
    
    # Generate all time slots
    slots = generate_time_slots(selected_date)
    
    # Check availability for each slot
    result = []
    for slot in slots:
        available = slot_has_free_table(slot, guests, tables, bookings)
        result.append({
            "time": slot.strftime("%H:%M"),
            "available": available
        })
    
    return jsonify(result)


@app.route("/calendar")
def calendar():
    """Daily calendar grid view using shared booking helper."""
    if "user" not in session:
        return redirect(url_for("login"))

    # Parse ?date=YYYY-MM-DD or default to today
    date_str = request.args.get("date")
    if date_str:
        try:
            current_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            current_date = date.today()
    else:
        current_date = date.today()

    prev_date = current_date - timedelta(days=1)
    next_date = current_date + timedelta(days=1)

    # Unified loading
    tables = load_tables()
    # Filter to only bookable tables for calendar view (exclude landmarks)
    bookable_tables = [t for t in tables if t.get("bookable", True)]
    all_bookings = get_bookings_for_day(current_date)

    # Generate time slots from 17:00 to 23:30
    CLOSING_TIME = time(23, 30)
    time_slots = []
    dt = datetime.combine(current_date, OPENING_TIME)
    last_dt = datetime.combine(current_date, CLOSING_TIME)
    step = timedelta(minutes=SLOT_MINUTES)
    while dt <= last_dt:
        time_slots.append(dt)
        dt += step

    num_slots = len(time_slots)
    slot_length = timedelta(minutes=SLOT_MINUTES)
    first_slot_dt = time_slots[0]
    last_slot_end = time_slots[-1] + slot_length

    # Build bookings_by_table: table_id -> list of booking segments
    bookings_by_table = {}
    for t in bookable_tables:
        table_id = str(t["id"])
        bookings_by_table[table_id] = []

    for booking_index, b in enumerate(all_bookings):
        table_id = str(b.get("table_id", ""))
        if not table_id or table_id not in bookings_by_table:
            continue

        # Parse start and end times
        start_time_str = b.get("start_time", "")
        end_time_str = b.get("end_time", "")
        
        if not start_time_str or not end_time_str:
            continue

        try:
            # Parse times as HH:MM
            start_h, start_m = map(int, start_time_str.split(":"))
            end_h, end_m = map(int, end_time_str.split(":"))
            
            start_dt = datetime.combine(current_date, time(start_h, start_m))
            end_dt = datetime.combine(current_date, time(end_h, end_m))
        except (ValueError, AttributeError):
            continue

        # Skip if completely out of range
        if end_dt <= first_slot_dt or start_dt >= last_slot_end:
            continue

        # Calculate slot index and colspan
        clamped_start = max(start_dt, first_slot_dt)
        clamped_end = min(end_dt, last_slot_end)

        offset_minutes = (clamped_start - first_slot_dt).total_seconds() / 60
        slot_index = int(offset_minutes // SLOT_MINUTES)

        duration_minutes = (clamped_end - clamped_start).total_seconds() / 60
        colspan = max(1, int(round(duration_minutes / SLOT_MINUTES)))

        # Create label
        name = b.get("name", "Booking")
        party_size = b.get("party_size", 0)
        label = f'{name} ({party_size})'

        bookings_by_table[table_id].append({
            "slot_index": slot_index,
            "colspan": colspan,
            "label": label,
            "booking": b,
            "booking_index": booking_index,  # Add booking index for drag & drop and edit
            "name": name,
            "party_size": party_size,
            "start_time": start_time_str,
            "end_time": end_time_str,
            "notes": b.get("notes", ""),
        })

    # Sort segments by slot_index for each table
    for table_id in bookings_by_table:
        bookings_by_table[table_id].sort(key=lambda s: s["slot_index"])

    # Build row data for each table
    rows = []
    for table in bookable_tables:
        table_id = str(table["id"])
        segments = bookings_by_table.get(table_id, [])
        
        cells = []
        current_slot = 0
        
        for seg in segments:
            # Add empty cells before this booking
            if seg["slot_index"] > current_slot:
                gap = seg["slot_index"] - current_slot
                for i in range(gap):
                    cells.append({
                        "type": "empty",
                        "colspan": 1,
                        "slot_index": current_slot + i,
                    })
                current_slot = seg["slot_index"]
            
            # Add the booking cell
            cells.append({
                "type": "booking",
                "colspan": seg["colspan"],
                "label": seg["label"],
                "booking": seg["booking"],
                "booking_index": seg["booking_index"],
                "slot_index": seg["slot_index"],
                "name": seg["name"],
                "party_size": seg["party_size"],
                "start_time": seg["start_time"],
                "end_time": seg["end_time"],
                "notes": seg["notes"],
            })
            current_slot += seg["colspan"]
        
        # Fill remaining empty cells
        while current_slot < num_slots:
            cells.append({
                "type": "empty",
                "colspan": 1,
                "slot_index": current_slot,
            })
            current_slot += 1
        
        rows.append({
            "table": table,
            "cells": cells,
        })

    return render_template(
        "calendar.html",
        user=session["user"],
        active_page="calendar",
        current_date=current_date,
        prev_date=prev_date,
        next_date=next_date,
        time_slots=time_slots,
        rows=rows,
        tables=bookable_tables,  # Only pass bookable tables to template
    )


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
    ensure_default_tables()  # create defaults if missing
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
    # Accept both JSON API and HTML form submissions
    data = request.get_json(silent=True) or {}
    is_form = not data and request.form

    if is_form:
        # Form fields from modal
        date_str = request.form.get("date")
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        
        # Title-case both names
        first_name = first_name.title()
        last_name = last_name.title()
        
        # Combine into full name
        name = f"{first_name} {last_name}".strip()
        
        party_size = request.form.get("people")
        start_time = request.form.get("start_time")
        notes = request.form.get("notes", "").strip() or None

        # Basic validation
        if not (date_str and first_name and last_name and party_size and start_time):
            # For form posts, redirect back to index with minimal friction
            return redirect(url_for("index"))
        try:
            party_size = int(party_size)
        except (TypeError, ValueError):
            party_size = 0
        if party_size <= 0:
            return redirect(url_for("index"))
        duration_minutes = 150  # default duration for modal-based create (2.5 hours)
    else:
        # JSON API
        # Validate required fields
        required = ["date", "name", "party_size", "start_time"]
        missing = [r for r in required if r not in data]
        if missing:
            return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

        date_str = data["date"]
        name = data["name"].strip().title() if isinstance(data["name"], str) else data["name"]
        party_size = data["party_size"]
        start_time = data["start_time"]
        notes = data.get("notes", "").strip() or None
    
    # Validate booking date (must be today or future, max 2 months ahead)
    try:
        booking_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        if is_form:
            return redirect(url_for("index"))
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400
    
    today = date.today()
    max_date = today + timedelta(days=60)  # ~2 months
    
    if booking_date < today:
        if is_form:
            return redirect(url_for("index"))
        return jsonify({"error": "You cannot book in the past."}), 400
    
    if booking_date > max_date:
        if is_form:
            return redirect(url_for("index"))
        return jsonify({"error": "Bookings can only be made up to 2 months in advance."}), 400
    
    # Calculate duration
    if not is_form:
        if "duration_minutes" in data:
            duration_minutes = data["duration_minutes"]
        elif "end_time" in data and data["end_time"]:
            # Calculate duration from start_time and end_time
            start_mins = booking_app.time_to_minutes(start_time)
            end_mins = booking_app.time_to_minutes(data["end_time"])
            duration_minutes = end_mins - start_mins
            if duration_minutes <= 0:
                return jsonify({"error": "end_time must be after start_time"}), 400
        else:
            # Default: 2.5 hours (150 minutes) if no end_time or duration_minutes provided
            duration_minutes = 150
    
    # Load tables and bookings for the specified date
    booking_app.load_tables()
    booking_app.load_bookings(date_str)
    
    # Find an available table using app.py logic
    table = booking_app.find_available_table(party_size, start_time, duration_minutes)
    
    if table is None:
        return jsonify({
            "error": "No table available for this time and party size",
            "details": f"No table found for party of {party_size} at {start_time} for {duration_minutes} minutes. Try adjusting the time, party size, or update the table layout."
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
    
    # Add notes if provided
    if notes:
        new_booking["notes"] = notes
    
    # Load existing bookings and append the new one
    bookings = load_bookings_for_date(date_str)
    bookings.append(new_booking)
    save_bookings_for_date(date_str, bookings)
    
    if is_form:
        # On form submission, redirect back to the Bookings page
        return redirect(url_for("index"))
    else:
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


@app.route("/bookings/swap_tables", methods=["POST"])
def swap_booking_tables():
    """
    Swap table assignments between two bookings.
    Used by drag & drop in calendar view.
    
    Expected JSON:
    {
      "date": "YYYY-MM-DD",
      "booking_index_1": <int>,
      "booking_index_2": <int>
    }
    """
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON body"}), 400

    date_str = data.get("date")
    index1 = data.get("booking_index_1")
    index2 = data.get("booking_index_2")

    if date_str is None or index1 is None or index2 is None:
        return jsonify({"error": "date, booking_index_1, and booking_index_2 are required"}), 400

    try:
        bookings = load_bookings_for_date(date_str)
        
        if index1 >= len(bookings) or index2 >= len(bookings):
            return jsonify({"error": "One or both booking indices out of range"}), 404

        # Swap the table_ids
        bookings[index1]["table_id"], bookings[index2]["table_id"] = \
            bookings[index2]["table_id"], bookings[index1]["table_id"]

        save_bookings_for_date(date_str, bookings)

        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/bookings/move_to_table", methods=["POST"])
def move_booking_to_table():
    """
    Move a booking to a different table (keep time unchanged).
    Used by drag & drop in calendar view.
    
    Expected JSON:
    {
      "date": "YYYY-MM-DD",
      "booking_index": <int>,
      "new_table_id": <int or str>
    }
    """
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON body"}), 400

    date_str = data.get("date")
    booking_index = data.get("booking_index")
    new_table_id = data.get("new_table_id")

    if date_str is None or booking_index is None or new_table_id is None:
        return jsonify({"error": "date, booking_index, and new_table_id are required"}), 400

    try:
        bookings = load_bookings_for_date(date_str)
        
        if booking_index >= len(bookings):
            return jsonify({"error": "Booking index out of range"}), 404

        # Update table
        bookings[booking_index]["table_id"] = new_table_id

        save_bookings_for_date(date_str, bookings)

        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/bookings/<int:date_str>/<int:booking_index>/edit", methods=["GET", "POST"])
def edit_booking(date_str, booking_index):
    """Edit an existing booking identified by date and index position.
    
    Form fields:
    - name: Guest name
    - party_size: Number of guests
    - table_id: Table assignment
    - date: New date (YYYY-MM-DD)
    - start_time: New start time (HH:MM)
    - end_time: New end time (HH:MM)
    - notes: Optional notes
    """
    if "user" not in session:
        return redirect(url_for("login"))
    
    # Convert date_str integer to proper format (it comes as path param)
    original_date = str(date_str)
    if len(original_date) == 8:  # e.g., 20251113
        original_date = f"{original_date[:4]}-{original_date[4:6]}-{original_date[6:]}"
    
    # Load bookings for the original date
    bookings = load_bookings_for_date(original_date)
    
    if booking_index < 0 or booking_index >= len(bookings):
        return jsonify({"error": "Booking not found"}), 404
    
    booking = bookings[booking_index]
    
    if request.method == "GET":
        # Return booking data as JSON for modal prefill
        return jsonify({
            "name": booking.get("name", ""),
            "party_size": booking.get("party_size", 1),
            "tables": booking.get("tables", []),
            "table_id": booking.get("table_id", ""),  # For backward compatibility
            "date": booking.get("date", original_date),
            "start_time": booking.get("start_time", ""),
            "end_time": booking.get("end_time", ""),
            "notes": booking.get("notes", "")
        })

    # Read form fields
    name = request.form.get("name", "").strip()
    party_size_str = request.form.get("party_size", "0").strip()
    table_ids_list = request.form.getlist("table_ids")  # Get multiple table selections
    new_date_str = request.form.get("date", "").strip()
    start_time_str = request.form.get("start_time", "").strip()
    end_time_str = request.form.get("end_time", "").strip()
    notes = request.form.get("notes", "").strip()
    
    # Basic validation
    if not name or not new_date_str or not start_time_str or not end_time_str:
        return redirect(url_for("index", date=original_date))
    
    try:
        party_size = int(party_size_str)
    except ValueError:
        party_size = booking.get("party_size", 2)
    
    # Parse multiple table IDs
    tables = []
    for tid in table_ids_list:
        try:
            tables.append(int(tid))
        except ValueError:
            continue
    
    # Fall back to existing tables if none selected
    if not tables:
        tables = booking.get("tables", [])
    
    # Title case the name
    name = name.title()
    
    # Validate date is not in the past or too far in the future
    try:
        new_date = datetime.strptime(new_date_str, "%Y-%m-%d").date()
    except ValueError:
        return redirect(url_for("index", date=original_date))
    
    today = date.today()
    max_date = today + timedelta(days=60)
    
    if new_date < today:
        return redirect(url_for("index", date=original_date))
    if new_date > max_date:
        return redirect(url_for("index", date=original_date))
    
    # Update booking fields
    booking["name"] = name
    booking["party_size"] = party_size
    booking["tables"] = tables
    # Maintain backward compatibility: set table_id to first table
    if tables:
        booking["table_id"] = tables[0]
    booking["date"] = new_date_str
    booking["start_time"] = start_time_str
    booking["end_time"] = end_time_str
    if notes:
        booking["notes"] = notes
    elif "notes" in booking:
        del booking["notes"]
    
    # If date changed, move booking to new date file
    if new_date_str != original_date:
        # Remove from original date
        bookings.pop(booking_index)
        save_bookings_for_date(original_date, bookings)
        
        # Add to new date
        new_date_bookings = load_bookings_for_date(new_date_str)
        new_date_bookings.append(booking)
        save_bookings_for_date(new_date_str, new_date_bookings)
    else:
        # Same date, just save
        save_bookings_for_date(original_date, bookings)
    
    return redirect(url_for("index", date=new_date_str))


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

    # Determine current date from query parameter, default to today
    date_str = request.args.get("date")
    if date_str:
        try:
            current_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            current_date = date.today()
    else:
        current_date = date.today()

    prev_date = current_date - timedelta(days=1)
    next_date = current_date + timedelta(days=1)

    # Shared helper usage
    bookings_for_day = get_bookings_for_day(current_date)

    total_bookings = len(bookings_for_day)
    total_seats = sum(b.get("party_size", 0) for b in bookings_for_day)

    today = date.today()
    max_booking_date = today + timedelta(days=60)

    ensure_default_tables()
    tables = load_tables()

    return render_template(
        "index.html",
        user=session["user"],
        active_page="bookings",
        bookings=bookings_for_day,
        total_bookings=total_bookings,
        total_seats=total_seats,
        current_date=current_date,
        prev_date=prev_date,
        next_date=next_date,
        today=today,
        max_booking_date=max_booking_date,
        tables=tables,
    )

# ===== TABLES MANAGEMENT =====

@app.route("/tables/<int:table_id>", methods=["POST"])
def update_table(table_id):
    """
    Update basic table properties: name, capacity, section.
    Expects JSON body like:
    {
      "name": "10",
      "capacity": 4,
      "section": "Main"
    }
    """
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON body"}), 400

    tables = load_tables()
    table = next((t for t in tables if t["id"] == table_id), None)
    if table is None:
        return jsonify({"error": "Table not found"}), 404

    name = data.get("name")
    capacity = data.get("capacity")
    section = data.get("section")
    shape = data.get("shape")

    if isinstance(name, str) and name.strip():
        table["name"] = name.strip()

    try:
        if capacity is not None:
            capacity_int = int(capacity)
            if capacity_int > 0:
                table["capacity"] = capacity_int
                table["seats"] = capacity_int  # Keep seats in sync
    except (TypeError, ValueError):
        pass

    if isinstance(section, str) and section.strip():
        table["section"] = section.strip()

    if isinstance(shape, str) and shape.strip() in ("round", "square"):
        table["shape"] = shape.strip()

    save_tables(tables)

    return jsonify({"status": "ok", "table": table})

@app.route("/tables/<int:table_id>/edit", methods=["POST"])
def edit_table(table_id):
    """
    Update basic table properties: name, capacity, section.
    Expects form data (from the modal) not JSON.
    """
    if "user" not in session:
        return redirect(url_for("login"))
    
    tables = load_tables()
    table = next((t for t in tables if t["id"] == table_id), None)
    if table is None:
        return "Table not found", 404

    name = request.form.get("name", "").strip()
    capacity_str = request.form.get("capacity", "").strip()
    section = request.form.get("section", "").strip()
    shape = request.form.get("shape", "").strip()  # NEW

    if name:
        table["name"] = name

    try:
        if capacity_str:
            capacity = int(capacity_str)
            if capacity > 0:
                table["capacity"] = capacity
                table["seats"] = capacity  # Keep seats in sync
    except ValueError:
        pass

    if section:
        table["section"] = section

    # Accept only valid shapes
    if shape in ("round", "square"):
        table["shape"] = shape

    save_tables(tables)

    # redirect back to floorplan, same date if provided
    date_param = request.args.get("date")
    if date_param:
        return redirect(url_for("floorplan", date=date_param))
    return redirect(url_for("floorplan"))

# ===== FLOORPLAN =====

UPCOMING_MINUTES = 30

@app.route("/floorplan")
def floorplan():
    if "user" not in session:
        return redirect(url_for("login"))
    
    # Determine date (same as Bookings/Calendar)
    date_str = request.args.get("date")
    if date_str:
        try:
            current_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            current_date = date.today()
    else:
        current_date = date.today()
    
    prev_date = current_date - timedelta(days=1)
    next_date = current_date + timedelta(days=1)
    
    # Load tables, landmarks, and bookings
    ensure_default_tables()
    tables = load_tables()
    landmarks = load_landmarks()
    bookings_for_day = get_bookings_for_day(current_date)
    
    # Build table_status: table_id -> {"state": ..., "booking": ...}
    now = datetime.now()
    upcoming_threshold = now + timedelta(minutes=UPCOMING_MINUTES)
    
    # Start with all tables empty
    table_status = {t["id"]: {"state": "empty", "booking": None} for t in tables}
    
    # Group bookings by table
    by_table = {}
    for b in bookings_for_day:
        table_id = b.get("table_id")
        if table_id is None:
            continue
        
        # Parse times
        try:
            start_time_str = b.get("start_time", "")
            end_time_str = b.get("end_time", "")
            date_str_booking = b.get("date", current_date.isoformat())
            
            start_dt = datetime.fromisoformat(f"{date_str_booking}T{start_time_str}")
            end_dt = datetime.fromisoformat(f"{date_str_booking}T{end_time_str}")
            
            b_copy = dict(b)
            b_copy["start_dt"] = start_dt
            b_copy["end_dt"] = end_dt
            
            by_table.setdefault(table_id, []).append(b_copy)
        except (ValueError, TypeError):
            continue
    
    # Decide status for each table
    for table_id, blist in by_table.items():
        # Sort by start time
        blist.sort(key=lambda x: x["start_dt"])
        
        active = None
        upcoming = None
        
        for b in blist:
            if b["start_dt"] <= now < b["end_dt"]:
                active = b
                break
            if b["start_dt"] >= now and b["start_dt"] <= upcoming_threshold:
                if upcoming is None or b["start_dt"] < upcoming["start_dt"]:
                    upcoming = b
        
        if active:
            table_status[table_id] = {"state": "occupied", "booking": active}
        elif upcoming:
            table_status[table_id] = {"state": "upcoming", "booking": upcoming}
        # else keep "empty"
    
    return render_template(
        "floorplan.html",
        user=session["user"],
        active_page="floorplan",
        tables=tables,
        table_status=table_status,
        current_date=current_date,
        prev_date=prev_date,
        next_date=next_date,
        table_combinations=TABLE_COMBINATIONS,
        landmarks=landmarks,
    )

@app.route("/landmarks/positions", methods=["POST"])
def update_landmark_positions():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    payload = request.get_json(silent=True)
    if not payload or "landmarks" not in payload or not isinstance(payload["landmarks"], list):
        return jsonify({"error": "Invalid payload"}), 400
    
    # Load current tables
    tables = load_tables()
    if not tables:
        return jsonify({"error": "No tables found"}), 404
    
    # Create lookup for landmark updates
    updates = {lm.get("id"): lm for lm in payload["landmarks"] if isinstance(lm, dict) and lm.get("id")}
    if not updates:
        return jsonify({"error": "No updates"}), 400
    
    # Update landmark table positions
    changed = 0
    for table in tables:
        if table.get("id") in updates and table.get("is_landmark"):
            upd = updates[table["id"]]
            for field in ("x", "y", "width", "height"):
                if field in upd:
                    try:
                        table[field] = int(upd[field])
                    except Exception:
                        pass
            changed += 1
    
    # Save updated tables
    if changed:
        save_tables(tables)
    
    return jsonify({"success": True, "status": "ok", "updated": changed})

# Also add endpoint for the frontend's expected path
@app.route("/api/save_landmark_positions", methods=["POST"])
def api_save_landmark_positions():
    """Alternative endpoint for saving landmark positions"""
    return update_landmark_positions()

@app.route("/api/save_table_layout", methods=["POST"])
def save_table_layout():
    """Save positions, dimensions, and properties for ALL tables"""
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    payload = request.get_json(silent=True)
    if not payload or "tables" not in payload or not isinstance(payload["tables"], list):
        return jsonify({"error": "Invalid payload"}), 400
    
    # Load current tables
    tables = load_tables()
    if not tables:
        return jsonify({"error": "No tables found"}), 404
    
    # Create lookup for table updates
    updates = {t.get("id"): t for t in payload["tables"] if isinstance(t, dict) and t.get("id")}
    if not updates:
        return jsonify({"error": "No updates"}), 400
    
    # Update table positions, dimensions, and properties
    changed = 0
    for table in tables:
        table_id = table.get("id")
        if table_id in updates:
            upd = updates[table_id]
            
            # Update position and dimensions
            for field in ("x", "y", "width", "height"):
                if field in upd:
                    try:
                        table[field] = int(upd[field])
                    except Exception:
                        pass
            
            # Update table properties
            if "name" in upd:
                table["name"] = str(upd["name"])
            
            if "capacity" in upd:
                try:
                    capacity = int(upd["capacity"])
                    table["capacity"] = capacity
                    table["seats"] = capacity  # Keep seats in sync
                except Exception:
                    pass
            
            if "section" in upd:
                table["section"] = str(upd["section"])
            
            if "shape" in upd:
                table["shape"] = str(upd["shape"])
            
            if "bookable" in upd:
                table["bookable"] = bool(upd["bookable"])
            
            if "is_landmark" in upd:
                table["is_landmark"] = bool(upd["is_landmark"])
            
            changed += 1
    
    # Save updated tables
    if changed:
        save_tables(tables)
    
    return jsonify({"success": True, "updated": changed})

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5003, use_reloader=False)
