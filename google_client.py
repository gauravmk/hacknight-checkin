from google_auth import get_sheets_service
import os
import redis_client

SPREADSHEET_ID = os.environ["SPREADSHEET_ID"]


def save_to_google_sheets():
    current_event = redis_client.get_current_event()
    checked_in_emails = redis_client.get_checked_in_user()

    # Pull down meta column from sheets
    meta_result = (
        get_sheets_service()
        .spreadsheets()
        .values()
        .batchGet(
            spreadsheetId=SPREADSHEET_ID, ranges=["B2:B3"], majorDimension="COLUMNS",
        )
        .execute()
    )

    next_empty_col_key, email_col_key = meta_result["valueRanges"][0]["values"][0]

    # Pull down email column from sheets
    email_col_result = (
        get_sheets_service()
        .spreadsheets()
        .values()
        .batchGet(
            spreadsheetId="1IEym6f_2h8qqoyMwTKFyDOnFNrcWTfK_EPwmyY-Rysg",
            ranges=[f"{email_col_key}2:{email_col_key}1000"],
            majorDimension="COLUMNS",
        )
        .execute()
    )

    email_col = email_col_result["valueRanges"][0]["values"][0]

    # Add in any never before seen members to the email col list
    for email in checked_in_emails:
        if email not in email_col:
            email_col.append(email)

    # checkin_col is a parallel array to email_col and stores whether
    # each user was present at the last event
    checkin_col = []
    for email in email_col:
        if email in checked_in_emails:
            checkin_col.append("y")
        else:
            checkin_col.append("")

    # Write back to google sheets
    #
    # There are three ranges we care about
    # 1. Update the email column (aka list of emails) to include new members
    # 2. Update the checkin column for the last event with whether each person came
    # 3. Update any metadata. For now that's incrementing the event column so that
    #    the next checkin will go in the next column.

    email_col_req_data = {
        "range": f"{email_col_key}2:{email_col_key}1000",
        "majorDimension": "COLUMNS",
        "values": [email_col],
    }

    event_title = f"{current_event['type']} {current_event['date'].format('M/D')}"
    checkin_col_req_data = {
        "range": f"{next_empty_col_key}1:{next_empty_col_key}1000",
        "majorDimension": "COLUMNS",
        "values": [[event_title, *checkin_col]],
    }

    meta_req_data = {
        "range": "B2:B2",
        "values": [[incr_google_col(next_empty_col_key)]],
    }

    (
        get_sheets_service()
        .spreadsheets()
        .values()
        .batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body={
                "value_input_option": "RAW",
                "data": [meta_req_data, email_col_req_data, checkin_col_req_data],
            },
        )
        .execute()
    )


# Bit of magic that incrememnts google sheet columns by 1.
# A -> B, G -> H, Z -> AA, AZ -> BA, etc.
def incr_google_col(col):
    if col == "":
        return "A"
    char = col[-1]
    if char == "Z":
        return incr_google_col(col[:-1]) + "A"
    return col[:-1] + (chr(ord(col[-1]) + 1))