import os
import json
import time
import requests
from bs4 import BeautifulSoup
import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase
firebase_credentials = os.getenv("FIREBASE_CREDENTIALS")
if firebase_credentials:
    cred_dict = json.loads(firebase_credentials)
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
else:
    raise ValueError("🚨 FIREBASE_CREDENTIALS environment variable is missing!")

# News Websites to Scrape
NEWS_SOURCES = {
    "Economic Times": "https://economictimes.indiatimes.com/markets",
    "CNBC18": "https://www.cnbctv18.com/market/",
    "Financial Express": "https://www.financialexpress.com/market/"
}

def scrape_news():
    news_data = []
    
    for source, url in NEWS_SOURCES.items():
        try:
            response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
            if response.status_code != 200:
                print(f"❌ Failed to fetch {source}")
                continue
            
            soup = BeautifulSoup(response.text, "html.parser")
            articles = []
            
            if source == "Economic Times":
                articles = soup.select(".eachStory h3 a")
            elif source == "CNBC18":
                articles = soup.select(".listview-story-card a")
            elif source == "Financial Express":
                articles = soup.select(".listitembx a")
            
            for article in articles[:5]:  # Get top 5 articles per source
                title = article.text.strip()
                link = article.get("href")
                if not link.startswith("http"):
                    link = url + link  # Make relative URLs absolute
                news_data.append({"source": source, "title": title, "link": link})
        
        except Exception as e:
            print(f"❌ Error scraping {source}: {str(e)}")
    
    return news_data

def store_news_in_firebase():
    news_items = scrape_news()
    if not news_items:
        print("❌ No news items scraped.")
        return
    
    batch = db.batch()
    collection_ref = db.collection("latest_news")
    
    for item in news_items:
        doc_ref = collection_ref.document()
        batch.set(doc_ref, item)
    
    batch.commit()
    print("✅ News stored in Firebase!")

# Run every 30 minutes
while True:
    store_news_in_firebase()
    time.sleep(1800)
