import gspread
import json
import os
from last_five_games import run_predictions
from oauth2client.service_account import ServiceAccountCredentials

# Set the scope for API access
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]

# Load credentials from GitHub Secrets (in Actions)
json_creds = os.getenv("GOOGLE_SHEETS_CREDENTIALS")

if json_creds:
    creds_dict = json.loads(json_creds)  # Convert JSON string to dict
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict)
else:
    raise ValueError("GOOGLE_SHEETS_CREDENTIALS environment variable not found!")

# Authenticate and open the Google Sheets document
client = gspread.authorize(creds)

# Open the Google Sheet (use the sheet's name or URL)
spreadsheet = client.open("MLB Underdog ML Betting")  # Name of the Google Sheet
log_sheet = spreadsheet.worksheet("daily_predictions")

def append_unique_df_to_sheet(df, sheet):
    # Convert DataFrame to list of lists
    df = df.astype(str)  # Convert all data to string format to prevent mismatches
    new_rows = df.values.tolist()  # Convert DataFrame to a list of lists

    # Fetch existing sheet data
    existing_values = sheet.get_all_values()  # List of lists
    existing_rows = {tuple(row) for row in existing_values}  # Convert to a set of tuples

    # Filter out duplicates
    unique_rows = [row for row in new_rows if tuple(row) not in existing_rows]

    # Append only unique rows
    if unique_rows:
        sheet.append_rows(unique_rows, value_input_option="USER_ENTERED")

todays_preds = run_predictions()
print(todays_preds)

append_unique_df_to_sheet(todays_preds, log_sheet)
