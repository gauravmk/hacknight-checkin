import slack
import os

client = slack.WebClient(token=os.environ["SLACK_API_TOKEN"])


def get_user_name(user_id):
    return client.users_profile_get(user=user_id).get("profile")["real_name"]
