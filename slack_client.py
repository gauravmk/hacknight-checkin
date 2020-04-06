import slack
import os
import redis_client


def get_user_name(team_id, user_id):
    return (
        _slack_client(team_id)
        .users_profile_get(user=user_id)
        .get("profile")["real_name"]
    )


def finish_oauth_and_return_team(code):
    resp = slack.WebClient().oauth_v2_access(
        client_id=os.environ["SLACK_CLIENT_ID"],
        client_secret=os.environ["SLACK_CLIENT_SECRET"],
        code=code,
    )

    token = resp["access_token"]
    team = resp["team"]["id"]
    user = resp["authed_user"]["id"]

    redis_client.save(team, "slack_token", token)
    redis_client.save(team, "admin_user", user)

    return team


def send_final_onboarding_message(team_id, spreadsheet_url):
    admin_user = redis_client.retrieve(team_id, "admin_user").decode()
    message = f"""
You're all done setting up Hack Night Check In. At your next hack night, just ask all attendees to type in `/checkin` into any channel in slack and they'll be good to go.

Checkins will sync to this google sheet automatically: {spreadsheet_url}. We sync every couple of minutes so you might have to wait a bit to see the results.

If you want to test it out right now, just type a `/checkin` right back at me. You should see your name show up in that spreadsheet within minutes.

The integration is fairly robust to changes to that sheet. Feel free to move the google sheet to whatever folder you'd like. I also find it useful to mark existing users in the sheet as present if I saw them show up but they forgot to mark themselves. If you do this on the same day as the hack night, the re-sync will currently overwrite it, so I'd wait till the next day for that.

Lastly, please add issues (or help contribute) here: https://github.com/gauravmk/hacknight-checkin. Thanks for trying it out!
"""

    _slack_client(team_id).chat_postMessage(channel=admin_user, text=message)


def _slack_client(team_id):
    return slack.WebClient(token=redis_client.retrieve(team_id, "slack_token").decode())
