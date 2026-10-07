"""
Entry point. Run with:  python run.py
Or with the Flask CLI:  flask --app run run --debug
"""
from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
