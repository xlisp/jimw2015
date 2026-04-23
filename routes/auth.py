from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from models import User, db

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("home.index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            user.sign_in_count = (user.sign_in_count or 0) + 1
            user.last_sign_in_at = user.current_sign_in_at
            user.current_sign_in_at = datetime.utcnow()
            user.last_sign_in_ip = user.current_sign_in_ip
            user.current_sign_in_ip = request.remote_addr
            db.session.commit()
            login_user(user, remember=True)
            return redirect(url_for("home.index"))
        flash("ACCESS DENIED :: invalid credentials", "error")

    return render_template("auth/login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("home.index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("password_confirmation", "")

        if not email or not password:
            flash("email and password required", "error")
        elif password != confirm:
            flash("passwords do not match", "error")
        elif User.query.filter_by(email=email).first():
            flash("email already registered", "error")
        else:
            user = User(email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            return redirect(url_for("home.index"))

    return render_template("auth/register.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
