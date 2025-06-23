from last_five_games import run_predictions
from datetime import date
import tweepy
import os

today = date.today()
formatted_date = today.strftime("%-m/%-d")

client = tweepy.Client(
    consumer_key=os.getenv("X_API_KEY"),
    consumer_secret=os.getenv("X_API_KEY_SECRET"),
    access_token=os.getenv("X_ACCESS_TOKEN"),
    access_token_secret=os.getenv("X_ACCESS_TOKEN_SECRET")
)

# Get your model result (this could be any result from your script)
todays_preds = run_predictions()

picks = []

for index, row in todays_preds.iterrows():
    underdog = row['dog']
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
if len(picks) == 1:
    header = f"{formatted_date} Underdog ML Pick:"
    tweet_text = f"{header}\n\n" + "⚾️ " + "\n".join(picks) + "\n\n" + "Only one play from the model today, let's make it count!🎯 RT if you're riding!" + "\n\n" + "#SportsBetting #MLBPicks"
elif len(picks) == 2:
    header = f"{formatted_date} Underdog ML Picks:"
    tweet_text = f"{header}\n\n" + "⚾ " + "\n⚾ ".join(picks) + "\n\n" + "We got two plays from the model today! Think we can go 2-0??🧹🧹 RT if you're riding!" + "\n\n" + "#SportsBetting #MLBPicks"
elif len(picks) > 2 and len(picks) < 5:
    header = f"{formatted_date} Underdog ML Picks:"
    tweet_text = f"{header}\n\n" + "⚾ " + "\n⚾ ".join(picks) + "\n\n" + "Few picks today from our model, hopefully we get a couple hits! Can we sweep this slate? 🧹🧹🧹" + "\n\n" + "#SportsBetting #MLBPicks"
elif len(picks) >= 5:
    header = f"{formatted_date} Underdog ML Picks:"
    tweet_text = f"{header}\n\n" + "⚾ " + "\n⚾ ".join(picks) + "\n\n" + "Our model LOVES todays slate of dogs! Got a lot on the line here, let's have a day!💰💰 Which are you riding?" + "\n\n" + "#SportsBetting #MLBPicks"
else:
    tweet_text = f"Our model didn't turn up any underdogs with value today. Check back tomorrow for our next slate of picks!🔥" + "\n\n" + "What are your favorite bets today? Drop 'em in the thread!🧵"
print(tweet_text)

# Post the tweet
try:
    client.create_tweet(text=tweet_text)
    print("Tweet posted successfully!")
except Exception as e:
    print("An error occurred:", e)
