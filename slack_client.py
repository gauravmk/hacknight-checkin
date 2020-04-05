import slack
import os
import redis_client


def get_user_name(team_id, user_id):
    return (
        _slack_client(team_id)
        .users_profile_get(user=user_id)
        .get("profile")["real_name"]
    )


def oauth_and_return_team(code):
    resp = slack.WebClient().oauth_v2_access(
        client_id=os.environ["SLACK_CLIENT_ID"],
        client_secret=os.environ["SLACK_CLIENT_SECRET"],
        code=code,
    )

    token = resp["access_token"]
    team = resp["team"]["id"]

    redis_client.save(team, "slack_token", token)

    return team


def _slack_client(team_id):
    return slack.WebClient(token=redis_client.retrieve(team_id, "slack_token").decode())
