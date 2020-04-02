from __future__ import print_function
import pickle
import os.path
from redis_client import redis, redis_key
from oauth2client.client import OAuth2WebServerFlow
from googleapiclient.discovery import build

# If modifying these scopes, delete the file token.pickle.
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

flow = OAuth2WebServerFlow(
    client_id=os.environ["GOOGLE_CLIENT_ID"],
    client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
    scope=SCOPES,
    redirect_uri="urn:ietf:wg:oauth:2.0:oob",
)


def initiate_login():
    return flow.step1_get_authorize_url()


def complete_login(code):
    creds = flow.step2_exchange(code)

    # Save the credentials for the next run
    pickled = pickle.dumps(creds)
    redis.set(redis_key("token"), pickled)


def get_sheets_service():
    creds = None
    token = redis.get(redis_key("token"))
    if token:
        creds = pickle.loads(token)
    if not creds:
        raise Exception("Could not log in")
    return build("sheets", "v4", credentials=creds)


if __name__ == "__main__":
    get_sheets_service()
