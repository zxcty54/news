import os
import json
import threading
import time
import requests
import firebase_admin
from firebase_admin import credentials, firestore
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ✅ Load Firebase credentials from Render environment variable
firebase_credentials = os.getenv("FIREBASE_CREDENTIALS")

if firebase_credentials:
    cred_dict = json.loads(firebase_credentials)  # Convert string to dictionary
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
else:
    raise ValueError("🚨 FIREBASE_CREDENTIALS environment variable is missing!")

# ✅ API Configuration
API_KEY = "fxf_IxSwVBEIZNwwMkh3GyZM"  # Replace with your actual API key
BASE_URL = "https://api.fxfeed.io/v1/latest"
BASE_CURRENCY = "USD"
CURRENCIES = ["INR", "EUR", "GBP", "JPY"]  # Top 5 currencies including USD

# ✅ Function to Fetch Exchange Rates
def fetch_exchange_rates():
    try:
        # Construct API request URL
        currencies_str = ",".join(CURRENCIES)
        url = f"{BASE_URL}?api_key={API_KEY}&base={BASE_CURRENCY}&currencies={currencies_str}"
        
        response = requests.get(url)
        data = response.json()

        if not data.get("success"):
            print("❌ Error fetching exchange rates:", data)
            return

        exchange_rates = data["rates"]
        exchange_rates["base_currency"] = BASE_CURRENCY
        exchange_rates["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")

        # ✅ Store in Firebase Firestore
        db.collection("currency_rates").document("latest").set(exchange_rates)
        
        print("✅ Exchange rates updated:", exchange_rates)

    except Exception as e:
        print("❌ Error fetching exchange rates:", str(e))

    # ✅ Auto-update every 15 minutes
    threading.Timer(900, fetch_exchange_rates).start()  # 900s = 15 min

# ✅ Start Background Update Task
fetch_exchange_rates()

@app.route('/')
def home():
    return "✅ Currency Exchange Rate API is Running!"

@app.route('/update-currency-rates')
def manual_update():
    try:
        fetch_exchange_rates()
        return jsonify({"message": "✅ Currency exchange rates updated successfully!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/currency-rates')
def get_currency_rates():
    try:
        doc = db.collection("currency_rates").document("latest").get()
        if doc.exists:
            return jsonify(doc.to_dict())
        else:
            return jsonify({"error": "No data available"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
