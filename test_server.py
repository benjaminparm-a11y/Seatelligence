from flask import Flask

app = Flask(__name__)

@app.route("/")
def index():
    return "Hello World!"

if __name__ == "__main__":
    print("Starting test server...")
    app.run(debug=False, host="127.0.0.1", port=5002)
