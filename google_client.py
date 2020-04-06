from google_auth import get_sheets_service
import string
import os
import redis_client
import slack_client

SPREADSHEET_ID = os.environ["SPREADSHEET_ID"]


def save_to_google_sheets():
    checked_in_users = redis_client.get_checked_in_user()
    event_key = redis_client.get_event_key()

    # Pull down header row from sheets
    header_result = (
        get_sheets_service()
        .spreadsheets()
        .values()
        .batchGet(spreadsheetId=SPREADSHEET_ID, ranges=["1:1"])
        .execute()
    )

    # We want to identify which columns the following things are in
    # - Slack User ID
    # - Name
    # - Current Event
    headers = header_result["valueRanges"][0]["values"][0]

    slack_id_index = get_letter_index(headers.index("Slack User ID"))
    name_index = get_letter_index(headers.index("Name"))
    event_index = get_letter_index(
        headers.index(event_key) if event_key in headers else len(headers)
    )

    # Pull down user columns from sheets
    user_col_results = (
        get_sheets_service()
        .spreadsheets()
        .values()
        .batchGet(
            spreadsheetId=SPREADSHEET_ID,
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
            user_names.append(slack_client.get_user_name(user))

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
        get_sheets_service()
        .spreadsheets()
        .values()
        .batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body={
                "value_input_option": "RAW",
                "data": [user_id_req_data, user_name_req_data, checkin_req_data],
            },
        )
        .execute()
    )


# Bit of magic that converts a numeric index into an alphabetical equivalent.
# This is because google sheets numbers the columns with letters A, B... Z, AA, AB.., etc
def get_letter_index(idx):
    output_str = ""

    # It's basically a modified base26 conversion.
    while idx >= 26:
        output_str = string.ascii_uppercase[idx % 26] + output_str
        idx = int(idx / 26) - 1
    output_str = string.ascii_uppercase[idx % 26] + output_str

    return output_str
