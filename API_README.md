# API.PY - Quick Reference

## What Changed

The `POST /bookings` endpoint now:
- ✅ Imports and reuses availability logic from `app.py`
- ✅ Automatically finds and assigns available tables
- ✅ Returns 400 error if no table is available
- ✅ Saves to date-specific booking files
- ✅ No longer requires `table_id` in the request

## Usage

### Start the API Server

```bash
python api.py
# Server runs on http://127.0.0.1:5000
```

### Create a Booking (Option 1: with end_time)

```bash
curl -X POST http://127.0.0.1:5000/bookings \
  -H "Content-Type: application/json" \
  -d '{
    "date": "2025-11-10",
    "name": "John Doe",
    "party_size": 4,
    "start_time": "19:00",
    "end_time": "21:00"
  }'
```

### Create a Booking (Option 2: with duration_minutes)

```bash
curl -X POST http://127.0.0.1:5000/bookings \
  -H "Content-Type: application/json" \
  -d '{
    "date": "2025-11-10",
    "name": "Jane Smith",
    "party_size": 2,
    "start_time": "18:30",
    "duration_minutes": 90
  }'
```

## Success Response (201 Created)

```json
{
  "status": "ok",
  "message": "Booking created for John Doe, party of 4",
  "booking": {
    "name": "John Doe",
    "party_size": 4,
    "date": "2025-11-10",
    "start_time": "19:00",
    "end_time": "21:00",
    "table_id": 3
  },
  "table": {
    "id": 3,
    "seats": 4
  }
}
```

## Error Response (400 Bad Request)

```json
{
  "error": "No table available",
  "details": "No table found for party of 50 at 19:00 for 120 minutes"
}
```

## How It Works

1. **Receives request** with date, name, party_size, start_time, and duration
2. **Loads tables** using `app.load_tables()`
3. **Loads existing bookings** for the specified date using `app.load_bookings(date)`
4. **Finds available table** using `app.find_available_table(party_size, start_time, duration)`
5. **Returns 400** if no table available
6. **Creates booking** with auto-assigned table_id
7. **Saves to file** `bookings_YYYY-MM-DD.json`
8. **Returns 201** with booking and table details

## Key Functions Used from app.py

- `find_available_table(party_size, start_time, duration_minutes)` - Finds first available table
- `times_overlap(start1, end1, start2, end2)` - Checks for time conflicts
- `time_to_minutes(hhmm)` - Converts "19:00" to minutes since midnight
- `minutes_to_time(minutes)` - Converts minutes to "HH:MM" format
- `load_tables()` - Loads table configurations
- `load_bookings(date)` - Loads bookings for specific date

## Testing

Run the test suite:
```bash
python test_api.py
```

Run the comprehensive demo:
```bash
python demo_api_update.py
```
