
from datetime import *
from dateutil import parser
from dateutil import tz
import statsapi
import pandas as pd
import requests

# gets last 8 days of games including today
last_five = statsapi.schedule(start_date=(datetime.now() - timedelta(days=8)).date(), end_date=(datetime.now() - timedelta(days=1)).date())

# configures data frame to continue the last eight days of games in the league
columns = ['date', 'away_team', 'away_id','away_score','home_team','home_id','home_score']
df = pd.DataFrame(columns=columns)

# for each game over the last eight days, logs a record into the dataframe above
for game in last_five:
    date = game['game_date']
    away = game['away_name']
    away_id = game['away_id']
    away_score = int(game['away_score'])
    home = game['home_name']
    home_id = game['home_id']
    home_score = int(game['home_score'])
    data = [date,away,away_id,away_score,home,home_id,home_score]
    df.loc[len(df)] = data

df = df[(df['home_score']>0) | (df['away_score']>0)]

# gets list of all teams in the league
get_teams = statsapi.lookup_team('')

# builds a list of all teams
teams = []

for team in get_teams:
    teams.append(team['name'])

# configures a dataframe to contain each teams run differential over their last five games
columns_run_diff = ['team', 'l5_run_diff']
df_run_diff = pd.DataFrame(columns=columns_run_diff)

# for each team in the league, calculates their run differential over the last five games
for team in teams:
    # builds dataframe team_games that contains data on the teams last five games
    team_away_games = df[df.away_team == team]
    team_home_games = df[df.home_team == team]
    all_team_games = [team_home_games, team_away_games]
    team_games = pd.concat(all_team_games).sort_values(by='date', ascending=True).tail(5)

    # calculates run differential for the team over the last five games
    team_away_games_runs = team_games[team_games.away_team == team]
    team_home_games_runs = team_games[team_games.home_team == team]
    away_runs_for = team_away_games_runs['away_score'].sum()
    home_runs_for = team_home_games_runs['home_score'].sum()
    team_runs_for = int(away_runs_for) + int(home_runs_for)
    away_runs_against = team_away_games_runs['home_score'].sum()
    home_runs_against = team_home_games_runs['away_score'].sum()
    team_runs_against = away_runs_against + home_runs_against
    team_run_differential = team_runs_for - team_runs_against

    # writes a record to the dataframe containing team and last five games run differential
    data_run_diff = [str(team), str(team_run_differential)]
    df_run_diff.loc[len(df_run_diff)] = data_run_diff

# draftkings API specs
API_KEY = '7f908dfa6f555a6f509f958b2353ce65'
SPORT = 'baseball_mlb'  # baseball_mlb for regular season / baseball_mlb_preseason for preseason
REGIONS = 'us'
MARKETS = 'h2h'  # h2h | spreads | totals. Multiple can be specified if comma delimited
ODDS_FORMAT = 'american'
DATE_FORMAT = 'iso'
BOOKMAKER = 'draftkings'
EST_DATE = datetime.now().astimezone(tz.gettz('America/New_York')).date()

# gets list of all MLB games moneylines
odds_response = requests.get(
    f'https://api.the-odds-api.com/v4/sports/{SPORT}/odds',
    params={
        'api_key': API_KEY,
        'regions': REGIONS,
        'markets': MARKETS,
        'oddsFormat': ODDS_FORMAT,
        'dateFormat': DATE_FORMAT,
        'bookmakers': BOOKMAKER
    }
)

odds_json = odds_response.json()

columns = ['date','team','odds']
odds_df = pd.DataFrame(columns=columns)

for game in odds_json:
    start_time = parser.parse(game['commence_time'])
    date = start_time.astimezone(tz.gettz('America/New_York')).date()
    home_team = game['home_team']
    away_team = game['away_team']
    odds = game['bookmakers'][0]['markets'][0]['outcomes']
    for i in odds:
        team = i['name']
        odds = i['price']
        data = [date, team, odds]
        odds_df.loc[len(odds_df)] = data

todays_odds = odds_df[odds_df.date == EST_DATE]

next_date_odds = odds_df.date.min()

# gets all games played today
games_today = statsapi.schedule(start_date=next_date_odds, end_date=next_date_odds)

columns_todays_games = ['date', 'home_team','away_team','home_pitcher','away_pitcher','home_team_run_diff','away_team_run_diff','favorite'
    ,'dog','dog_ml','fav_ml_dk','dog_ml_dk','dog_odds_gap']
df_todays_games = pd.DataFrame(columns=columns_todays_games)

for game in games_today:
    date = game['game_date']
    away_team = game['away_name']
    home_team = game['home_name']
    away_pitcher = game['away_probable_pitcher']
    home_pitcher = game['home_probable_pitcher']
    away_team_run_diff = int(df_run_diff[df_run_diff.team == away_team]['l5_run_diff'].sum())
    home_team_run_diff = int(df_run_diff[df_run_diff.team == home_team]['l5_run_diff'].sum())

    if away_team_run_diff > 0 and home_team_run_diff > 0 and away_team_run_diff >= home_team_run_diff:
        run_diff = (away_team_run_diff - home_team_run_diff) / 2
    elif away_team_run_diff < 0 and home_team_run_diff < 0 and away_team_run_diff >= home_team_run_diff:
        run_diff = (away_team_run_diff - home_team_run_diff) / 2
    elif away_team_run_diff > 0 and home_team_run_diff > 0 and away_team_run_diff < home_team_run_diff:
        run_diff = (home_team_run_diff - away_team_run_diff) / 2
    elif away_team_run_diff < 0 and home_team_run_diff < 0 and away_team_run_diff < home_team_run_diff:
        run_diff = (home_team_run_diff - away_team_run_diff) / 2
    else:
        run_diff = (abs(home_team_run_diff) + abs(away_team_run_diff)) / 2

    run_diff_one_game = run_diff / 5

    if away_team_run_diff > home_team_run_diff:
        favorite = away_team
        dog = home_team
    elif home_team_run_diff > away_team_run_diff:
        favorite = home_team
        dog = away_team
    else:
        favorite = 'EVEN'
        dog = 'EVEN'

    al_teams = ['Oakland Athletics','Seattle Mariners','Texas Rangers','Tampa Bay Rays','Toronto Blue Jays','Minnesota Twins',
                'Chicago White Sox','New York Yankees','Los Angeles Angels','Baltimore Orioles','Boston Red Sox',
                'Cleveland Guardians','Detroit Tigers','Houston Astros','Kansas City Royals']

    al_cents_per_run = 1 / 4.2742998353
    nl_cents_per_run = 1 / 4.512345679

    if home_team in al_teams:
        moneyline = round(((al_cents_per_run * run_diff_one_game) * 100) + 100,0)
    else:
        moneyline = round(((nl_cents_per_run * run_diff_one_game) * 100) + 100,0)

    fav_ml = int(-moneyline)
    dog_ml = "+" + str(int(moneyline))

    away_team_run_ml_dk = todays_odds[todays_odds.team == away_team]['odds'].sum()
    home_team_run_ml_dk = todays_odds[todays_odds.team == home_team]['odds'].sum()

    fav_odds_dk = todays_odds[todays_odds.team == favorite]['odds'].sum()
    dog_odds_dk = todays_odds[todays_odds.team == dog]['odds'].sum()

    if dog_odds_dk <= 0:
        dog_ml_gap = 0
    else:
        dog_ml_gap = dog_odds_dk - moneyline

    data_todays_games = [date,home_team,away_team,home_pitcher,away_pitcher,home_team_run_diff,away_team_run_diff,favorite,dog
        ,moneyline,fav_odds_dk,dog_odds_dk,dog_ml_gap] # hi
    df_todays_games.loc[len(df_todays_games)] = data_todays_games

take_these_lines = df_todays_games[(df_todays_games['dog_odds_gap'] > 10) & (df_todays_games['dog_ml_dk'] < 200)]

def run_predictions():
    print(take_these_lines.to_string())
    return take_these_lines
