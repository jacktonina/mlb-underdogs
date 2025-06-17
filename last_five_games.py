from datetime import datetime, timedelta

import streamlit
from dateutil import parser
from dateutil import tz
import statsapi
import pandas as pd
import requests


def get_historical_data(days_back=8):
    """Get MLB games from the past days_back days and create a dataframe."""
    # Get historical games
    start_date = (datetime.now() - timedelta(days=days_back)).date()
    end_date = (datetime.now() - timedelta(days=1)).date()
    games = statsapi.schedule(start_date=start_date, end_date=end_date)

    # Build dataframe
    columns = ['date', 'away_team', 'away_id', 'away_score', 'home_team', 'home_id', 'home_score']
    df = pd.DataFrame(columns=columns)

    for game in games:
        date = game['game_date']
        away = game['away_name']
        away_id = game['away_id']
        away_score = int(game['away_score'])
        home = game['home_name']
        home_id = game['home_id']
        home_score = int(game['home_score'])
        data = [date, away, away_id, away_score, home, home_id, home_score]
        df.loc[len(df)] = data

    # Filter out games without scores
    return df[(df['home_score'] > 0) | (df['away_score'] > 0)]


def calculate_team_run_differentials(historical_df):
    """Get all teams and calculate run differentials for each team over their last 5 games."""
    # Get all teams
    get_teams = statsapi.lookup_team('')
    teams = [team['name'] for team in get_teams]

    # Calculate run differentials
    columns_run_diff = ['team', 'l5_run_diff']
    df_run_diff = pd.DataFrame(columns=columns_run_diff)

    for team in teams:
        # Build dataframe of team's last five games
        team_away_games = historical_df[historical_df.away_team == team]
        team_home_games = historical_df[historical_df.home_team == team]
        all_team_games = [team_home_games, team_away_games]
        team_games = pd.concat(all_team_games).sort_values(by='date', ascending=True).tail(5)

        # Calculate run differential
        team_away_games_runs = team_games[team_games.away_team == team]
        team_home_games_runs = team_games[team_games.home_team == team]
        away_runs_for = team_away_games_runs['away_score'].sum()
        home_runs_for = team_home_games_runs['home_score'].sum()
        team_runs_for = int(away_runs_for) + int(home_runs_for)
        away_runs_against = team_away_games_runs['home_score'].sum()
        home_runs_against = team_home_games_runs['away_score'].sum()
        team_runs_against = away_runs_against + home_runs_against
        team_run_differential = team_runs_for - team_runs_against

        # Add to dataframe
        data_run_diff = [str(team), str(team_run_differential)]
        df_run_diff.loc[len(df_run_diff)] = data_run_diff

    return df_run_diff


def get_draftkings_odds_df():
    """Get moneylines from DraftKings API and convert to dataframe."""
    API_KEY = '7f908dfa6f555a6f509f958b2353ce65'

    # Get odds from API
    odds_response = requests.get(
        f'https://api.the-odds-api.com/v4/sports/baseball_mlb/odds',
        params={
            'api_key': API_KEY,
            'regions': 'us',
            'markets': 'h2h',
            'oddsFormat': 'american',
            'dateFormat': 'iso',
            'bookmakers': 'draftkings'
        }
    )
    odds_json = odds_response.json()

    # Convert to dataframe
    columns = ['date', 'team', 'odds']
    odds_df = pd.DataFrame(columns=columns)

    for game in odds_json:
        try:
            start_time = parser.parse(game['commence_time'])
            date = start_time.astimezone(tz.gettz('America/New_York')).date()
            odds = game['bookmakers'][0]['markets'][0]['outcomes']

            for i in odds:
                team = i['name']
                odds_value = i['price']
                data = [date, team, odds_value]
                odds_df.loc[len(odds_df)] = data
        except (KeyError, IndexError):
            # Skip this game if any required field is missing
            continue

    todays_odds = odds_df[odds_df['date'] == datetime.now().date()]

    return todays_odds


def analyze_todays_games(df_run_diff, todays_odds):
    """Get today's games, analyze them and build prediction dataframe."""
    # Get EST date
    EST_DATE = datetime.now().astimezone(tz.gettz('America/New_York')).date()

    # Determine which date to use for games
    if not todays_odds[todays_odds.date == EST_DATE].empty:
        next_date_odds = EST_DATE
    else:
        next_date_odds = todays_odds.date.min()

    # Get today's games
    games_today = statsapi.schedule(start_date=next_date_odds, end_date=next_date_odds)

    # Set up dataframe for today's games
    columns_todays_games = [
        'date', 'home_team', 'away_team', 'home_pitcher', 'away_pitcher',
        'home_team_run_diff', 'away_team_run_diff', 'favorite', 'dog',
        'dog_ml', 'fav_ml_dk', 'dog_ml_dk', 'dog_odds_gap'
    ]
    df_todays_games = pd.DataFrame(columns=columns_todays_games)

    # League constants
    al_teams = [
        'Oakland Athletics', 'Seattle Mariners', 'Texas Rangers', 'Tampa Bay Rays',
        'Toronto Blue Jays', 'Minnesota Twins', 'Chicago White Sox', 'New York Yankees',
        'Los Angeles Angels', 'Baltimore Orioles', 'Boston Red Sox', 'Cleveland Guardians',
        'Detroit Tigers', 'Houston Astros', 'Kansas City Royals'
    ]
    al_cents_per_run = 1 / 4.2742998353
    nl_cents_per_run = 1 / 4.512345679

    # Process each game
    for game in games_today:
        date = game['game_date']
        away_team = game['away_name']
        home_team = game['home_name']
        away_pitcher = game['away_probable_pitcher']
        home_pitcher = game['home_probable_pitcher']

        # Get run differentials
        away_team_run_diff = int(df_run_diff[df_run_diff.team == away_team]['l5_run_diff'].sum())
        home_team_run_diff = int(df_run_diff[df_run_diff.team == home_team]['l5_run_diff'].sum())

        # Calculate run differential for this matchup
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

        # Determine favorite and dog
        if away_team_run_diff > home_team_run_diff:
            favorite = away_team
            dog = home_team
        elif home_team_run_diff > away_team_run_diff:
            favorite = home_team
            dog = away_team
        else:
            favorite = 'EVEN'
            dog = 'EVEN'

        # Calculate model moneyline
        if home_team in al_teams:
            moneyline = round(((al_cents_per_run * run_diff_one_game) * 100) + 100, 0)
        else:
            moneyline = round(((nl_cents_per_run * run_diff_one_game) * 100) + 100, 0)

        # Get DraftKings odds
        fav_odds_dk = todays_odds[todays_odds.team == favorite]['odds'].sum()
        dog_odds_dk = todays_odds[todays_odds.team == dog]['odds'].sum()

        # Calculate odds gap
        if dog_odds_dk <= 0:
            dog_ml_gap = 0
        else:
            dog_ml_gap = dog_odds_dk - moneyline

        data_todays_games = [
            date, home_team, away_team, home_pitcher, away_pitcher,
            home_team_run_diff, away_team_run_diff, favorite, dog,
            moneyline, fav_odds_dk, dog_odds_dk, dog_ml_gap
        ]
        df_todays_games.loc[len(df_todays_games)] = data_todays_games

    return df_todays_games


def get_good_plays(block_list=['Colorado Rockies', 'Chicago White Sox']):
    """Main function to get today's good plays for MLB betting."""
    # Get historical data and calculate run differentials
    historical_df = get_historical_data()
    df_run_diff = calculate_team_run_differentials(historical_df)

    # Get DraftKings odds
    odds_df = get_draftkings_odds_df()

    # Get EST date
    EST_DATE = datetime.now().astimezone(tz.gettz('America/New_York')).date()
    todays_odds = odds_df[odds_df.date == EST_DATE]

    # Analyze today's games
    df_todays_games = analyze_todays_games(df_run_diff, odds_df)

    # Filter to good plays
    todays_eligible_games = df_todays_games[~df_todays_games['dog'].isin(block_list)]

    # Official plays are where DK odds are +10pts higher than model, and DK odds loss than +200
    todays_picks = todays_eligible_games[(todays_eligible_games['dog_odds_gap'] > 10) & (todays_eligible_games['dog_ml_dk'] < 200)]

    #TESTING LOGGING MODEL FAVORITES / DK UNDERDOGS
    todays_eligible_favs = df_todays_games[~df_todays_games['favorite'].isin(block_list)]
    test_log_favs = todays_eligible_favs[(todays_eligible_favs['dog_ml_dk'] < 0) & (todays_eligible_favs['fav_ml_dk'] > 0)]

    return todays_picks, test_log_favs


def run_predictions():
    """Function to run predictions and return good plays."""
    todays_picks, test_log_favs = get_good_plays()
    return todays_picks, test_log_favs


if __name__ == "__main__":
    run_predictions()