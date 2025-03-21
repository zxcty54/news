import os
import json
import time
import requests
from bs4 import BeautifulSoup
import firebase_admin
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

# ✅ News Websites to Scrape
NEWS_SOURCES = {
    "Economic Times": "https://economictimes.indiatimes.com/markets",
    "CNBC18": "https://www.cnbctv18.com/market/",
    "Financial Express": "https://www.financialexpress.com/market/"
}

def scrape_news():
    """Scrapes latest news from sources and returns a list of articles."""
    news_data = []
    
    for source, url in NEWS_SOURCES.items():
        try:
            print(f"🔄 Scraping {source}...")
            response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
            
            if response.status_code != 200:
                print(f"❌ Failed to fetch {source} - Status Code: {response.status_code}")
                continue
            
            soup = BeautifulSoup(response.text, "html.parser")
            articles = []
            
            if source == "Economic Times":
                articles = soup.select(".eachStory h3 a")
            elif source == "CNBC18":
                articles = soup.select(".listview-story-card a")
            elif source == "Financial Express":
                articles = soup.select(".listitembx a")
            
            for article in articles[:5]:  # ✅ Get top 5 articles per source
                title = article.text.strip()
                link = article.get("href")
                if not link.startswith("http"):
                    link = url + link  # ✅ Convert relative URLs to absolute
                news_data.append({"source": source, "title": title, "link": link})
        
        except Exception as e:
            print(f"❌ Error scraping {source}: {str(e)}")
    
    print(f"✅ Scraped {len(news_data)} articles.")
    return news_data

def store_news_in_firebase():
    """Fetches and stores news in Firebase."""
    news_items = scrape_news()
    
    if not news_items:
        print("❌ No news items scraped.")
        return
    
    batch = db.batch()
    collection_ref = db.collection("latest_news")
    
    # ✅ Delete old news before storing new ones
    docs = collection_ref.stream()
    for doc in docs:
        batch.delete(doc.reference)
    
    for item in news_items:
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
    """Fetches latest news from Firebase and returns JSON response."""
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
