from last_five_games import run_predictions
import tweepy
import os

# Twitter API credentials (store these securely, e.g., as GitHub secrets)
consumer_key = os.getenv("X_API_KEY")
consumer_secret = os.getenv("X_API_KEY_SECRET")
access_token = os.getenv("X_ACCESS_TOKEN")
access_token_secret = os.getenv("X_ACCESS_TOKEN_SECRET")

# Authenticate to Twitter
auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)
api = tweepy.API(auth)

# Get your model result (this could be any result from your script)
# todays_preds = run_predictions()
# print(todays_preds)

# Construct your tweet text
#tweet_text = f"Daily model update: {todays_preds}"
tweet_text = f"Daily model update: "
print(tweet_text)

# Post the tweet
try:
    api.update_status(tweet_text)
    print("Tweet posted successfully!")
except Exception as e:
    print("An error occurred:", e)
