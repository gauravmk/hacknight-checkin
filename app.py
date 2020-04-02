from flask import (
    Flask,
    render_template,
    request,
)
from flask_bootstrap import Bootstrap
from threading import Thread
import google_client
import redis_client
import os

app = Flask(__name__)
Bootstrap(app)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "local")


@app.route("/finish_event")
def finish_event():
    current_event = redis_client.get_current_event()
    if not current_event:
        return render_template("no_event.html")
    # Do in a separate thread since saving is potentially slow
    Thread(target=async_finish_event).start()
    return "Saving..."


def async_finish_event():
    google_client.save_to_google_sheets()
    redis_client.clear_current_event()


@app.route("/oauth")
    slack_client.oauth(request.args["code"])
    return "Authed!"

@app.route("/slack", methods=["POST"])
def slack():
    if request.form["token"] != os.environ.get("SLACK_VERIFICATION_TOKEN"):
        raise Exception("unauthenticated")

    current_event = redis_client.get_current_event()
    if not current_event:
        return "There is no event to check in to"

    redis_client.add_checked_in_user(request.form["user_id"])
    return "You are checked in"
