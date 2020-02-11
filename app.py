from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    jsonify,
)
from flask_httpauth import HTTPBasicAuth
from flask_bootstrap import Bootstrap
from threading import Thread
import google_client
import redis_client
import os

app = Flask(__name__)
Bootstrap(app)
auth = HTTPBasicAuth()
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "local")


@auth.verify_password
def verify_password(username, password):
    admin_user = os.environ.get("ADMIN_USER", "admin")
    admin_pass = os.environ.get("ADMIN_PASS", "password")
    return username == admin_user and password == admin_pass


@app.route("/admin")
@auth.login_required
def admin():
    current_event = redis_client.get_current_event()
    if current_event:
        return render_template("finish_event.html", current_event=current_event)
    return render_template("create_event.html")


@app.route("/create_event")
@auth.login_required
def create_event():
    redis_client.set_current_event()
    return redirect(url_for("admin"))


@app.route("/poll_checkins")
@auth.login_required
def poll_checkins():
    return jsonify({"count": len(redis_client.get_checked_in_user())})


@app.route("/finish_event")
@auth.login_required
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


@app.route("/slack", methods=["POST"])
def slack():
    current_event = redis_client.get_current_event()
    if not current_event:
        return "There is no event to check in to"

    redis_client.add_checked_in_user(request.form["user_id"])
    return "You are checked in"
