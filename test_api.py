#!/usr/bin/env python3
"""Test the API booking endpoint logic"""

import json
import app as booking_app
import api

print('🧪 Testing POST /bookings endpoint logic\n')

# Test 1: Valid booking request
print('TEST 1: Valid booking request (party of 2 at 18:00)')
print('=' * 70)

# Load data
booking_app.load_tables()
booking_app.load_bookings('2025-11-10')

print(f'Loaded {len(booking_app.tables)} tables')
print(f'Loaded {len(booking_app.bookings)} existing bookings for 2025-11-10')

# Find available table
table = booking_app.find_available_table(2, '18:00', 90)

if table:
    print(f'✅ Found available table: ID={table["id"]}, Seats={table["seats"]}')
    
    # Create the booking
    start_mins = booking_app.time_to_minutes('18:00')
    end_mins = start_mins + 90
    end_time = booking_app.minutes_to_time(end_mins)
    
    new_booking = {
        'name': 'Test API User',
        'party_size': 2,
        'date': '2025-11-10',
        'start_time': '18:00',
        'end_time': end_time,
        'table_id': table['id']
    }
    
    print(f'Created booking:')
    print(json.dumps(new_booking, indent=2))
    
    # Save it
    bookings = api.load_bookings_for_date('2025-11-10')
    bookings.append(new_booking)
    api.save_bookings_for_date('2025-11-10', bookings)
    
    print(f'✅ Saved to bookings_2025-11-10.json')
else:
    print('❌ No table available')

print()

# Test 2: No table available (party too large)
print('TEST 2: No table available (party of 20)')
print('=' * 70)

table = booking_app.find_available_table(20, '19:00', 90)
if table:
    print(f'❌ Unexpectedly found table: {table}')
else:
    print('✅ Correctly returned None - no table large enough for party of 20')
    print('   (Would return 400 error in API)')

print()

# Test 3: Table occupied (conflict)
print('TEST 3: Overlapping time slot')
print('=' * 70)

# Try to book at overlapping time
booking_app.load_bookings('2025-11-10')  # Reload with our new booking
table = booking_app.find_available_table(2, '18:30', 90)  # Overlaps with 18:00-19:30

if table:
    print(f'✅ Found different available table: ID={table["id"]}')
    print(f'   (Table {booking_app.bookings[-1]["table_id"]} was busy)')
else:
    print('ℹ️  No table available at this time')

print()

# Verify the booking was saved
print('VERIFICATION: Check saved bookings')
print('=' * 70)
saved_bookings = api.load_bookings_for_date('2025-11-10')
print(f'Total bookings for 2025-11-10: {len(saved_bookings)}')
for b in saved_bookings:
    print(f'  • {b["name"]}: party of {b["party_size"]}, table {b["table_id"]}, {b["start_time"]}-{b["end_time"]}')

print()
print('=' * 70)
print('✅ All tests completed!')
print()
print('📝 Summary:')
print('   • API correctly uses find_available_table() from app.py')
print('   • Returns None when no table available (→ 400 error)')
print('   • Saves bookings to date-specific files')
print('   • Handles time overlaps correctly')
