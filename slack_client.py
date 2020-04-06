import slack
import os

client = slack.WebClient(token=os.environ["SLACK_API_TOKEN"])


def get_user_name(user_id):
    return client.users_profile_get(user=user_id).get("profile")["real_name"]


def oauth(code):
    token = slack.WebClient().oauth_access(
        client_id=os.environ["SLACK_CLIENT_ID"],
        client_secret=os.environ["SLACK_CLIENT_SECRET"],
        code=code,
    )["access_token"]

    resp = slack.WebClient(token=token).auth_test()
    # store the auth token
    print(resp)
