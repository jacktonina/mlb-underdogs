
from datetime import *
import statsapi
import pandas as pd
import matplotlib.pyplot as mp
import requests


# gets last 8 days of games including today
last_five = statsapi.schedule(start_date=(datetime.now() - timedelta(days=21)).date(), end_date=(datetime.now() - timedelta(days=1)).date())

# configures data frame to continue the last eight days of games in the league
columns = ['date', 'away_team', 'away_id','away_score','home_team','home_id','home_score']
df = pd.DataFrame(columns=columns)

# for each game over the last 21 days, logs a record into the dataframe above
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

# gets list of all teams in the league
get_teams = statsapi.lookup_team('')

# builds a list of all teams
teams = []

for team in get_teams:
    teams.append(team['name'])

# configures a dataframe to contain each teams run differential over their last five games
columns_run_diff = ['team', 'ln_run_diff', 'lookback']
df_run_diff = pd.DataFrame(columns=columns_run_diff)

# for each team in the league, calculates their run differential over the last five games
for i in range(3,11):
    for team in teams:
        lookback = i
        # builds dataframe team_games that contains data on the teams last five games
        team_away_games = df[df.away_team == team]
        team_home_games = df[df.home_team == team]
        all_team_games = [team_home_games, team_away_games]
        team_games = pd.concat(all_team_games).tail(i)

        # calculates run differential for the team over the last five games
        team_away_games_runs = team_games[team_games.away_team == team]
        team_home_games_runs = team_games[team_games.home_team == team]
        away_runs_for = team_away_games_runs['away_score'].sum()
        home_runs_for = team_home_games_runs['home_score'].sum()
        team_runs_for = away_runs_for + home_runs_for
        away_runs_against = team_away_games_runs['home_score'].sum()
        home_runs_against = team_home_games_runs['away_score'].sum()
        team_runs_against = away_runs_against + home_runs_against
        team_run_differential = team_runs_for - team_runs_against

        # writes a record to the dataframe containing team and last five games run differential
        data_run_diff = [str(team), str(team_run_differential), lookback]
        df_run_diff.loc[len(df_run_diff)] = data_run_diff

# draftkings API specs
API_KEY = '7f908dfa6f555a6f509f958b2353ce65'
SPORT = 'baseball_mlb'  # baseball_mlb for regular season
REGIONS = 'us'
MARKETS = 'h2h'  # h2h | spreads | totals. Multiple can be specified if comma delimited
ODDS_FORMAT = 'american'
DATE_FORMAT = 'iso'
BOOKMAKER = 'draftkings'

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
    date = game['commence_time'][0:10]
    home_team = game['home_team']
    away_team = game['away_team']
    odds = game['bookmakers'][0]['markets'][0]['outcomes']
    for i in odds:
        team = i['name']
        odds = i['price']
        data = [date, team, odds]
        odds_df.loc[len(odds_df)] = data


next_date_odds = odds_df.date.min()

# # gets all games played today
games_today = statsapi.schedule(start_date=next_date_odds, end_date=next_date_odds)


columns_todays_games = ['date','home_team','away_team','home_team_run_diff','away_team_run_diff','favorite','fav_ml','dog','dog_ml','lookback','dog_ml_dk']
df_todays_games = pd.DataFrame(columns=columns_todays_games)

for game in games_today:
    date = game['game_date']
    away_team = game['away_name']
    home_team = game['home_name']
    print(home_team + ' ' + away_team)
    home_team_run_diff = df_run_diff[df_run_diff.team == home_team]
    away_team_run_diff = df_run_diff[df_run_diff.team == away_team]
    for i in range(3,11):
        lookback = i
        away_team_relevant_run_diff = away_team_run_diff[away_team_run_diff.lookback == lookback]['ln_run_diff'].sum()
        home_team_relevant_run_diff = home_team_run_diff[home_team_run_diff.lookback == lookback]['ln_run_diff'].sum()
        if away_team_relevant_run_diff == '':
            away_team_run_diff_final = 0
        else:
            away_team_run_diff_final = int(away_team_relevant_run_diff)

        if home_team_relevant_run_diff == '':
            home_team_run_diff_final = 0
        else:
            home_team_run_diff_final = int(home_team_relevant_run_diff)

        if away_team_run_diff_final > 0 and home_team_run_diff_final > 0 and away_team_run_diff_final >= home_team_run_diff_final:
            run_diff = (away_team_run_diff_final - home_team_run_diff_final) / 2
        elif away_team_run_diff_final < 0 and home_team_run_diff_final < 0 and away_team_run_diff_final >= home_team_run_diff_final:
            run_diff = (away_team_run_diff_final - home_team_run_diff_final) / 2
        elif away_team_run_diff_final > 0 and home_team_run_diff_final > 0 and away_team_run_diff_final < home_team_run_diff_final:
            run_diff = (home_team_run_diff_final - away_team_run_diff_final) / 2
        elif away_team_run_diff_final < 0 and home_team_run_diff_final < 0 and away_team_run_diff_final < home_team_run_diff_final:
            run_diff = (home_team_run_diff_final - away_team_run_diff_final) / 2
        else:
            run_diff = (abs(home_team_run_diff_final) + abs(away_team_run_diff_final)) / 2

        run_diff_one_game = run_diff / 5

        if away_team_run_diff_final > home_team_run_diff_final:
            favorite = away_team
            dog = home_team
        elif home_team_run_diff_final > away_team_run_diff_final:
            favorite = home_team
            dog = away_team
        else:
            favorite = 'EVEN'
            dog = 'EVEN'

        al_teams = ['Oakland Athletics', 'Seattle Mariners', 'Texas Rangers', 'Tampa Bay Rays', 'Toronto Blue Jays',
                    'Minnesota Twins',
                    'Chicago White Sox', 'New York Yankees', 'Los Angeles Angels', 'Baltimore Orioles',
                    'Boston Red Sox',
                    'Cleveland Guardians', 'Detroit Tigers', 'Houston Astros', 'Kansas City Royals']

        al_cents_per_run = 1 / 4.22
        nl_cents_per_run = 1 / 4.34

        if home_team in al_teams:
            moneyline = round(((al_cents_per_run * run_diff_one_game) * 100) + 100, 0)
        else:
            moneyline = round(((nl_cents_per_run * run_diff_one_game) * 100) + 100, 0)

        fav_ml = int(-moneyline)
        dog_ml = int(moneyline)

        dog_odds_dk = odds_df[odds_df.team == dog]['odds'].sum()

        data = [date, home_team, away_team, home_team_run_diff_final, away_team_run_diff_final, favorite, fav_ml, dog, dog_ml, lookback, dog_odds_dk]
        df_todays_games.loc[len(df_todays_games)] = data

print(df_todays_games.to_string())


for game in games_today:
    date = game['game_date']
    away_team = game['away_name']
    home_team = game['home_name']
    relevant_data = df_todays_games[df_todays_games.away_team == away_team]
    five_game_lookback = int(relevant_data[relevant_data.lookback == 5]['dog_ml'].sum())
    five_game_lookback_dk_ml = int(relevant_data[relevant_data.lookback == 5]['dog_ml_dk'].sum())
    fav = relevant_data[relevant_data.lookback == 5]['favorite'].values[0]
    print(relevant_data)
    plot = relevant_data.plot(x="lookback", y="dog_ml", kind="line", color='g', title=home_team + ' @ ' + away_team)
    plot.hlines(y=five_game_lookback, xmin=3, xmax=10, linewidth=2, color='r')
    plot.hlines(y=five_game_lookback_dk_ml, xmin=3, xmax=10, linewidth=2, color='b')
    plot.set_xlabel("Lookback")
    plot.set_ylabel("Underdog ML")
    plot.legend(["running_ml", "five_game_ml",'dk_ml']);
    mp.show()
