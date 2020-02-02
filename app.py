from flask import (
    Flask,
    render_template,
    make_response,
    request,
    redirect,
    url_for,
    jsonify,
)
from flask_httpauth import HTTPBasicAuth
from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import Email, DataRequired
import google_client
import redis_client
import os

app = Flask(__name__)
Bootstrap(app)
auth = HTTPBasicAuth()
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "local")


class CheckinForm(FlaskForm):
    email = StringField(validators=[DataRequired(), Email()])
    submit = SubmitField("Check in")


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
    # Get checked in users
    current_event = redis_client.get_current_event()
    if not current_event:
        return render_template("no_event.html")
    google_client.save_to_google_sheets()
    return "Done"


@app.route("/", methods=["GET", "POST"])
def index():
    current_event = redis_client.get_current_event()
    if not current_event:
        return render_template("no_event.html")

    form = CheckinForm(email=request.cookies.get("user_email"))
    if form.validate_on_submit():
        email = form.email.data
        redis_client.add_checked_in_user(email)

        # Send response back while setting cookie
        resp = make_response(render_template("checked_in.html"))
        resp.set_cookie("user_email", email)
        return resp
    return render_template("check_in.html", form=form)
