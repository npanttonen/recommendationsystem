import os
import sqlite3
import shutil
from flask import Flask, request, jsonify
from app import get_recommendations
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

def get_firefox_history():
    """Finds and copies the Firefox browsing history database."""
    profiles_path = os.path.expanduser("~\\AppData\\Roaming\\Mozilla\\Firefox\\Profiles")

    if not os.path.exists(profiles_path):
        return None  # Firefox is not installed or profile folder is missing

    # Find the profile folder containing places.sqlite
    history_db = None
    for profile in os.listdir(profiles_path):
        profile_path = os.path.join(profiles_path, profile, "places.sqlite")
        if os.path.exists(profile_path):
            history_db = profile_path
            break

    if not history_db:
        return None  # No valid profile with history found

    # Copy the database to avoid permission & locking issues
    temp_db = "firefox_history_copy.sqlite"
    shutil.copy2(history_db, temp_db)

    return temp_db  # Return copied file path

def get_chrome_history():
    """Finds and copies the Chrome browsing history database."""
    history_path = os.path.expanduser("~\\AppData\\Local\\Google\\Chrome\\User Data\\Default\\History")

    if not os.path.exists(history_path):
        return None  # Chrome history not found

    # Copy the database to avoid permission & locking issues
    temp_db = "chrome_history_copy.sqlite"
    shutil.copy2(history_path, temp_db)

    return temp_db  # Return copied file path

@app.route("/recommend/firefox", methods=["GET"])
def recommend_firefox():
    """API route to fetch Firefox browsing history and recommend movies."""
    history_file = get_firefox_history()

    if not history_file:
        return jsonify({"error": "Firefox history database not found"}), 400

    try:
        recommendations = get_recommendations(history_file)  # Pass file path, NOT file object
        os.remove(history_file)  # Clean up temporary file
        return jsonify(recommendations)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/recommend/chrome", methods=["GET"])
def recommend_chrome():
    """API route to fetch Chrome browsing history and recommend movies."""
    history_file = get_chrome_history()

    if not history_file:
        return jsonify({"error": "Chrome history database not found"}), 400

    try:
        recommendations = get_recommendations(history_file)  # Pass file path, NOT file object
        os.remove(history_file)  # Clean up temporary file
        return jsonify(recommendations)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5001)
