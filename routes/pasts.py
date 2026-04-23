from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from models import Nav, Past, db

pasts_bp = Blueprint("pasts", __name__)


@pasts_bp.route("/")
@login_required
def index():
    pasts = Past.query.order_by(Past.updated_at.desc()).all()
    items = []
    for p in pasts:
        first = (
            Nav.query.filter_by(past_id=p.id, parid=0)
            .order_by(Nav.id.asc())
            .first()
        )
        items.append((p, first.id if first else None))
    return render_template("pasts/index.html", items=items)


@pasts_bp.route("/new", methods=["GET"])
@login_required
def new():
    return render_template("pasts/new.html", past=None)


@pasts_bp.route("/", methods=["POST"])
@login_required
def create():
    past = Past(
        name=request.form.get("name"),
        content=request.form.get("content"),
    )
    db.session.add(past)
    db.session.commit()

    nav = Nav(
        content="=====这里是分割线=====",
        past_id=past.id,
        parid=0,
    )
    db.session.add(nav)
    db.session.commit()

    flash("Past and BoundaryLine was successfully created.", "notice")
    return redirect(url_for("navs.index", past_id=past.id))


@pasts_bp.route("/<int:past_id>", methods=["GET"])
@login_required
def show(past_id: int):
    past = Past.query.get_or_404(past_id)
    return render_template("pasts/show.html", past=past)


@pasts_bp.route("/<int:past_id>/edit", methods=["GET"])
@login_required
def edit(past_id: int):
    past = Past.query.get_or_404(past_id)
    return render_template("pasts/edit.html", past=past)


@pasts_bp.route("/<int:past_id>", methods=["POST"])
@login_required
def update(past_id: int):
    past = Past.query.get_or_404(past_id)
    method_override = request.form.get("_method", "").upper()
    if method_override == "DELETE":
        db.session.delete(past)
        db.session.commit()
        flash("Past was successfully destroyed.", "notice")
        return redirect(url_for("pasts.index"))

    past.name = request.form.get("name")
    past.content = request.form.get("content")
    db.session.commit()
    flash("Past was successfully updated.", "notice")
    return redirect(url_for("pasts.show", past_id=past.id))


@pasts_bp.route("/<int:past_id>/delete", methods=["POST", "GET"])
@login_required
def destroy(past_id: int):
    past = Past.query.get_or_404(past_id)
    db.session.delete(past)
    db.session.commit()
    flash("Past was successfully destroyed.", "notice")
    return redirect(url_for("pasts.index"))
