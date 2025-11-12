import sys
sys.path.insert(0, '/Users/benjaminparmeggiani/Res_Booking_1')

try:
    print("Importing api...")
    import api
    print("API imported successfully!")
    print(f"Flask app: {api.app}")
    print(f"Routes: {list(api.app.url_map.iter_rules())}")
except Exception as e:
    print(f"Error importing api: {e}")
    import traceback
    traceback.print_exc()
