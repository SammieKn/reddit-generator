"""
A script that generates comments using the RedditAPI and OpenAI API. 
"""

import praw
import openai
import time
import os
from dotenv import load_dotenv

# Load API keys from .env file
load_dotenv()

REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT")
REDDIT_USER_NAME = os.getenv("REDDIT_USER_NAME")
REDDIT_USER_PASSWORD = os.getenv("REDDIT_USER_PASSWORD")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # Replace with your actual OpenAI API key

def connect_to_reddit():
    reddit = praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=REDDIT_USER_AGENT,
        username=REDDIT_USER_NAME,
        password=REDDIT_USER_PASSWORD,
    )
    return reddit

# Initialize OpenAI client
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# Function to generate a reply using OpenAI GPT-4o Mini
def generate_reply(post_title, post_body, comment_text):
    prompt = (
        f"You're replying to a comment in an AskReddit thread.\n\n"
        f"Post Title: {post_title}\n"
        f"Post Body: {post_body if post_body else '[No body]'}\n"
        f"Comment: {comment_text}\n\n"
        f"Write a thoughtful and engaging response:"
    )

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Be engaging and relevant."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=150
    )
    
    return response.choices[0].message.content.strip()

# Function to generate a witty joke/comment
def generate_witty_comment(post_title, post_body, top_comments):
    comments_text = "\n".join([f"- {comment.body}" for comment in top_comments])

    prompt = (
        f"You're replying to an AskReddit post with the most obvious, witty, and funny comment. The goal is to become a popular comment to gain karma.\n\n"
        f"Post Title: {post_title}\n"
        f"Post Body: {post_body if post_body else '[No body]'}\n"
        f"Top 5 Comments:\n{comments_text}\n\n"
        f"Make a short, actually funny, and witty joke or reply. No political correctness, just say what a real Redditor would:"
    )

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Be funny, witty, and to the point. Don't be afraid to make a controversial statement or joke. The joke should feel natural and obvious, not forced."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=50
    )
    
    return response.choices[0].message.content.strip()

# Connect to AskReddit and get rising posts
reddit = connect_to_reddit()
subreddit = reddit.subreddit("AskReddit")
rising_posts = subreddit.rising(limit=5)

for post in rising_posts:
    print(f"\nPost: {post.title}")
    
    # Fetch and sort top 5 comments by upvotes
    post.comments.replace_more(limit=0)
    top_comments = sorted(post.comments.list(), key=lambda c: c.score, reverse=True)[:5]

    if not top_comments:
        print("No top comments found. Skipping...")
        continue

    # Generate a witty reply
    for i in range(10):
        witty_reply = generate_witty_comment(post.title, post.selftext, top_comments)
        print(f"🔥 Funny Reply {i+1}: {witty_reply}")

    # Uncomment the line below to actually post the reply
    # post.reply(witty_reply)

    time.sleep(2)  # Avoid spamming Reddit's API

print("\n✅ Done!")
