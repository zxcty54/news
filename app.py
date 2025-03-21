import os
import json
import time
import requests
import firebase_admin
import feedparser  # ✅ Install with: pip install feedparser
from firebase_admin import credentials, firestore
from flask import Flask, jsonify

# ✅ Initialize Flask App
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ News API is Running!"

# ✅ Initialize Firebase
firebase_credentials = os.getenv("FIREBASE_CREDENTIALS")
if firebase_credentials:
    cred_dict = json.loads(firebase_credentials)
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
else:
    raise ValueError("🚨 FIREBASE_CREDENTIALS environment variable is missing!")

# ✅ RSS Feeds
RSS_FEEDS = {
    "Economic Times": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    "CNBC TV18": "https://www.cnbctv18.com/rss/market.xml",
    "Financial Express": "https://www.financialexpress.com/feed/"
}

def fetch_news_from_rss():
    """Fetches news from RSS feeds."""
    news_data = []
    
    for source, feed_url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(feed_url)
            if not feed.entries:
                print(f"❌ No news from {source}")
                continue
            
            for entry in feed.entries[:5]:  # ✅ Get top 5 news articles
                news_data.append({
                    "source": source,
                    "title": entry.title,
                    "link": entry.link
                })
        
        except Exception as e:
            print(f"❌ Error fetching RSS from {source}: {str(e)}")
    
    return news_data

def store_news_in_firebase():
    """Fetches and stores news in Firebase."""
    news_items = fetch_news_from_rss()
    
    if not news_items:
        print("❌ No news items fetched.")
        return
    
    print(f"✅ Storing {len(news_items)} news articles in Firebase...")

    batch = db.batch()
    collection_ref = db.collection("latest_news")
    
    # ✅ Delete old news before storing new ones
    docs = collection_ref.stream()
    for doc in docs:
        batch.delete(doc.reference)
    
    for item in news_items:
        print(f"📌 Storing: {item}")  # ✅ Debugging Log
        doc_ref = collection_ref.document()
        batch.set(doc_ref, item)
    
    batch.commit()
    print("✅ News stored in Firebase!")

# ✅ Flask API Endpoint to Manually Trigger Scraping
@app.route('/update-news', methods=['GET'])
def update_news():
    try:
        store_news_in_firebase()
        return jsonify({"message": "✅ News updated successfully!"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/latest-news', methods=['GET'])
def get_latest_news():
    try:
        docs = db.collection("latest_news").stream()
        news_list = [doc.to_dict() for doc in docs]
        return jsonify(news_list)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ✅ Background Task: Run Every 30 Minutes
def scheduled_news_update():
    while True:
        store_news_in_firebase()
        time.sleep(1800)  # ✅ Sleep for 30 minutes

# ✅ Run Flask App
if __name__ == '__main__':
    import threading
    threading.Thread(target=scheduled_news_update, daemon=True).start()  # ✅ Run in background

    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
