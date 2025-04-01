import sqlite3
import pandas as pd
import datetime
import csv
import torch
import time
import os
import shutil
from transformers import pipeline
from concurrent.futures import ThreadPoolExecutor

# Check if GPU is available
device = 0 if torch.cuda.is_available() else -1  # Use GPU if available, else CPU
print(f"⚡ Device set to {'GPU' if device == 0 else 'CPU'}")

# Load the optimized zero-shot classifier
classifier = pipeline("zero-shot-classification", model="roberta-large-mnli", device=device)

# Define category labels
CATEGORIES = ["Entertainment", "Technology", "News", "Shopping", "Education", "Health"]

# 🔹 Get browser history path (Fixed for Chrome)
def get_browser_history_path(browser):
    if browser == "firefox":
        profiles_path = os.path.expanduser("~\\AppData\\Roaming\\Mozilla\\Firefox\\Profiles")
        if os.path.exists(profiles_path):
            for profile in os.listdir(profiles_path):
                history_db = os.path.join(profiles_path, profile, "places.sqlite")
                if os.path.exists(history_db):
                    return history_db
    elif browser == "chrome":
        history_db = os.path.expanduser("~\\AppData\\Local\\Google\\Chrome\\User Data\\Default\\History")
        if os.path.exists(history_db):
            # ✅ FIX: Copy Chrome's history to a temp file
            temp_db = "chrome_history_copy.sqlite"
            shutil.copy2(history_db, temp_db)  
            return temp_db
    return None

# 🔹 Load history for Firefox & Chrome (Reads from copied DB for Chrome)
def load_history(history_db, browser, limit=1000):
    conn = sqlite3.connect(history_db)

    if browser == "firefox":
        query = f"""
        SELECT moz_places.url, moz_places.title, moz_places.visit_count, moz_historyvisits.visit_date
        FROM moz_places
        JOIN moz_historyvisits ON moz_places.id = moz_historyvisits.place_id
        ORDER BY moz_historyvisits.visit_date DESC
        LIMIT {limit};
        """
    elif browser == "chrome":
        query = f"""
        SELECT urls.url, urls.title, urls.visit_count, visits.visit_time
        FROM urls
        JOIN visits ON urls.id = visits.url
        ORDER BY visits.visit_time DESC
        LIMIT {limit};
        """

    try:
        history = pd.read_sql_query(query, conn)
        return history
    except Exception as e:
        print(f"❌ Error loading history: {e}")
        return None
    finally:
        conn.close()

# 🔹 Preprocess history (Common for both browsers)
def preprocess_history(history, browser):
    if history is None:
        return None

    platform_names = [
        "YouTube", "Netflix", "Amazon", "Hulu", "Twitter", "Facebook", "Instagram", 
        "Reddit", "Twitch", "Vimeo", "Pinterest", "Spotify", "Apple", "Google", 
        "TikTok", "Disney", "BBC", "CNN", "Game", "Movie"
    ]

    if browser == "firefox":
        history['visit_date'] = history['visit_date'].apply(
            lambda x: datetime.datetime(1970, 1, 1) + datetime.timedelta(microseconds=x)
        )
    elif browser == "chrome":
        history['visit_time'] = history['visit_time'].apply(
            lambda x: datetime.datetime(1601, 1, 1) + datetime.timedelta(microseconds=x)
        )
        history.rename(columns={"visit_time": "visit_date"}, inplace=True)

    history = history[~history['url'].str.contains('chrome://|file://', na=False)]
    
    history.loc[:, 'title'] = history['title'].apply(
        lambda x: x if not x else ' '.join([word for word in x.split() if word not in platform_names])
    )

    # Remove duplicate titles while keeping the first occurrence
    history = history.drop_duplicates(subset=['title'], keep='first')

    return history

# 🔹 Classify a batch of titles
def classify_batch(batch):
    results = classifier(batch, CATEGORIES)

    # Extract relevant information
    classified_entries = []
    for i, result in enumerate(results):
        label_scores = dict(zip(result['labels'], result['scores']))
        entertainment_score = label_scores.get("Entertainment", 0)
        if entertainment_score > 0.25:  # Only keep titles with score > 0.25
            classified_entries.append((batch[i], entertainment_score))

    return classified_entries

# 🔹 Classify history using multi-threading
def classify_history_parallel(history, batch_size=20, max_workers=4):
    history_texts = history['title'].dropna().tolist()

    # Ensure no empty strings and remove duplicates
    history_texts = list(set([t.strip() for t in history_texts if t.strip()]))
    
    if not history_texts:
        print("⚠️ No valid history titles found for classification.")
        return []

    filtered_entries = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        batches = [history_texts[i:i + batch_size] for i in range(0, len(history_texts), batch_size)]
        
        start_classify = time.time()
        results = executor.map(classify_batch, batches)
        end_classify = time.time()

        for batch_results in results:
            filtered_entries.extend(batch_results)

    print(f"⏳ Classification Time: {end_classify - start_classify:.2f} seconds")
    return filtered_entries

# 🔹 Save results to CSV
def save_to_csv(entries, filename="filtered_history.csv"):
    if not entries:
        print("⚠️ No entries above 0.2 score to save.")
        return

    start_save = time.time()
    
    with open(filename, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Title", "Entertainment Score"])
        writer.writerows(entries)
    
    end_save = time.time()
    print(f"\n✅ Filtered history saved to {filename} in {end_save - start_save:.2f} seconds")

# 🔹 Get filtered history (Firefox or Chrome)
def get_filtered_history(browser="firefox", limit=1000):
    print(f"📥 Loading {browser.capitalize()} browsing history...")
    start_load = time.time()
    
    history_db = get_browser_history_path(browser)
    if not history_db:
        print(f"❌ No {browser.capitalize()} history found.")
        return []

    history = load_history(history_db, browser, limit)

    end_load = time.time()
    print(f"⏳ History Load Time: {end_load - start_load:.2f} seconds")

    history = preprocess_history(history, browser)

    if history is not None:
        print(f"🚀 Classifying {browser.capitalize()} history using multi-threading...")
        filtered_entries = classify_history_parallel(history, batch_size=20, max_workers=4)
        return filtered_entries
    else:
        return []


# 🔹 Main function
def main():
    start_time = time.time()

    browser = input("Enter browser (firefox/chrome): ").strip().lower()
    if browser not in ["firefox", "chrome"]:
        print("❌ Invalid browser! Use 'firefox' or 'chrome'.")
        return

    filtered_entries = get_filtered_history(browser, limit=1000)

    if filtered_entries:
        print("\n🎬 Filtered Entertainment History (Top 10) 🎬\n")
        for entry in filtered_entries[:10]:
            print(f"📝 {entry[0]} | 🎭 Score: {entry[1]:.2f}")
            print("-" * 80)

        save_to_csv(filtered_entries)
    else:
        print("No entries classified as Entertainment.")

    end_time = time.time()
    print(f"\n🚀 Total Execution Time: {end_time - start_time:.2f} seconds")

if __name__ == "__main__":
    main()
