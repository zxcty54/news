import os
import json
import time
import feedparser
import firebase_admin
from firebase_admin import credentials, firestore
from flask import Flask, jsonify

# ✅ Initialize Flask App
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ RSS News API is Running!"

# ✅ Initialize Firebase
firebase_credentials = os.getenv("FIREBASE_CREDENTIALS")
if firebase_credentials:
    cred_dict = json.loads(firebase_credentials)
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
else:
    raise ValueError("🚨 FIREBASE_CREDENTIALS environment variable is missing!")

# ✅ RSS Feeds to Fetch News From
RSS_FEEDS = {
    "Moneycontrol": "https://www.moneycontrol.com/rss/latestnews.xml",
    "NDTV Profit": "https://www.ndtvprofit.com/feed",
    "LiveMint": "https://www.livemint.com/rss/news.xml"
}

# ✅ Function to Fetch News from RSS Feeds
def fetch_rss_news():
    news_data = []
    for source, url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            if not feed.entries:
                print(f"❌ No news found for {source}")
                continue

            for entry in feed.entries[:5]:  # ✅ Get top 5 articles per source
                news_data.append({
                    "source": source,
                    "title": entry.title,
                    "link": entry.link,
                    "published": entry.published if "published" in entry else "Unknown"
                })
        except Exception as e:
            print(f"❌ Error fetching RSS from {source}: {str(e)}")
    
    return news_data

# ✅ Store News in Firebase
def store_news_in_firebase():
    news_items = fetch_rss_news()
    if not news_items:
        print("❌ No news items fetched.")
        return
    
    batch = db.batch()
    collection_ref = db.collection("latest_news")

    # ✅ Delete old news before inserting new ones
    old_docs = collection_ref.stream()
    for doc in old_docs:
        doc.reference.delete()

    # ✅ Store new news
    for item in news_items:
        doc_ref = collection_ref.document()
        batch.set(doc_ref, item)

    batch.commit()
    print("✅ News updated in Firebase!")

# ✅ Flask API Endpoint to Manually Trigger News Update
@app.route('/update-news', methods=['GET'])
def update_news():
    try:
        store_news_in_firebase()
        return jsonify({"message": "✅ News updated successfully!"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ✅ API Endpoint to Fetch Latest News
@app.route('/latest-news', methods=['GET'])
def get_latest_news():
    try:
        docs = db.collection("latest_news").stream()
        news_list = [doc.to_dict() for doc in docs]
        return jsonify(news_list)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ✅ Background Task: Auto Update Every 30 Minutes
def scheduled_news_update():
    while True:
        store_news_in_firebase()
        time.sleep(1800)  # ✅ Sleep for 30 minutes

# ✅ Run Flask App
if __name__ == '__main__':
    import threading
    threading.Thread(target=scheduled_news_update, daemon=True).start()  # ✅ Background Auto-Update

    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
