import contextlib
import io

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from models import FileSy, db

file_sies_bp = Blueprint("file_sies", __name__)


def _run_python_snippet(code: str) -> str:
    """Execute a python snippet and capture stdout.

    NOTE: This is an eval-sandbox equivalent to the original Ruby app's Thor
    task that ran user-supplied Ruby code. It is intentionally limited to
    authenticated users. Don't expose this endpoint publicly.
    """
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            exec(code, {"__builtins__": __builtins__}, {})
        return buf.getvalue()
    except Exception as exc:  # noqa: BLE001
        return f"{buf.getvalue()}\n[error] {exc!r}"


@file_sies_bp.route("/")
@login_required
def index():
    items = FileSy.query.order_by(FileSy.id.desc()).all()
    return render_template("file_sies/index.html", file_sies=items)


@file_sies_bp.route("/new")
@login_required
def new():
    return render_template("file_sies/new.html", file_sy=None)


@file_sies_bp.route("/", methods=["POST"])
@login_required
def create():
    f = FileSy(content=request.form.get("content"))
    db.session.add(f)
    db.session.commit()
    flash("File sy was successfully created.", "notice")
    return redirect(url_for("file_sies.show", fid=f.id))


@file_sies_bp.route("/<int:fid>")
@login_required
def show(fid: int):
    f = FileSy.query.get_or_404(fid)
    result = _run_python_snippet(f.content or "")
    f.result = result
    db.session.commit()
    return render_template("file_sies/show.html", file_sy=f, result=result)


@file_sies_bp.route("/<int:fid>/edit")
@login_required
def edit(fid: int):
    f = FileSy.query.get_or_404(fid)
    return render_template("file_sies/edit.html", file_sy=f)


@file_sies_bp.route("/<int:fid>", methods=["POST"])
@login_required
def update(fid: int):
    f = FileSy.query.get_or_404(fid)
    method_override = request.form.get("_method", "").upper()
    if method_override == "DELETE":
        db.session.delete(f)
        db.session.commit()
        flash("File sy was successfully destroyed.", "notice")
        return redirect(url_for("file_sies.index"))

    f.content = request.form.get("content")
    db.session.commit()
    flash("File sy was successfully updated.", "notice")
    return redirect(url_for("file_sies.show", fid=f.id))


@file_sies_bp.route("/<int:fid>/delete", methods=["POST", "GET"])
@login_required
def destroy(fid: int):
    f = FileSy.query.get_or_404(fid)
    db.session.delete(f)
    db.session.commit()
    flash("File sy was successfully destroyed.", "notice")
    return redirect(url_for("file_sies.index"))
