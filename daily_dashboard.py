from datetime import datetime, timedelta
from dateutil import parser
from dateutil import tz
import statsapi
import pandas as pd
import requests
import json
import numpy as np
from flask import Flask, render_template


def get_historical_data(days_back=15):  # Get more days to ensure we have enough games for each team
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


def get_team_last_games(historical_df, team_name, num_games=5):
    """Get the last n games for a specific team."""
    # Get team's games where they were either home or away
    team_away_games = historical_df[historical_df.away_team == team_name].copy()
    team_home_games = historical_df[historical_df.home_team == team_name].copy()

    # Add result and opponent columns for away games
    team_away_games['opponent'] = team_away_games['home_team']
    team_away_games['is_away'] = True
    team_away_games['team_score'] = team_away_games['away_score']
    team_away_games['opp_score'] = team_away_games['home_score']
    team_away_games['result'] = team_away_games.apply(
        lambda row: f"W ({row['away_score']}-{row['home_score']})" if row['away_score'] > row['home_score']
        else f"L ({row['away_score']}-{row['home_score']})", axis=1
    )

    # Add result and opponent columns for home games
    team_home_games['opponent'] = team_home_games['away_team']
    team_home_games['is_away'] = False
    team_home_games['team_score'] = team_home_games['home_score']
    team_home_games['opp_score'] = team_home_games['away_score']
    team_home_games['result'] = team_home_games.apply(
        lambda row: f"W ({row['home_score']}-{row['away_score']})" if row['home_score'] > row['away_score']
        else f"L ({row['home_score']}-{row['away_score']})", axis=1
    )

    # Combine home and away games
    all_games = pd.concat([team_away_games, team_home_games])

    # Sort by date (newest first) and get last n games
    all_games['date'] = pd.to_datetime(all_games['date'])
    last_games = all_games.sort_values(by='date', ascending=False).head(num_games)

    # Format date as MM/DD
    last_games['formatted_date'] = last_games['date'].dt.strftime('%m/%d')

    # Format opponent with @ for away games
    last_games['formatted_opponent'] = last_games.apply(
        lambda row: f"@ {row['opponent']}" if row['is_away'] else row['opponent'], axis=1
    )

    # Create result list (newest to oldest) - Convert to native Python types
    game_results = last_games[['formatted_date', 'formatted_opponent', 'result']].to_dict('records')

    return game_results


def calculate_team_run_differentials(historical_df, num_games=5):
    """Calculate run differentials for each team over their last n games."""
    # Get all teams
    get_teams = statsapi.lookup_team('')
    teams = [team['name'] for team in get_teams]

    # Calculate run differentials
    columns_run_diff = ['team', 'run_diff']
    df_run_diff = pd.DataFrame(columns=columns_run_diff)

    for team in teams:
        # Build dataframe of team's last n games
        team_away_games = historical_df[historical_df.away_team == team]
        team_home_games = historical_df[historical_df.home_team == team]
        all_team_games = [team_home_games, team_away_games]
        team_games = pd.concat(all_team_games).sort_values(by='date', ascending=True).tail(num_games)

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
        data_run_diff = [str(team), int(team_run_differential)]
        df_run_diff.loc[len(df_run_diff)] = data_run_diff

    return df_run_diff


def get_draftkings_odds_df():
    """Get moneylines from DraftKings API and convert to dataframe."""
    API_KEY = '7f908dfa6f555a6f509f958b2353ce65'
    SPORT = 'baseball_mlb'
    REGIONS = 'us'
    MARKETS = 'h2h'
    ODDS_FORMAT = 'american'
    DATE_FORMAT = 'iso'
    BOOKMAKER = 'draftkings'

    # Get odds from API
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
    print(odds_response)

    # Create an empty DataFrame in case of errors
    columns = ['date', 'team', 'odds']
    odds_df = pd.DataFrame(columns=columns)

    # Only proceed if we got a valid response
    if odds_response.status_code != 200:
        print(f"Error fetching odds: Status code {odds_response.status_code}")
        return odds_df

    try:
        odds_json = odds_response.json()
        print(odds_json)

        for game in odds_json:
            print(game)
            try:
                start_time = parser.parse(game['commence_time'])
                date = start_time.astimezone(tz.gettz('America/New_York')).date()

                # Error handling for accessing bookmakers and markets
                if ('bookmakers' not in game or
                        len(game['bookmakers']) == 0 or
                        'markets' not in game['bookmakers'][0] or
                        len(game['bookmakers'][0]['markets']) == 0 or
                        'outcomes' not in game['bookmakers'][0]['markets'][0]):
                    print(f"No odds data available for game: {game.get('id', 'unknown')}")
                    continue

                odds = game['bookmakers'][0]['markets'][0]['outcomes']
                for i in odds:
                    team = i['name']
                    odds_value = i['price']
                    data = [date, team, odds_value]
                    odds_df.loc[len(odds_df)] = data

            except Exception as e:
                print(f"Error processing game {game.get('id', 'unknown')}: {str(e)}")
                continue

    except Exception as e:
        print(f"Error processing odds response: {str(e)}")

    return odds_df


def calculate_moneyline_for_game(home_team, away_team, home_team_run_diff, away_team_run_diff):
    """Calculate moneyline for a specific game."""
    # League constants
    al_teams = [
        'Oakland Athletics', 'Seattle Mariners', 'Texas Rangers', 'Tampa Bay Rays',
        'Toronto Blue Jays', 'Minnesota Twins', 'Chicago White Sox', 'New York Yankees',
        'Los Angeles Angels', 'Baltimore Orioles', 'Boston Red Sox', 'Cleveland Guardians',
        'Detroit Tigers', 'Houston Astros', 'Kansas City Royals'
    ]
    al_cents_per_run = 1 / 4.2742998353
    nl_cents_per_run = 1 / 4.512345679

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

    return {
        'favorite': favorite,
        'dog': dog,
        'dog_ml': int(moneyline),
        'fav_ml': int(-moneyline)
    }


def get_todays_games():
    """Get today's games from StatsAPI."""
    EST_DATE = datetime.now().astimezone(tz.gettz('America/New_York')).date()
    games = statsapi.schedule(start_date=EST_DATE, end_date=EST_DATE)

    # Filter for upcoming games only (exclude in-progress or completed)
    upcoming_games = []
    for game in games:
        # Check if game is still scheduled (not started or completed)
        if game['status'] == 'Scheduled' or game['status'] == 'Pre-Game':
            upcoming_games.append(game)

    return upcoming_games


def generate_game_data_for_ranges(historical_df, odds_df):
    """Generate prediction data for each game using 3-10 games of historical data."""
    # Get today's upcoming games
    games_today = get_todays_games()

    # Create results container
    game_results = []

    # For each game today
    for game in games_today:
        away_team = game['away_name']
        home_team = game['home_name']
        away_pitcher = game['away_probable_pitcher']
        home_pitcher = game['home_probable_pitcher']
        game_time = parser.parse(game['game_datetime']).astimezone(tz.gettz('America/New_York')).strftime('%I:%M %p')

        # Get DraftKings odds for specific teams
        try:
            away_team_odds = odds_df[odds_df.team == away_team]['odds'].values[0] if not odds_df[
                odds_df.team == away_team].empty else None
            home_team_odds = odds_df[odds_df.team == home_team]['odds'].values[0] if not odds_df[
                odds_df.team == home_team].empty else None

            # Convert NumPy types to native Python types
            if isinstance(away_team_odds, np.integer):
                away_team_odds = int(away_team_odds)
            if isinstance(home_team_odds, np.integer):
                home_team_odds = int(home_team_odds)
        except (IndexError, KeyError):
            away_team_odds = None
            home_team_odds = None

        # Get last 5 games for each team
        away_team_last_games = get_team_last_games(historical_df, away_team)
        home_team_last_games = get_team_last_games(historical_df, home_team)

        # Calculate moneyline for different game ranges
        range_data = []
        for num_games in range(3, 11):
            # Calculate run differentials using n games
            df_run_diff = calculate_team_run_differentials(historical_df, num_games)

            # Get run differentials for both teams - convert to native Python int
            away_team_run_diff = int(df_run_diff[df_run_diff.team == away_team]['run_diff'].sum())
            home_team_run_diff = int(df_run_diff[df_run_diff.team == home_team]['run_diff'].sum())

            # Calculate moneyline
            moneyline_data = calculate_moneyline_for_game(
                home_team, away_team, home_team_run_diff, away_team_run_diff
            )

            # Add to results - ensure all values are native Python types
            range_data.append({
                'num_games': int(num_games),
                'away_run_diff': int(away_team_run_diff),
                'home_run_diff': int(home_team_run_diff),
                'favorite': str(moneyline_data['favorite']),
                'dog': str(moneyline_data['dog']),
                'dog_ml': int(moneyline_data['dog_ml']),
                'fav_ml': int(moneyline_data['fav_ml'])
            })

        # Format odds for display with + sign for positive numbers
        formatted_away_odds = f"+{away_team_odds}" if away_team_odds and away_team_odds > 0 else away_team_odds
        formatted_home_odds = f"+{home_team_odds}" if home_team_odds and home_team_odds > 0 else home_team_odds

        # Add game info to results
        game_results.append({
            'home_team': str(home_team),
            'away_team': str(away_team),
            'home_pitcher': str(home_pitcher) if home_pitcher else "TBD",
            'away_pitcher': str(away_pitcher) if away_pitcher else "TBD",
            'game_time': str(game_time),
            'dk_home_odds': str(formatted_home_odds) if home_team_odds is not None else 'N/A',
            'dk_away_odds': str(formatted_away_odds) if away_team_odds is not None else 'N/A',
            'range_data': range_data,
            'away_team_last_games': away_team_last_games,
            'home_team_last_games': home_team_last_games
        })

    return game_results


# Flask app for the dashboard
app = Flask(__name__)


@app.route('/')
def dashboard():
    # Get historical data
    historical_df = get_historical_data()

    # Get DraftKings odds
    odds_df = get_draftkings_odds_df()

    # Generate data for all games at different ranges
    game_data = generate_game_data_for_ranges(historical_df, odds_df)

    # Convert to JSON for the frontend
    # Use a JSON encoder that can handle NumPy types
    class NumpyEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            return super(NumpyEncoder, self).default(obj)

    game_data_json = json.dumps(game_data, cls=NumpyEncoder)

    # Render the template
    return render_template('dashboard.html', game_data=game_data_json)


if __name__ == "__main__":
    # Run the Flask app
    print("Starting MLB Prediction Dashboard at http://127.0.0.1:5000")
    app.run(debug=True)