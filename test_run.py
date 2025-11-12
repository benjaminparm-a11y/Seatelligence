import sys
sys.path.insert(0, '/Users/benjaminparmeggiani/Res_Booking_1')

import api

print("Starting Flask app...")
api.app.run(debug=False, host="127.0.0.1", port=5003, use_reloader=False)
