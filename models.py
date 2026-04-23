from datetime import datetime

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash


db = SQLAlchemy()


class TimestampMixin:
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class User(db.Model, UserMixin, TimestampMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    encrypted_password = db.Column(db.String(255), nullable=False, default="")
    sign_in_count = db.Column(db.Integer, nullable=False, default=0)
    current_sign_in_at = db.Column(db.DateTime)
    last_sign_in_at = db.Column(db.DateTime)
    current_sign_in_ip = db.Column(db.String(64))
    last_sign_in_ip = db.Column(db.String(64))

    def set_password(self, password: str) -> None:
        self.encrypted_password = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        if not self.encrypted_password:
            return False
        return check_password_hash(self.encrypted_password, password)


class Past(db.Model, TimestampMixin):
    __tablename__ = "pasts"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    content = db.Column(db.Text)

    navs = db.relationship(
        "Nav", backref="past", cascade="all, delete-orphan", lazy="dynamic"
    )


class Nav(db.Model, TimestampMixin):
    __tablename__ = "navs"

    id = db.Column(db.Integer, primary_key=True)
    parid = db.Column(db.Integer, default=0)
    name = db.Column(db.String(255))
    content = db.Column(db.Text)
    past_id = db.Column(
        db.Integer, db.ForeignKey("pasts.id", ondelete="CASCADE"), index=True
    )


class Activation(db.Model, TimestampMixin):
    __tablename__ = "activations"

    id = db.Column(db.Integer, primary_key=True)
    past_id = db.Column(db.Integer, index=True)
    parid = db.Column(db.Integer)


class FileSy(db.Model, TimestampMixin):
    __tablename__ = "file_sies"

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text)
    result = db.Column(db.Text)
