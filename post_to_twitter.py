from last_five_games import run_predictions
from datetime import date
import tweepy
import os

today = date.today()
formatted_date = today.strftime("%m/%d")

# client = tweepy.Client(
#     consumer_key=os.getenv("X_API_KEY"),
#     consumer_secret=os.getenv("X_API_KEY_SECRET"),
#     access_token=os.getenv("X_ACCESS_TOKEN"),
#     access_token_secret=os.getenv("X_ACCESS_TOKEN_SECRET")
# )

# Get your model result (this could be any result from your script)
todays_preds = run_predictions()

picks = []

for index, row in todays_preds.iterrows():
    underdog = row['dog']
    favorite = row['favorite']
    dog_ml_dk = row['dog_ml_dk']
    dog_ml_model = row['dog_ml']

    if dog_ml_model < 126 and dog_ml_dk < 151:
        units = 3
    elif dog_ml_model < 125 and dog_ml_dk < 176:
        units = 2
    else:
        units = 1

    pick_text = f"{underdog} ML +{dog_ml_dk} ({units}u)"
    picks.append(pick_text)

# Construct your tweet text
header = f"{formatted_date} Underdog ML Picks:"
tweet_text = f"{header}\n\n" + "\n".join(picks) + "\n" + "RT if you're riding todays dogs!" + "\n" + "#MLB #GamblingTwitter #FreePicks #GamblingX #MLBBets"
print(tweet_text)

# Post the tweet
# try:
#     client.create_tweet(text=tweet_text)
#     print("Tweet posted successfully!")
# except Exception as e:
#     print("An error occurred:", e)
