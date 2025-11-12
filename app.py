# ----------------------------
# TABLE SETUP (loaded from file)
# ----------------------------
import json
import os
from datetime import datetime, date

TABLES_FILE = "tables.json"
CONSTRAINTS_FILE = "restaurant_constraints.json"

tables = []
bookings = []
current_date = None  # Track which date we're viewing/editing
constraints = {}  # Restaurant layout constraints and rules


def load_constraints():
    """Load restaurant constraints from restaurant_constraints.json"""
    global constraints
    if os.path.exists(CONSTRAINTS_FILE):
        with open(CONSTRAINTS_FILE, "r") as f:
            constraints = json.load(f)
        room = constraints.get("room", {})
        print(f"📐 Loaded constraints: {room.get('name', 'Room')} ({room.get('width', 0)}x{room.get('height', 0)})")
    else:
        # Set default constraints
        constraints = {
            "room": {"width": 800, "height": 600, "name": "Main Dining Area"},
            "layout_rules": {
                "min_gap_between_tables": 20,
                "min_wall_clearance": 10,
                "max_tables": 20
            },
            "no_go_zones": [],
            "metadata": {"version": "1.0", "notes": "Default constraints"}
        }
        print("⚠️ No restaurant_constraints.json found. Using defaults.")


def save_constraints():
    """Save constraints back to restaurant_constraints.json"""
    with open(CONSTRAINTS_FILE, "w") as f:
        json.dump(constraints, f, indent=4)


def load_tables():
    """Load tables from tables.json"""
    global tables
    if os.path.exists(TABLES_FILE):
        with open(TABLES_FILE, "r") as f:
            tables = json.load(f)
    else:
        tables = []
        print("⚠️ No tables.json found. Currently no tables are defined.")


def save_tables():
    """Persist tables to tables.json"""
    with open(TABLES_FILE, "w") as f:
        json.dump(tables, f, indent=4)


def list_tables(show_index: bool = False):
    """Print the list of tables and their capacities."""
    if not tables:
        print("No tables defined.")
        return

    print("🍽️ Tables:")
    for i, t in enumerate(tables, start=1):
        name = t.get("name")
        label = f"Table {t['id']}" if name is None else f"Table {t['id']} – {name}"
        line = f"{label}: {t['seats']} seats"
        if show_index:
            print(f"{i}) {line}")
        else:
            print(f"- {line}")


def _next_table_id() -> int:
    """Generate the next numeric table id based on existing tables."""
    max_id = 0
    for t in tables:
        try:
            max_id = max(max_id, int(t.get("id", 0)))
        except (TypeError, ValueError):
            # Skip non-numeric ids
            continue
    return max_id + 1


def add_table():
    """Interactively add a new table to the system."""
    try:
        seats = int(input("Number of seats for the new table: "))
        if seats <= 0:
            print("Seats must be a positive number.")
            return
    except ValueError:
        print("Please enter a valid number for seats.")
        return

    name = input("Optional table name/label (press Enter to skip): ").strip()
    table_id = _next_table_id()

    # Create table with default layout position (can be updated later)
    table = {
        "id": table_id,
        "seats": seats,
        "x": 0,
        "y": 0,
        "width": 80,
        "height": 80
    }
    if name:
        table["name"] = name

    tables.append(table)
    save_tables()
    label = f"Table {table_id}" if not name else f"Table {table_id} – {name}"
    print(f"✅ Added {label} with {seats} seats.")


def edit_table():
    """Interactively edit a table's seat count."""
    if not tables:
        print("No tables to edit.")
        return
    
    list_tables(show_index=True)
    
    try:
        choice = int(input("Enter the number of the table to edit: "))
    except ValueError:
        print("Please enter a valid number.")
        return
    
    index = choice - 1
    if not (0 <= index < len(tables)):
        print("No table with that number.")
        return
    
    table = tables[index]
    print(f"Current seats for Table {table['id']}: {table['seats']}")
    
    try:
        new_seats = int(input("Enter new number of seats: "))
        if new_seats <= 0:
            print("Seats must be a positive number.")
            return
    except ValueError:
        print("Please enter a valid number for seats.")
        return
    
    table['seats'] = new_seats
    save_tables()
    print(f"✅ Updated Table {table['id']} to {new_seats} seats.")


def show_constraints():
    """Display the restaurant layout constraints and rules."""
    if not constraints:
        print("⚠️ No constraints loaded.")
        return
    
    print("\n📐 Restaurant Layout Constraints")
    print("=" * 60)
    
    # Room dimensions
    room = constraints.get("room", {})
    print(f"\n🏢 Room Information:")
    print(f"   Name: {room.get('name', 'N/A')}")
    print(f"   Dimensions: {room.get('width', 0)} x {room.get('height', 0)} pixels")
    
    # Layout rules
    rules = constraints.get("layout_rules", {})
    print(f"\n📏 Layout Rules:")
    print(f"   Minimum gap between tables: {rules.get('min_gap_between_tables', 0)} px")
    print(f"   Minimum wall clearance: {rules.get('min_wall_clearance', 0)} px")
    print(f"   Maximum tables allowed: {rules.get('max_tables', 0)}")
    
    # No-go zones
    no_go_zones = constraints.get("no_go_zones", [])
    print(f"\n🚫 No-Go Zones: {len(no_go_zones)}")
    if no_go_zones:
        for zone in no_go_zones:
            name = zone.get("name", "Unnamed")
            x, y = zone.get("x", 0), zone.get("y", 0)
            w, h = zone.get("width", 0), zone.get("height", 0)
            print(f"   • {name}: ({x}, {y}) - {w}x{h}")
    else:
        print("   (None defined)")
    
    # Metadata
    metadata = constraints.get("metadata", {})
    print(f"\n📋 Metadata:")
    print(f"   Version: {metadata.get('version', 'N/A')}")
    print(f"   Last updated: {metadata.get('last_updated', 'N/A')}")
    if metadata.get('notes'):
        print(f"   Notes: {metadata.get('notes')}")
    
    print("=" * 60)


# ----------------------------
# BOOKING FUNCTIONS
# ----------------------------
def get_bookings_filename(booking_date):
    """Get the filename for bookings on a specific date."""
    if isinstance(booking_date, str):
        # Already in YYYY-MM-DD format
        date_str = booking_date
    else:
        # datetime.date object
        date_str = booking_date.strftime("%Y-%m-%d")
    return f"bookings_{date_str}.json"


def load_bookings(booking_date=None):
    """Load bookings for a specific date."""
    global bookings, current_date
    
    if booking_date is None:
        booking_date = date.today()
    
    current_date = booking_date
    filename = get_bookings_filename(booking_date)
    
    if os.path.exists(filename):
        with open(filename, "r") as f:
            bookings = json.load(f)
    else:
        bookings = []


def save_bookings():
    """Save bookings to the current date's file."""
    if current_date is None:
        print("⚠️ No date set for bookings.")
        return
    
    filename = get_bookings_filename(current_date)
    with open(filename, "w") as f:
        json.dump(bookings, f, indent=4)


bookings = []  # each booking will have: name, party_size, start_time, end_time, table_id, date


# ----------------------------
# HELPER FUNCTIONS
# ----------------------------
def normalize_time(raw_time: str) -> str:
    """Turn user input into HH:MM format."""
    raw_time = raw_time.strip()

    # 4 digits -> HHMM
    if len(raw_time) == 4 and raw_time.isdigit():
        return raw_time[:2] + ":" + raw_time[2:]

    # already HH:MM
    if ":" in raw_time:
        return raw_time

    # just an hour like "7"
    if raw_time.isdigit():
        hour = int(raw_time)
        if 0 <= hour <= 23:
            return f"{hour:02d}:00"

    return raw_time


def time_to_minutes(hhmm: str) -> int:
    """'19:30' -> 1170 minutes since midnight."""
    parts = hhmm.split(":")
    hour = int(parts[0])
    minute = int(parts[1]) if len(parts) > 1 else 0
    return hour * 60 + minute


def minutes_to_time(minutes: int) -> str:
    """1170 -> '19:30'"""
    hour = minutes // 60
    minute = minutes % 60
    return f"{hour:02d}:{minute:02d}"


def times_overlap(start1, end1, start2, end2) -> bool:
    """
    Two time ranges overlap if they intersect at all.
    start/end are minutes from midnight.
    """
    return not (end1 <= start2 or end2 <= start1)


def find_available_table(party_size, start_time_str, duration_minutes):
    """Find a table that fits party_size and is free during the time window."""
    start_minutes = time_to_minutes(start_time_str)
    end_minutes = start_minutes + duration_minutes

    for table in tables:
        if table["seats"] < party_size:
            continue

        # check this table's existing bookings
        table_is_free = True
        for b in bookings:
            if b["table_id"] != table["id"]:
                continue

            existing_start = time_to_minutes(b["start_time"])
            existing_end = time_to_minutes(b["end_time"])

            if times_overlap(start_minutes, end_minutes, existing_start, existing_end):
                table_is_free = False
                break

        if table_is_free:
            return table

    return None


def create_booking(name, party_size, start_time_str, duration_minutes, booking_date=None):
    """Create a booking for a specific date."""
    if booking_date is None:
        booking_date = current_date if current_date else date.today()
    
    # Ensure we're working with the correct date's bookings
    if booking_date != current_date:
        load_bookings(booking_date)
    
    start_time_str = normalize_time(start_time_str)
    table = find_available_table(party_size, start_time_str, duration_minutes)
    if table is None:
        print("❌ No table available for that time/size.")
        return

    start_minutes = time_to_minutes(start_time_str)
    end_minutes = start_minutes + duration_minutes
    end_time_str = minutes_to_time(end_minutes)

    # Format date as string for storage
    date_str = booking_date.strftime("%Y-%m-%d") if isinstance(booking_date, date) else booking_date

    booking = {
        "name": name,
        "party_size": party_size,
        "date": date_str,
        "start_time": start_time_str,
        "end_time": end_time_str,
        "duration": duration_minutes,
        "table_id": table["id"],
    }
    bookings.append(booking)
    save_bookings()
    print(
        f"✅ Booking created for {name} {start_time_str}-{end_time_str} on table {table['id']}."
    )


def list_bookings(show_index=False):
    if not bookings:
        print("No bookings yet.")
        return

    date_str = current_date.strftime("%Y-%m-%d") if current_date else "Unknown"
    print(f"📋 Bookings for {date_str}:")
    for i, b in enumerate(bookings, start=1):
        line = (
            f"{b['start_time']}–{b['end_time']} | {b['name']} "
            f"({b['party_size']} ppl) -> Table {b['table_id']}"
        )
        if show_index:
            print(f"{i}) {line}")
        else:
            print(f"- {line}")


def list_bookings_for_date(booking_date, show_index=False):
    """Load and display all bookings for a specific date."""
    # Parse date if it's a string
    if isinstance(booking_date, str):
        booking_date = parse_date(booking_date)
    
    # Temporarily save current state
    old_bookings = bookings.copy()
    old_date = current_date
    
    # Load bookings for the requested date
    load_bookings(booking_date)
    
    # Display the bookings
    if not bookings:
        date_str = booking_date.strftime("%Y-%m-%d")
        print(f"No bookings for {date_str}.")
    else:
        list_bookings(show_index=show_index)
    
    # Restore previous state if needed
    # (Optional: comment out these lines if you want to keep the loaded date)
    # bookings[:] = old_bookings
    # current_date = old_date


def cancel_booking():
    if not bookings:
        print("There are no bookings to cancel.")
        return

    list_bookings(show_index=True)

    try:
        choice = int(input("Enter the number of the booking to cancel: "))
    except ValueError:
        print("Please enter a valid number.")
        return

    index = choice - 1
    if 0 <= index < len(bookings):
        removed = bookings.pop(index)
        save_bookings()
        print(
            f"🗑️ Canceled booking for {removed['name']} at {removed['start_time']} (Table {removed['table_id']})."
        )
    else:
        print("No booking with that number.")


def optimize_layout(layout_request=None, bookings_list=None, tables_list=None):
    """
    Analyze party sizes and table usage to perform rule-based layout optimization.
    
    Can be called with either:
    - layout_request: dict from build_layout_request() containing all data
    - bookings_list, tables_list: legacy support for direct lists
    
    Returns:
    - None (just prints analysis) for legacy mode
    - None or list of tables (new layout) when using layout_request
    
    Optimization rules:
    1. If parties are larger than available tables, try to group smaller tables
    2. Reposition tables to create space for grouping
    3. Move smaller tables to edges/corners to free central space
    4. Respect constraints (room size, no-go zones, minimum gaps)
    """
    # Handle both new and legacy calling conventions
    if layout_request is not None:
        # New mode: extract from layout request
        bookings_list = layout_request.get('bookings', [])
        tables_list = layout_request.get('tables', [])
        constraints_data = layout_request.get('constraints', {})
        capacity_metrics = layout_request.get('capacity_metrics', {})
        request_date = layout_request.get('date', 'unknown')
        
        print(f"\n🔍 Layout Optimization Analysis for {request_date}")
    else:
        # Legacy mode: use provided lists
        constraints_data = constraints if constraints else {}
        print("\n🔍 Layout Optimization Analysis")
    
    print("=" * 50)
    
    if not bookings_list:
        print("No bookings to analyze.")
        return None
    
    if not tables_list:
        print("No tables available.")
        return None
    
    # Analyze party size distribution
    party_sizes = [b['party_size'] for b in bookings_list]
    total_bookings = len(party_sizes)
    
    print(f"\n📊 Booking Statistics:")
    print(f"   Total bookings: {total_bookings}")
    print(f"   Average party size: {sum(party_sizes) / total_bookings:.1f}")
    print(f"   Largest party: {max(party_sizes)}")
    print(f"   Smallest party: {min(party_sizes)}")
    
    # Count bookings by party size
    size_counts = {}
    for size in party_sizes:
        size_counts[size] = size_counts.get(size, 0) + 1
    
    print(f"\n👥 Party Size Distribution:")
    for size in sorted(size_counts.keys()):
        print(f"   {size} people: {size_counts[size]} booking(s)")
    
    # Analyze table capacity
    table_seats = [t['seats'] for t in tables_list]
    print(f"\n🍽️ Table Configuration:")
    print(f"   Total tables: {len(tables_list)}")
    print(f"   Total capacity: {sum(table_seats)} seats")
    
    seat_counts = {}
    for seats in table_seats:
        seat_counts[seats] = seat_counts.get(seats, 0) + 1
    
    for seats in sorted(seat_counts.keys()):
        print(f"   {seats}-seat tables: {seat_counts[seats]}")
    
    # Generate suggestions
    print(f"\n💡 Optimization Suggestions:")
    
    # Suggestion 1: Check for oversized tables
    oversized = []
    for b in bookings_list:
        party = b['party_size']
        table_id = b['table_id']
        # Find the table
        table = next((t for t in tables_list if t['id'] == table_id), None)
        if table and table['seats'] - party >= 3:
            oversized.append((b['name'], party, table['seats'], table_id))
    
    if oversized:
        print(f"   ⚠️ {len(oversized)} booking(s) on oversized tables:")
        for name, party, seats, tid in oversized[:3]:  # Show first 3
            print(f"      • {name} ({party} people) on {seats}-seat table {tid}")
        print(f"      → Consider moving to smaller tables to free capacity")
    
    # Suggestion 2: Check for missing table sizes
    max_party = max(party_sizes)
    max_table = max(table_seats)
    needs_optimization = max_party > max_table
    
    if needs_optimization:
        print(f"   ⚠️ Largest party ({max_party}) exceeds largest table ({max_table})")
        print(f"      → Attempting rule-based layout optimization...")
    
    # Suggestion 3: Most common party size
    most_common_size = max(size_counts, key=size_counts.get)
    matching_tables = seat_counts.get(most_common_size, 0)
    print(f"   ℹ️ Most common party size: {most_common_size} people ({size_counts[most_common_size]} bookings)")
    if matching_tables == 0:
        print(f"      → No {most_common_size}-seat tables available")
        print(f"      → Consider adding or repositioning tables for this size")
    elif matching_tables < size_counts[most_common_size]:
        print(f"      → Only {matching_tables} table(s) match this size")
        print(f"      → Consider adding more {most_common_size}-seat tables")
    
    print("\n" + "=" * 50)
    
    # Only perform optimization in layout_request mode
    if layout_request is None:
        return None
    
    # Perform rule-based optimization if needed
    if needs_optimization:
        print(f"\n🔧 Applying Rule-Based Optimization")
        print("=" * 50)
        
        optimized_tables = _perform_layout_optimization(
            tables_list, 
            bookings_list, 
            constraints_data,
            max_party
        )
        
        if optimized_tables:
            return optimized_tables
    
    return None


def _perform_layout_optimization(tables_list, bookings_list, constraints_data, max_party_size):
    """
    Perform rule-based layout optimization.
    
    Strategy:
    1. Group smaller tables together to accommodate larger parties
    2. Move small tables to edges to free central space
    3. Position larger table groupings in the center
    """
    import copy
    
    # Get constraints
    room = constraints_data.get('room', {'width': 800, 'height': 600})
    rules = constraints_data.get('layout_rules', {})
    no_go_zones = constraints_data.get('no_go_zones', [])
    
    room_width = room.get('width', 800)
    room_height = room.get('height', 600)
    min_gap = rules.get('min_gap_between_tables', 20)
    min_wall_clearance = rules.get('min_wall_clearance', 10)
    
    # Create a copy of tables to modify
    new_tables = copy.deepcopy(tables_list)
    
    # Sort tables by size (smallest first)
    new_tables.sort(key=lambda t: t['seats'])
    
    # Identify which tables to group
    tables_to_group = []
    remaining_capacity_needed = max_party_size
    
    for table in new_tables:
        if remaining_capacity_needed > 0:
            tables_to_group.append(table)
            remaining_capacity_needed -= table['seats']
    
    if not tables_to_group:
        print("   ❌ No suitable tables found for grouping")
        return None
    
    total_grouped_capacity = sum(t['seats'] for t in tables_to_group)
    
    print(f"   📍 Grouping {len(tables_to_group)} tables (capacity: {total_grouped_capacity}) for party of {max_party_size}")
    
    # Helper function to check if position is valid
    def is_position_valid(x, y, width, height, exclude_table_id=None):
        # Check room boundaries
        if x < min_wall_clearance or y < min_wall_clearance:
            return False
        if x + width > room_width - min_wall_clearance:
            return False
        if y + height > room_height - min_wall_clearance:
            return False
        
        # Check no-go zones
        for zone in no_go_zones:
            zx, zy = zone['x'], zone['y']
            zw, zh = zone['width'], zone['height']
            
            # Check if rectangles overlap
            if not (x + width < zx or x > zx + zw or y + height < zy or y > zy + zh):
                return False
        
        # Check overlap with other tables
        for table in new_tables:
            if table['id'] == exclude_table_id:
                continue
            
            tx, ty = table['x'], table['y']
            tw, th = table['width'], table['height']
            
            # Check if too close (within min_gap)
            if not (x + width + min_gap < tx or x > tx + tw + min_gap or 
                    y + height + min_gap < ty or y > ty + th + min_gap):
                return False
        
        return True
    
    # Strategy 1: Position grouped tables in center
    center_x = room_width // 2
    center_y = room_height // 2
    
    # Try to place tables to group side-by-side in center
    current_x = center_x - sum(t['width'] + min_gap for t in tables_to_group) // 2
    current_y = center_y
    
    repositioned_count = 0
    
    for table in tables_to_group:
        new_x = current_x
        new_y = current_y - table['height'] // 2
        
        if is_position_valid(new_x, new_y, table['width'], table['height'], table['id']):
            old_x, old_y = table['x'], table['y']
            table['x'] = new_x
            table['y'] = new_y
            repositioned_count += 1
            print(f"      • Table {table['id']} ({table['seats']} seats): ({old_x},{old_y}) → ({new_x},{new_y})")
        
        current_x += table['width'] + min_gap
    
    # Strategy 2: Move remaining small tables to edges
    remaining_tables = [t for t in new_tables if t not in tables_to_group]
    
    if remaining_tables:
        print(f"   📍 Repositioning {len(remaining_tables)} remaining tables to edges")
        
        # Position along top edge
        edge_x = min_wall_clearance
        edge_y = min_wall_clearance
        
        for table in remaining_tables:
            if is_position_valid(edge_x, edge_y, table['width'], table['height'], table['id']):
                old_x, old_y = table['x'], table['y']
                table['x'] = edge_x
                table['y'] = edge_y
                repositioned_count += 1
                print(f"      • Table {table['id']} ({table['seats']} seats): ({old_x},{old_y}) → ({edge_x},{edge_y})")
                
                edge_x += table['width'] + min_gap
                
                # Wrap to next row if needed
                if edge_x + table['width'] > room_width - min_wall_clearance:
                    edge_x = min_wall_clearance
                    edge_y += max(t['height'] for t in remaining_tables if t['x'] < edge_x) + min_gap
    
    if repositioned_count > 0:
        print(f"\n   ✅ Optimized layout: repositioned {repositioned_count} tables")
        print(f"   💡 Tables {', '.join(str(t['id']) for t in tables_to_group)} can now be grouped for party of {max_party_size}")
        return new_tables
    else:
        print(f"   ⚠️ Could not reposition tables - layout constraints too restrictive")
        return None


def compute_capacity(bookings_list, tables_list, analysis_date):
    """
    Calculate capacity metrics for a specific date:
    - Total bookings
    - Bookings that could not be seated
    - Total wasted seats (unused capacity)
    """
    print("\n📊 Capacity Analysis")
    print("=" * 60)
    
    # Format date for display
    if isinstance(analysis_date, str):
        date_str = analysis_date
    else:
        date_str = analysis_date.strftime("%Y-%m-%d")
    
    print(f"Date: {date_str}")
    
    if not bookings_list:
        print("\n⚠️ No bookings for this date.")
        print("=" * 60)
        return
    
    if not tables_list:
        print("\n⚠️ No tables available.")
        print("=" * 60)
        return
    
    # Metrics
    total_bookings = len(bookings_list)
    total_seats_used = sum(b['party_size'] for b in bookings_list)
    
    # Calculate wasted seats
    wasted_seats = 0
    booking_details = []
    
    for booking in bookings_list:
        party_size = booking['party_size']
        table_id = booking['table_id']
        
        # Find the table
        table = next((t for t in tables_list if t['id'] == table_id), None)
        if table:
            table_seats = table['seats']
            waste = table_seats - party_size
            wasted_seats += waste
            
            booking_details.append({
                'name': booking['name'],
                'party': party_size,
                'table_id': table_id,
                'table_seats': table_seats,
                'waste': waste
            })
    
    # Calculate total capacity used
    total_table_seats = sum(bd['table_seats'] for bd in booking_details)
    
    # Efficiency metrics
    if total_table_seats > 0:
        efficiency = (total_seats_used / total_table_seats) * 100
    else:
        efficiency = 0
    
    # Display results
    print(f"\n📈 Summary:")
    print(f"   Total bookings: {total_bookings}")
    print(f"   Total guests: {total_seats_used}")
    print(f"   Total table capacity used: {total_table_seats} seats")
    print(f"   Wasted seats: {wasted_seats} seats")
    print(f"   Capacity efficiency: {efficiency:.1f}%")
    
    # Show details
    print(f"\n📋 Booking Details:")
    for bd in booking_details:
        waste_indicator = "⚠️" if bd['waste'] >= 3 else "✓" if bd['waste'] == 0 else "○"
        print(f"   {waste_indicator} {bd['name']:15} - {bd['party']} guests on {bd['table_seats']}-seat table {bd['table_id']} "
              f"(waste: {bd['waste']} seat{'s' if bd['waste'] != 1 else ''})")
    
    # Recommendations
    print(f"\n💡 Recommendations:")
    if efficiency < 70:
        print(f"   ⚠️ Low efficiency ({efficiency:.1f}%) - Many tables are oversized for parties")
        print(f"      → Consider reassigning guests to better-fitting tables")
    elif efficiency < 85:
        print(f"   ○ Moderate efficiency ({efficiency:.1f}%) - Some optimization possible")
        print(f"      → Review table assignments for large waste values")
    else:
        print(f"   ✅ Good efficiency ({efficiency:.1f}%) - Tables well-matched to party sizes")
    
    if wasted_seats >= total_bookings * 2:
        print(f"   ⚠️ High waste ratio ({wasted_seats}/{total_seats_used} wasted/used)")
        print(f"      → Average waste of {wasted_seats/total_bookings:.1f} seats per booking")
    
    print("=" * 60)
    
    return {
        'total_bookings': total_bookings,
        'total_guests': total_seats_used,
        'total_capacity': total_table_seats,
        'wasted_seats': wasted_seats,
        'efficiency': efficiency
    }


def build_layout_request(request_date):
    """
    Build a comprehensive layout request containing all relevant information.
    
    Returns a dictionary with:
    - date: the selected date
    - tables: list of tables with positions and dimensions
    - bookings: list of bookings for that date
    - constraints: room constraints and layout rules
    - capacity_metrics: efficiency and waste calculations
    """
    # Parse date if string
    if isinstance(request_date, str):
        request_date = parse_date(request_date)
    
    # Format date for storage
    date_str = request_date.strftime("%Y-%m-%d")
    
    # Load bookings for the specified date
    temp_bookings = []
    temp_current_date = current_date
    
    # Load bookings for the requested date
    load_bookings(request_date)
    temp_bookings = bookings.copy()
    
    # Compute capacity metrics
    capacity_metrics = None
    if temp_bookings and tables:
        capacity_metrics = compute_capacity(temp_bookings, tables, request_date)
    else:
        capacity_metrics = {
            'total_bookings': 0,
            'total_guests': 0,
            'total_capacity': 0,
            'wasted_seats': 0,
            'efficiency': 0.0
        }
    
    # Build the comprehensive request
    layout_request = {
        'date': date_str,
        'tables': tables.copy(),
        'bookings': temp_bookings,
        'constraints': constraints.copy() if constraints else {},
        'capacity_metrics': capacity_metrics,
        'metadata': {
            'generated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'total_tables': len(tables),
            'total_bookings': len(temp_bookings)
        }
    }
    
    return layout_request


def export_layout_request(request_date, filename=None):
    """
    Export a layout request to a JSON file for external processing (AI/API).
    
    This function builds a complete layout request and saves it to a file,
    allowing it to be sent to external AI services or APIs for optimization.
    
    Args:
        request_date: Date string (YYYY-MM-DD) or date object
        filename: Optional custom filename. If None, uses default pattern:
                 layout_request_YYYY-MM-DD.json
    
    Returns:
        dict: {
            'success': bool,
            'message': str,
            'filename': str,
            'data': dict (the layout request)
        }
    
    Example:
        result = export_layout_request("2025-11-15")
        # Creates: layout_request_2025-11-15.json
        
        result = export_layout_request("2025-11-15", "my_custom_request.json")
        # Creates: my_custom_request.json
    """
    try:
        # Build the layout request
        layout_request = build_layout_request(request_date)
        
        # Parse date for filename if needed
        if isinstance(request_date, str):
            date_obj = parse_date(request_date)
        else:
            date_obj = request_date
        
        # Generate filename if not provided
        if filename is None:
            filename = f"layout_request_{date_obj.strftime('%Y-%m-%d')}.json"
        
        # Ensure .json extension
        if not filename.endswith('.json'):
            filename += '.json'
        
        # Write to file with pretty formatting
        with open(filename, 'w') as f:
            json.dump(layout_request, f, indent=4, sort_keys=False)
        
        # Calculate file size for feedback
        file_size = os.path.getsize(filename)
        
        return {
            'success': True,
            'message': f'Layout request exported successfully',
            'filename': filename,
            'file_size': file_size,
            'data': layout_request
        }
        
    except Exception as e:
        return {
            'success': False,
            'message': f'Failed to export layout request: {str(e)}',
            'filename': filename,
            'error': str(e)
        }


def validate_layout(new_tables, constraints_data):
    """
    Comprehensive validation of table layout.
    
    Checks:
    1. All tables are inside room bounds
    2. Tables do not overlap with each other
    3. Table IDs are preserved (all original IDs still present)
    4. Required fields are present and valid
    5. No negative positions or dimensions
    
    Args:
        new_tables: List of table dictionaries with id, seats, x, y, width, height
        constraints_data: Constraints dictionary with room dimensions
        
    Returns:
        dict: {
            'valid': bool,
            'errors': list of error messages,
            'warnings': list of warning messages
        }
    """
    errors = []
    warnings = []
    
    # Get room dimensions
    room = constraints_data.get('room', {})
    room_width = room.get('width', 800)
    room_height = room.get('height', 600)
    no_go_zones = constraints_data.get('no_go_zones', [])
    
    # Get original table IDs for comparison
    global tables
    original_ids = {t['id'] for t in tables} if tables else set()
    
    # Validation 1: Check all tables are inside room bounds
    for table in new_tables:
        if not isinstance(table, dict):
            errors.append(f"Invalid table entry: must be a dictionary")
            continue
        
        table_id = table.get('id', '?')
        x = table.get('x', 0)
        y = table.get('y', 0)
        width = table.get('width', 0)
        height = table.get('height', 0)
        
        # Check if table fits within room
        if x < 0 or y < 0:
            errors.append(f"Table {table_id}: Position ({x}, {y}) has negative coordinates")
        
        if x + width > room_width:
            errors.append(f"Table {table_id}: Right edge ({x + width}) exceeds room width ({room_width})")
        
        if y + height > room_height:
            errors.append(f"Table {table_id}: Bottom edge ({y + height}) exceeds room height ({room_height})")
    
    # Validation 2: Check tables do not overlap with each other
    for i, table1 in enumerate(new_tables):
        if not isinstance(table1, dict):
            continue
        
        x1 = table1.get('x', 0)
        y1 = table1.get('y', 0)
        w1 = table1.get('width', 0)
        h1 = table1.get('height', 0)
        id1 = table1.get('id', '?')
        
        for j, table2 in enumerate(new_tables[i+1:], start=i+1):
            if not isinstance(table2, dict):
                continue
            
            x2 = table2.get('x', 0)
            y2 = table2.get('y', 0)
            w2 = table2.get('width', 0)
            h2 = table2.get('height', 0)
            id2 = table2.get('id', '?')
            
            # Check if rectangles overlap
            # Two rectangles do NOT overlap if:
            # - One is to the left of the other
            # - One is above the other
            if not (x1 + w1 <= x2 or x2 + w2 <= x1 or y1 + h1 <= y2 or y2 + h2 <= y1):
                errors.append(f"Table {id1} at ({x1},{y1}) overlaps with Table {id2} at ({x2},{y2})")
    
    # Validation 3: Check table IDs are preserved
    if original_ids:
        new_ids = {t.get('id') for t in new_tables if isinstance(t, dict)}
        
        # Check for missing IDs
        missing_ids = original_ids - new_ids
        if missing_ids:
            errors.append(f"Missing table IDs from original layout: {sorted(missing_ids)}")
        
        # Warn about new IDs (not an error, just informational)
        added_ids = new_ids - original_ids
        if added_ids:
            warnings.append(f"New table IDs added to layout: {sorted(added_ids)}")
    
    # Additional validation: Check for overlaps with no-go zones (warning only)
    for table in new_tables:
        if not isinstance(table, dict):
            continue
        
        tx = table.get('x', 0)
        ty = table.get('y', 0)
        tw = table.get('width', 0)
        th = table.get('height', 0)
        tid = table.get('id', '?')
        
        for zone in no_go_zones:
            zx = zone.get('x', 0)
            zy = zone.get('y', 0)
            zw = zone.get('width', 0)
            zh = zone.get('height', 0)
            zname = zone.get('name', 'Unnamed zone')
            
            # Check for overlap
            if not (tx + tw <= zx or tx >= zx + zw or ty + th <= zy or ty >= zy + zh):
                warnings.append(f"Table {tid}: Overlaps with no-go zone '{zname}' at ({zx},{zy})")
    
    # Return validation result
    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings
    }


def apply_new_layout(new_tables):
    """
    Validate and apply a new table layout to tables.json.
    
    Uses validate_layout() for comprehensive validation including:
    - Room boundary checks
    - Table overlap detection
    - Table ID preservation
    - Required field validation
    
    Args:
        new_tables: List of table dictionaries with id, seats, x, y, width, height
        
    Returns:
        dict: {'success': bool, 'message': str, 'errors': list, 'warnings': list}
    """
    global tables
    
    errors = []
    warnings = []
    
    # Validation 1: Check if input is a list
    if not isinstance(new_tables, list):
        return {
            'success': False,
            'message': 'Input must be a list of table dictionaries',
            'errors': ['Invalid input type'],
            'warnings': []
        }
    
    # Validation 2: Check if empty
    if len(new_tables) == 0:
        return {
            'success': False,
            'message': 'Cannot apply empty table layout',
            'errors': ['No tables provided'],
            'warnings': []
        }
    
    # Validation 3: Check max tables constraint
    if constraints:
        max_tables = constraints.get('layout_rules', {}).get('max_tables', 20)
        if len(new_tables) > max_tables:
            errors.append(f'Too many tables: {len(new_tables)} exceeds maximum of {max_tables}')
    
    # Validation 4: Validate each table's required fields and basic properties
    required_fields = ['id', 'seats', 'x', 'y', 'width', 'height']
    table_ids = set()
    
    for i, table in enumerate(new_tables):
        # Check if table is a dict
        if not isinstance(table, dict):
            errors.append(f'Table {i}: Must be a dictionary')
            continue
        
        # Check required fields
        missing_fields = [field for field in required_fields if field not in table]
        if missing_fields:
            errors.append(f'Table {i}: Missing required fields: {", ".join(missing_fields)}')
            continue
        
        # Validate field types and values
        try:
            table_id = int(table['id'])
            seats = int(table['seats'])
            x = float(table['x'])
            y = float(table['y'])
            width = float(table['width'])
            height = float(table['height'])
            
            # Check for positive values
            if seats <= 0:
                errors.append(f'Table {table_id}: Seats must be positive (got {seats})')
            if width <= 0 or height <= 0:
                errors.append(f'Table {table_id}: Width and height must be positive')
            
            # Check for duplicate IDs
            if table_id in table_ids:
                errors.append(f'Table {table_id}: Duplicate table ID')
            table_ids.add(table_id)
            
        except (ValueError, TypeError) as e:
            errors.append(f'Table {i}: Invalid field type - {str(e)}')
    
    # If basic validation failed, don't proceed
    if errors:
        return {
            'success': False,
            'message': f'Basic validation failed with {len(errors)} error(s)',
            'errors': errors,
            'warnings': warnings
        }
    
    # Validation 5: Use validate_layout for comprehensive checks
    # This checks: room bounds, table overlaps, ID preservation
    validation_result = validate_layout(new_tables, constraints if constraints else {})
    
    if not validation_result['valid']:
        # Combine any existing warnings with validation warnings
        all_errors = errors + validation_result['errors']
        all_warnings = warnings + validation_result['warnings']
        
        return {
            'success': False,
            'message': f'Layout validation failed with {len(validation_result["errors"])} error(s)',
            'errors': all_errors,
            'warnings': all_warnings
        }
    
    # Add validation warnings to our warnings list
    warnings.extend(validation_result['warnings'])
    
    # Apply the new layout
    try:
        # Update global tables
        tables = new_tables.copy()
        
        # Save to file
        save_tables()
        
        message = f'Successfully applied new layout with {len(new_tables)} tables'
        if warnings:
            message += f' ({len(warnings)} warning(s))'
        
        return {
            'success': True,
            'message': message,
            'errors': [],
            'warnings': warnings,
            'tables_updated': len(new_tables)
        }
        
    except Exception as e:
        return {
            'success': False,
            'message': f'Failed to save layout: {str(e)}',
            'errors': [str(e)],
            'warnings': warnings
        }


def parse_date(date_str):
    """Parse a date string in YYYY-MM-DD format or return today's date."""
    date_str = date_str.strip()
    if not date_str or date_str.lower() == "today":
        return date.today()
    
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        print("⚠️ Invalid date format. Using today's date.")
        return date.today()


# ----------------------------
# MAIN PROGRAM
# ----------------------------
def main():
    load_constraints()
    load_tables()
    # Load today's bookings by default
    load_bookings(date.today())
    print("🍽️ Restaurant Booking System")
    print(f"Current date: {current_date.strftime('%Y-%m-%d')}")
    
    # Display room info
    room = constraints.get("room", {})
    rules = constraints.get("layout_rules", {})
    no_go = constraints.get("no_go_zones", [])
    print(f"Room: {room.get('width', 0)}x{room.get('height', 0)} | "
          f"Min gap: {rules.get('min_gap_between_tables', 0)}px | "
          f"No-go zones: {len(no_go)}")


    while True:
        print("\nWhat do you want to do?")
        print("1) Create a booking")
        print("2) List bookings")
        print("3) Cancel a booking")
        print("4) Change viewing date")
        print("5) List tables")
        print("6) Add a table")
        print("7) Edit a table")
        print("8) Optimize layout")
        print("9) Optimize layout for a date")
        print("10) Export layout request to file")
        print("11) Quit")

        choice = input("Enter choice (1-11): ")

        if choice == "1":
            date_input = input(f"Booking date (YYYY-MM-DD or 'today', default: {current_date.strftime('%Y-%m-%d')}): ").strip()
            if date_input:
                booking_date = parse_date(date_input)
                if booking_date != current_date:
                    load_bookings(booking_date)
            else:
                booking_date = current_date
            
            name = input("Guest name: ")
            party_size = int(input("Party size (number of people): "))
            start_time = input("Start time (e.g. 19:00): ")
            duration_input = input(
                "Duration in minutes (press Enter for 120): "
            ).strip()
            if duration_input == "":
                duration = 120
            else:
                duration = int(duration_input)

            create_booking(name, party_size, start_time, duration, booking_date)
        elif choice == "2":
            list_bookings()
        elif choice == "3":
            cancel_booking()
        elif choice == "4":
            date_input = input("Enter date to view (YYYY-MM-DD or 'today'): ").strip()
            new_date = parse_date(date_input)
            load_bookings(new_date)
            print(f"✅ Now viewing bookings for {current_date.strftime('%Y-%m-%d')}")
        elif choice == "5":
            list_tables()
        elif choice == "6":
            add_table()
        elif choice == "7":
            edit_table()
        elif choice == "8":
            # Legacy mode: analyze current bookings
            optimize_layout(bookings_list=bookings, tables_list=tables)
        elif choice == "9":
            # New mode: optimize for specific date
            date_input = input(f"Enter date for optimization (YYYY-MM-DD or 'today', default: {current_date.strftime('%Y-%m-%d')}): ").strip()
            if date_input:
                opt_date = parse_date(date_input)
            else:
                opt_date = current_date
            
            print(f"\n🔄 Building layout request for {opt_date.strftime('%Y-%m-%d')}...")
            layout_request = build_layout_request(opt_date)
            
            print(f"✅ Loaded {len(layout_request['bookings'])} bookings and {len(layout_request['tables'])} tables")
            
            # Call optimize_layout with the layout request
            new_layout = optimize_layout(layout_request)
            
            # If a new layout is returned, apply it
            if new_layout is not None:
                print("\n📋 New optimized layout generated!")
                apply_choice = input("Apply this layout? (yes/no): ").strip().lower()
                if apply_choice in ['yes', 'y']:
                    result = apply_new_layout(new_layout)
                    if result['success']:
                        print(f"✅ {result['message']}")
                        if result.get('warnings'):
                            print("⚠️ Warnings:")
                            for warning in result['warnings']:
                                print(f"   • {warning}")
                    else:
                        print(f"❌ Failed to apply layout: {result['message']}")
                        if result.get('errors'):
                            print("Errors:")
                            for error in result['errors']:
                                print(f"   • {error}")
                else:
                    print("Layout not applied.")
            else:
                print("\n💡 No automated layout generated. Review suggestions above.")
        elif choice == "10":
            # Export layout request to file
            date_input = input(f"Enter date to export (YYYY-MM-DD or 'today', default: {current_date.strftime('%Y-%m-%d')}): ").strip()
            if date_input:
                export_date = parse_date(date_input)
            else:
                export_date = current_date
            
            filename_input = input("Enter filename (press Enter for default): ").strip()
            filename = filename_input if filename_input else None
            
            print(f"\n📤 Exporting layout request for {export_date.strftime('%Y-%m-%d')}...")
            result = export_layout_request(export_date, filename)
            
            if result['success']:
                print(f"✅ {result['message']}")
                print(f"   File: {result['filename']}")
                print(f"   Size: {result['file_size']} bytes")
                print(f"\n💡 This file can be sent to external AI/API for optimization")
            else:
                print(f"❌ {result['message']}")
        elif choice == "11":
            print("Goodbye!")
            break
        else:
            print("Please enter a number between 1 and 11.")


if __name__ == "__main__":
    main()
