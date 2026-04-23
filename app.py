from flask import Flask, redirect, url_for
from flask_login import LoginManager

from config import Config
from models import User, db
from routes.auth import auth_bp
from routes.file_sies import file_sies_bp
from routes.home import home_bp
from routes.navs import navs_bp
from routes.pasts import pasts_bp
from utils import markdown_filter


def create_app() -> Flask:
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config.from_object(Config)

    db.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = "auth.login"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id: str):
        return db.session.get(User, int(user_id))

    app.jinja_env.filters["markdown"] = markdown_filter

    app.register_blueprint(home_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(pasts_bp, url_prefix="/pasts")
    app.register_blueprint(navs_bp, url_prefix="/pasts/<int:past_id>/navs")
    app.register_blueprint(file_sies_bp, url_prefix="/file_sies")

    @app.route("/past_<int:past_id>_navs.gv")
    def nav_gv(past_id: int):
        from flask import send_from_directory

        return send_from_directory(
            Config.PUBLIC_DIR, f"past_{past_id}_navs.gv", mimetype="text/plain"
        )

    @app.errorhandler(404)
    def not_found(_e):
        return redirect(url_for("home.index"))

    return app


if __name__ == "__main__":
    import os

    app = create_app()
    with app.app_context():
        db.create_all()
        os.makedirs(Config.PUBLIC_DIR, exist_ok=True)
    app.run(host="0.0.0.0", port=3002, debug=True)
