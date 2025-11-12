"""
Interactive demonstration of the rule-based optimization feature
Run this to see the complete workflow
"""
from app import load_constraints, load_tables, build_layout_request, optimize_layout, apply_new_layout
import json

print("=" * 70)
print(" " * 15 + "OPTIMIZATION DEMO")
print("=" * 70)

# Setup: Create a scenario with a large party
print("\n📝 Step 1: Creating test scenario")
print("-" * 70)

# Create booking for party of 8 (larger than max table of 6)
test_booking = {
    "name": "Corporate Dinner",
    "party_size": 8,
    "date": "2025-12-01",
    "start_time": "18:30",
    "end_time": "21:00",
    "duration": 150,
    "table_id": None
}

with open('bookings_2025-12-01.json', 'w') as f:
    json.dump([test_booking], f, indent=4)

print(f"✅ Created booking:")
print(f"   - {test_booking['name']}")
print(f"   - Party of {test_booking['party_size']} people")
print(f"   - Current max table: 6 seats ⚠️")

# Step 2: Build layout request
print("\n🔄 Step 2: Building layout request")
print("-" * 70)

load_constraints()
load_tables()
layout_request = build_layout_request("2025-12-01")

print(f"✅ Layout request ready:")
print(f"   - Date: {layout_request['date']}")
print(f"   - Tables: {len(layout_request['tables'])}")
print(f"   - Bookings: {len(layout_request['bookings'])}")

# Step 3: Run optimization
print("\n🔍 Step 3: Running optimization")
print("-" * 70)

new_layout = optimize_layout(layout_request)

# Step 4: Show results
print("\n📊 Step 4: Results")
print("-" * 70)

if new_layout:
    print(f"✅ Optimized layout generated!")
    print(f"\n📍 Table repositioning summary:")
    
    original_tables = layout_request['tables']
    changes = []
    
    for new_table in new_layout:
        original = next(t for t in original_tables if t['id'] == new_table['id'])
        if new_table['x'] != original['x'] or new_table['y'] != original['y']:
            changes.append({
                'id': new_table['id'],
                'seats': new_table['seats'],
                'old_pos': (original['x'], original['y']),
                'new_pos': (new_table['x'], new_table['y'])
            })
    
    if changes:
        print(f"   Moved {len(changes)} tables:")
        for change in changes:
            print(f"   • Table {change['id']} ({change['seats']} seats): {change['old_pos']} → {change['new_pos']}")
    
    # Calculate which tables can be grouped
    grouped_tables = sorted(new_layout[:3], key=lambda t: t['id'])
    total_capacity = sum(t['seats'] for t in grouped_tables)
    
    print(f"\n💡 Optimization benefit:")
    print(f"   • Tables {', '.join(str(t['id']) for t in grouped_tables)} can be grouped")
    print(f"   • Combined capacity: {total_capacity} seats")
    print(f"   • Accommodates party of {test_booking['party_size']} ✅")
    
    print(f"\n�� You can now apply this layout using apply_new_layout()")
else:
    print("❌ No optimization generated")

print("\n" + "=" * 70)
print("✅ DEMO COMPLETE")
print("=" * 70)

# Cleanup
import os
if os.path.exists('bookings_2025-12-01.json'):
    os.remove('bookings_2025-12-01.json')
    print("\n🧹 Cleaned up test files")

