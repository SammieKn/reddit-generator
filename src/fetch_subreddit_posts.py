"""
A script to fetch reddit posts for a given subreddit sorted on new and place them in a db.
"""

import sqlite3
import praw
import time
import sys
import os
from dotenv import load_dotenv

load_dotenv()
# Set up Reddit API credentials
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT")
REDDIT_USER_NAME = os.getenv("REDDIT_USER_NAME")
REDDIT_USER_PASSWORD = os.getenv("REDDIT_USER_PASSWORD")
DB_NAME = "./data/reddit_data.db"

def connect_to_reddit():
    reddit = praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=REDDIT_USER_AGENT,
        username=REDDIT_USER_NAME,
        password=REDDIT_USER_PASSWORD,
    )
    return reddit

def create_database():
    """Creates the SQLite database with a table for storing posts."""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id TEXT PRIMARY KEY,
            subreddit TEXT,
            created_utc INTEGER,
            num_comments INTEGER,
            score INTEGER,
            upvote_ratio REAL,
            title TEXT,
            url TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS progress (
            subreddit TEXT PRIMARY KEY,
            last_processed_id TEXT,
            oldest_timestamp INTEGER
        )
    """)

    conn.commit()
    conn.close()

def get_progress(subreddit_name):
    """Fetches the last processed post ID and timestamp from the database for resuming."""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT last_processed_id, oldest_timestamp FROM progress WHERE subreddit = ?", (subreddit_name,))
    row = cur.fetchone()
    conn.close()
    return (row[0], row[1]) if row else (None, None)

def save_progress(subreddit_name, last_processed_id, oldest_timestamp):
    """Saves the progress to resume later."""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO progress (subreddit, last_processed_id, oldest_timestamp) 
        VALUES (?, ?, ?) ON CONFLICT(subreddit) 
        DO UPDATE SET last_processed_id = ?, oldest_timestamp = ?
    """, (subreddit_name, last_processed_id, oldest_timestamp, last_processed_id, oldest_timestamp))
    conn.commit()
    conn.close()

def fetch_posts(reddit, subreddit_name, before=None):
    """Fetches posts continuously from a given subreddit, going backwards in time."""
    subreddit = reddit.subreddit(subreddit_name)
    posts = []
    oldest_timestamp = None
    
    try:
        # If before is None, start from the newest posts
        # If before is provided, get posts older than that timestamp
        params = {"before": f"t3_{before}"} if before else {}
        
        for submission in subreddit.new(limit=None, params=params):
            post_data = {
                "id": submission.id,
                "subreddit": subreddit_name,
                "created_utc": submission.created_utc,
                "num_comments": submission.num_comments,
                "score": submission.score,
                "upvote_ratio": submission.upvote_ratio,
                "title": submission.title,
                "url": submission.url
            }
            posts.append(post_data)
            oldest_timestamp = submission.created_utc
            last_id = submission.id

        if posts:
            return posts, last_id, oldest_timestamp
        return [], None, None

    except Exception as e:
        print(f"Error fetching posts: {e}")
        return [], None, None

def save_posts_to_db(posts):
    """Saves posts to the SQLite database."""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    for post in posts:
        cur.execute("""
            INSERT OR IGNORE INTO posts (id, subreddit, created_utc, num_comments, score, upvote_ratio, title, url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            post["id"], post["subreddit"], post["created_utc"], post["num_comments"],
            post["score"], post["upvote_ratio"], post["title"], post["url"]
        ))

    conn.commit()
    conn.close()

def main():
    """Main function to scrape continuously until stopped."""
    reddit = connect_to_reddit()
    create_database()
    subreddit_name = "AskReddit"

    last_id, oldest_timestamp = get_progress(subreddit_name)
    
    print(f"Starting scraping for r/{subreddit_name}. Press CTRL+C to stop.")
    print(f"Resuming from timestamp: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(oldest_timestamp)) if oldest_timestamp else 'Beginning'}")

    while True:
        try:
            posts, last_id, oldest_timestamp = fetch_posts(reddit, subreddit_name, before=last_id)
            
            if posts:
                save_posts_to_db(posts)
                save_progress(subreddit_name, last_id, oldest_timestamp)
                oldest_date = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(oldest_timestamp))
                print(f"Saved {len(posts)} posts. Oldest post from: {oldest_date}")

            else:
                print("No more posts found or reached Reddit's limit. Sleeping for 5 minutes...")
                time.sleep(300)

        except KeyboardInterrupt:
            print("\nStopping script. Progress saved.")
            sys.exit()

        except Exception as e:
            print(f"Unexpected error: {e}. Retrying in 2 minutes...")
            time.sleep(120)

if __name__ == "__main__":
    main()