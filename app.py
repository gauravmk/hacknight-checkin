from dotenv import load_dotenv

load_dotenv()

from flask import (
    Flask,
    render_template,
    redirect,
    request,
    session,
    jsonify,
)
from flask_bootstrap import Bootstrap
from apscheduler.schedulers.background import BackgroundScheduler
from threading import Thread
import google_client
import redis_client
import slack_client
import os


app = Flask(__name__)
Bootstrap(app)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "local")


@app.route("/oauth")
def oauth():
    team = slack_client.finish_oauth_and_return_team(request.args["code"])
    session["team"] = team
    return redirect("/google-login")


@app.route("/google-login")
def login():
    return render_template("login.html")


@app.route("/save-google-login", methods=["POST"])
def save_login():
    payload = request.get_json()
    google_client.complete_login(session["team"], payload["code"])
    # Create the attendance google sheet in a background thread
    Thread(
        target=google_client.create_initial_google_sheet, args=(session["team"],),
    ).start()
    return jsonify({"success": True})


@app.route("/slack-command", methods=["POST"])
def slack_command():
    if request.form["token"] != os.environ.get("SLACK_VERIFICATION_TOKEN"):
        raise Exception("unauthenticated")

    redis_client.add_checked_in_user(request.form["team_id"], request.form["user_id"])
    return "You are checked in"


def sync_attendance_to_google_sheets():
    # Find all teams
    teams = redis_client.get_teams_to_sync()
    print(f"Syncing {len(teams)} teams")
    [google_client.sync_team_to_google_sheets(t) for t in teams]

scheduler = BackgroundScheduler()
scheduler.add_job(
    sync_attendance_to_google_sheets, "interval", minutes=2, id="save_job"
)
scheduler.start()
