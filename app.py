import os
import json
import requests
import threading
import time
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore

# 🔹 Load Firebase credentials from Render Environment Variables
firebase_json = os.getenv("FIREBASE_KEY")  # Set this in Render's environment variables

if firebase_json:
    cred_dict = json.loads(firebase_json)  # Convert string to dictionary
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)
else:
    raise ValueError("❌ Firebase credentials not found in environment variables!")

# 🔹 Firestore Database Instance
db = firestore.client()

# 🔹 Currency API Configuration
API_KEY = "fxf_IxSwVBEIZNwwMkh3GyZM"  # Your API key
API_URL = f"https://api.fxfeed.io/v1/latest?api_key={API_KEY}&base=USD&currencies=INR,EUR,GBP,JPY,AUD"

# 🔹 API Call Limit Management (3000 requests per month)
REQUESTS_PER_MONTH = 3000
INTERVAL_SECONDS = (30 * 24 * 60 * 60) / REQUESTS_PER_MONTH  # Time gap per request (~14.4 mins)

def fetch_and_store_currency():
    """Fetch latest currency exchange rates and store them in Firebase."""
    try:
        response = requests.get(API_URL)
        data = response.json()

        if data.get("success"):
            currency_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "rates": data["rates"]
            }
            db.collection("currency_rates").document("latest").set(currency_data)
            print("✅ Currency data updated in Firestore:", currency_data)
        else:
            print("❌ Error fetching currency data:", data)

    except Exception as e:
        print("⚠️ Exception:", e)

def update_currency_periodically():
    """Runs the fetch function at fixed intervals."""
    while True:
        fetch_and_store_currency()
        time.sleep(INTERVAL_SECONDS)  # Wait for next API call

# 🔹 Start the currency update process in a background thread
threading.Thread(target=update_currency_periodically, daemon=True).start()

# 🔹 Flask API to Fetch Data (Optional)
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/get_currency_rates', methods=['GET'])
def get_currency_rates():
    """Fetch latest currency rates from Firestore."""
    doc_ref = db.collection("currency_rates").document("latest")
    doc = doc_ref.get()
    
    if doc.exists:
        return jsonify(doc.to_dict())
    else:
        return jsonify({"error": "No currency data found"}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
