from __future__ import print_function
import pickle
import os.path
from redis_client import redis, redis_key
from oauth2client.client import OAuth2WebServerFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

# If modifying these scopes, delete the file token.pickle.
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def get_sheets_service():
    creds = None
    # we store the user's access and refresh tokens in redis and is added automatically
    # when the authorization flow completes for the first time.
    token = redis.get(redis_key("token"))
    if token:
        creds = pickle.loads(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = OAuth2WebServerFlow(
                client_id=os.environ["GOOGLE_CLIENT_ID"],
                client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
                scope=SCOPES,
                redirect_uri="urn:ietf:wg:oauth:2.0:oob",
            )
            auth_uri = flow.step1_get_authorize_url()
            print(auth_uri)
            code = input("code: ")
            creds = flow.step2_exchange(code)

        # Save the credentials for the next run
        pickled = pickle.dumps(creds)
        redis.set(redis_key("token"), pickled)

    return build("sheets", "v4", credentials=creds)


if __name__ == "__main__":
    get_sheets_service()
