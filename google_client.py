from oauth2client import client
from googleapiclient.discovery import build
import pickle
import string
import os
import redis_client
import slack_client

SCOPES = ["https://www.googleapis.com/auth/drive.file"]


def complete_login(team_id, code):
    creds = client.credentials_from_code(
        client_id=os.environ["GOOGLE_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        scope=SCOPES,
        code=code,
    )

    # Save the credentials for the next run
    pickled = pickle.dumps(creds)
    redis_client.save(team_id, "google_token", pickled)


def create_initial_google_sheet(team_id):
    sheets_service = _get_sheets_service(team_id)

    # Create the spreadsheet
    spreadsheet = (
        sheets_service.spreadsheets()
        .create(body={"properties": {"title": "Hack Night Attendance"}})
        .execute()
    )

    # Store spreadsheet ID
    spreadsheet_id = spreadsheet["spreadsheetId"]
    spreadsheet_url = spreadsheet["spreadsheetUrl"]
    sheet_id = spreadsheet["sheets"][0]["properties"]["sheetId"]

    redis_client.save(team_id, "spreadsheet_id", spreadsheet_id)

    # Format the spreadsheet
    requests = []

    # Set frozen rows / columns
    requests.append(
        {
            "updateSheetProperties": {
                "properties": {
                    "sheetId": sheet_id,
                    "title": "Attendance",
                    "gridProperties": {"frozenRowCount": 1, "frozenColumnCount": 2},
                },
                "fields": "title,gridProperties.frozenRowCount,gridProperties.frozenColumnCount",
            }
        }
    )

    # Bold the header
    requests.append(
        {
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1},
                "cell": {
                    "userEnteredFormat": {"textFormat": {"fontSize": 12, "bold": True}}
                },
                "fields": "userEnteredFormat(textFormat)",
            }
        }
    )

    # Setup protected ranges
    protected_ranges = [
        {
            "range": {"sheetId": sheet_id, "startColumnIndex": 0, "endColumnIndex": 1},
            "description": "Editing the slack User ID column could break the integration",
            "warningOnly": True,
        },
        {
            "range": {"sheetId": sheet_id, "startColumnIndex": 1, "endColumnIndex": 2},
            "description": "Editing user names won't break the integration but make sure you know what you're doing",
            "warningOnly": True,
        },
        {
            "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1},
            "description": "Editing the headers could break the integration. As long as there is some column named 'Slack User ID' and another named 'Name', the sync will work",
            "warningOnly": True,
        },
    ]
    requests += [{"addProtectedRange": {"protectedRange": r}} for r in protected_ranges]

    # Hide the slack user id column
    requests.append(
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": 0,
                    "endIndex": 1,
                },
                "properties": {"hiddenByUser": True},
                "fields": "hiddenByUser",
            }
        }
    )

    # Add a formatting rule so attendance shows up as green
    requests.append(
        {
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [
                        {"sheetId": sheet_id, "startRowIndex": 1, "startColumnIndex": 2}
                    ],
                    "booleanRule": {
                        "condition": {"type": "NOT_BLANK"},
                        "format": {
                            "backgroundColor": {
                                "red": 0.773,
                                "green": 0.933,
                                "blue": 0.804,
                            }
                        },
                    },
                },
                "index": 0,
            }
        }
    )

    # Batch run all the update requests
    sheets_service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id, body={"requests": requests}
    ).execute()

    # Setup initial header: (Slack User Id, Name)
    sheets_service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range="A1:B1",
        valueInputOption="RAW",
        body={"values": [["Slack User ID", "Name"]]},
    ).execute()

    # Alert the user that installed the app that we're all set up.
    slack_client.send_final_onboarding_message(team_id, spreadsheet_url)


def sync_team_to_google_sheets(team_id):
    sheets_service = _get_sheets_service(team_id)
    checked_in_users = redis_client.get_checked_in_user(team_id)
    event_key = redis_client.get_event_key()
    spreadsheet_id = redis_client.retrieve(team_id, "spreadsheet_id").decode()

    # Pull down header row from sheets
    header_result = (
        sheets_service.spreadsheets()
        .values()
        .batchGet(spreadsheetId=spreadsheet_id, ranges=["1:1"])
        .execute()
    )

    # We want to identify which columns the following things are in
    # - Slack User ID
    # - Name
    # - Current Event
    headers = header_result["valueRanges"][0]["values"][0]

    slack_id_index = _get_letter_index(headers.index("Slack User ID"))
    name_index = _get_letter_index(headers.index("Name"))
    event_index = _get_letter_index(
        headers.index(event_key) if event_key in headers else len(headers)
    )

    # Pull down user columns from sheets
    user_col_results = (
        sheets_service.spreadsheets()
        .values()
        .batchGet(
            spreadsheetId=spreadsheet_id,
            ranges=[f"{slack_id_index}:{slack_id_index}", f"{name_index}:{name_index}"],
            majorDimension="COLUMNS",
        )
        .execute()
    )

    # These are parallel arrays. As in, the nth user in both arrays are the same user
    user_ids = user_col_results["valueRanges"][0]["values"][0][1:]
    user_names = user_col_results["valueRanges"][1]["values"][0][1:]

    # Add in any never before seen members to the user col list
    for user in checked_in_users:
        if user not in user_ids:
            user_ids.append(user)
            user_names.append(slack_client.get_user_name(team_id, user))

    # checkin_col is another parallel array with the first two and stores whether
    # each user was present at the last event
    checkin_col = []
    for user in user_ids:
        if user in checked_in_users:
            checkin_col.append("y")
        else:
            checkin_col.append("")

    # Write back to google sheets
    #
    # We want to write back 3 ranges (each range is a column)
    # 1. The user ids with any new users we picked up
    # 2. The user names with any new users we picked up
    # 3. The checkins for all users

    user_id_req_data = {
        "range": f"{slack_id_index}2:{slack_id_index}",
        "majorDimension": "COLUMNS",
        "values": [user_ids],
    }

    user_name_req_data = {
        "range": f"{name_index}2:{name_index}",
        "majorDimension": "COLUMNS",
        "values": [user_names],
    }

    checkin_req_data = {
        "range": f"{event_index}:{event_index}",
        "majorDimension": "COLUMNS",
        "values": [[event_key, *checkin_col]],
    }

    (
        sheets_service.spreadsheets()
        .values()
        .batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={
                "value_input_option": "RAW",
                "data": [user_id_req_data, user_name_req_data, checkin_req_data],
            },
        )
        .execute()
    )


# Bit of magic that converts a numeric index into an alphabetical equivalent.
# This is because google sheets numbers the columns with letters A, B... Z, AA, AB.., etc
def _get_letter_index(idx):
    output_str = ""

    # It's basically a modified base26 conversion.
    while idx >= 0:
        output_str = string.ascii_uppercase[idx % 26] + output_str
        idx = int(idx / 26) - 1

    return output_str


def _get_sheets_service(team_id):
    creds = None
    token = redis_client.retrieve(team_id, "google_token")
    if token:
        creds = pickle.loads(token)
    if not creds:
        raise Exception("Could not log in")
    return build("sheets", "v4", credentials=creds)
