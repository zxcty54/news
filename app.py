from flask import Flask, jsonify
from flask_cors import CORS
import requests
from datetime import datetime, timedelta
import threading
import time
from firebase_admin import credentials, firestore, initialize_app

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend requests

# 🔥 Firebase Setup
cred = credentials.Certificate("firebase_credentials.json")  # Replace with your Firebase JSON file
initialize_app(cred)
db = firestore.client()
collection_ref = db.collection("currency_rates")

# 🌍 Currency API Config
API_KEY = "fxf_IxSwVBEIZNwwMkh3GyZM"
BASE_CURRENCY = "USD"
CURRENCIES = "INR,EUR,GBP,JPY,CNY"
API_URL = f"https://api.fxfeed.io/v1/latest?api_key={API_KEY}&base={BASE_CURRENCY}&currencies={CURRENCIES}"

def fetch_and_store_rates():
    """Fetches currency rates and stores them in Firebase."""
    response = requests.get(API_URL)
    
    if response.status_code == 200:
        data = response.json()
        
        if data.get("success"):
            rates = data["rates"]
            timestamp = datetime.utcnow()

            collection_ref.document("latest").set({
                "base": BASE_CURRENCY,
                "rates": rates,
                "timestamp": timestamp.isoformat()
            })
            print("✅ Rates updated:", rates)
            return rates
        else:
            print("❌ API Error:", data)
            return None
    else:
        print("❌ HTTP Error:", response.status_code)
        return None

def get_cached_rates():
    """Fetch cached rates if they are recent (within 15 mins)."""
    doc = collection_ref.document("latest").get()
    
    if doc.exists:
        data = doc.to_dict()
        last_updated = datetime.fromisoformat(data["timestamp"])
        time_diff = datetime.utcnow() - last_updated

        if time_diff < timedelta(minutes=15):  # Use cache if data is fresh
            print("♻️ Using cached rates")
            return data["rates"]
    
    print("🌐 Fetching new rates...")
    return fetch_and_store_rates()

@app.route("/currency_rates", methods=["GET"])
def get_currency_rates():
    """API endpoint for latest currency rates."""
    rates = get_cached_rates()
    if rates:
        return jsonify({"success": True, "base": BASE_CURRENCY, "rates": rates})
    else:
        return jsonify({"success": False, "message": "Failed to fetch rates"}), 500

def background_fetch():
    """Runs in a separate thread to fetch currency data every 15 minutes."""
    while True:
        fetch_and_store_rates()
        time.sleep(900)  # 900 seconds = 15 minutes

if __name__ == "__main__":
    # Start background thread
    threading.Thread(target=background_fetch, daemon=True).start()
    
    # Run Flask app
    app.run(host="0.0.0.0", port=5000, debug=True)
