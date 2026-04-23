import os
import random
from datetime import datetime

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import login_required
from sqlalchemy import and_

from models import Activation, Nav, Past, db

navs_bp = Blueprint("navs", __name__)


def _search_by_keys(query, keys: list[str]):
    for v in keys:
        query = query.filter(Nav.content.ilike(f"%{v}%"))
    return query


def _build_graph(past_id: int, root_id: int) -> list[str]:
    edges: list[str] = []
    children_cache: dict[int, list[Nav]] = {}

    def children(node_id: int) -> list[Nav]:
        if node_id not in children_cache:
            children_cache[node_id] = (
                Nav.query.filter_by(parid=node_id, past_id=past_id).all()
            )
        return children_cache[node_id]

    def walk(node_id: int):
        kids = children(node_id)
        for kid in kids:
            parent = db.session.get(Nav, kid.parid)
            parent_content = parent.content if parent else ""
            edges.append(
                f'"{(parent_content or "").replace(chr(34), "")}" -> '
                f'"{(kid.content or "").replace(chr(34), "")}"'
            )
            walk(kid.id)

    walk(root_id)
    return edges


@navs_bp.route("/", methods=["GET"])
@login_required
def index(past_id: int):
    past = Past.query.get_or_404(past_id)

    wd = request.args.get("wd", "").strip()
    keys = []
    if wd:
        keys = [k for k in wd.split() if k]
    else:
        for k, v in request.args.items():
            if k.startswith("q") and v:
                keys.append(v)

    q = Nav.query.filter_by(past_id=past_id)
    q = _search_by_keys(q, keys)
    navs = q.order_by(Nav.updated_at.desc()).all()

    nav_first = (
        Nav.query.filter_by(past_id=past_id).order_by(Nav.updated_at.desc()).first()
    )

    if nav_first:
        try:
            edges = _build_graph(past_id, nav_first.id)
            public_dir = current_app.config["PUBLIC_DIR"]
            os.makedirs(public_dir, exist_ok=True)
            with open(
                os.path.join(public_dir, f"past_{past_id}_navs.gv"),
                "w",
                encoding="utf-8",
            ) as f:
                f.write("digraph G {\n")
                for e in edges:
                    f.write(e + "\n")
                f.write("}\n")
        except Exception as exc:  # noqa: BLE001
            current_app.logger.warning("graph build failed: %s", exc)

    last_activation = (
        Activation.query.filter_by(past_id=past_id).order_by(Activation.id.desc()).first()
    )
    activation_id = last_activation.parid if last_activation else 0
    nav_part_root = db.session.get(Nav, activation_id) if activation_id else None

    # random indent widths per row, stable-ish per nav id
    indents = {n.id: int(random.random() * 100) for n in navs}

    return render_template(
        "navs/index.html",
        past=past,
        past_id=past_id,
        navs=navs,
        activation_id=activation_id,
        nav_part_root=nav_part_root,
        indents=indents,
    )


@navs_bp.route("/new", methods=["GET"])
@login_required
def new(past_id: int):
    return render_template("navs/new.html", past_id=past_id, nav=None, is_edit=False)


@navs_bp.route("/", methods=["POST"])
@login_required
def create(past_id: int):
    count = Nav.query.filter_by(past_id=past_id).count()
    parid_raw = request.form.get("parid") or 0
    try:
        parid = int(parid_raw)
    except (TypeError, ValueError):
        parid = 0
    if count < 1:
        parid = 0

    nav = Nav(
        parid=parid,
        name=request.form.get("name"),
        content=request.form.get("content"),
        past_id=past_id,
    )
    db.session.add(nav)
    db.session.commit()
    flash("Nav was successfully created.", "notice")
    return redirect(url_for("navs.index", past_id=past_id))


@navs_bp.route("/<int:nav_id>", methods=["GET"])
@login_required
def show(past_id: int, nav_id: int):
    nav = Nav.query.filter_by(id=nav_id, past_id=past_id).first_or_404()
    return render_template("navs/show.html", past_id=past_id, nav=nav)


@navs_bp.route("/<int:nav_id>/edit", methods=["GET"])
@login_required
def edit(past_id: int, nav_id: int):
    nav = Nav.query.filter_by(id=nav_id, past_id=past_id).first_or_404()
    return render_template("navs/edit.html", past_id=past_id, nav=nav, is_edit=True)


@navs_bp.route("/<int:nav_id>", methods=["POST"])
@login_required
def update(past_id: int, nav_id: int):
    nav = Nav.query.filter_by(id=nav_id, past_id=past_id).first_or_404()
    method_override = request.form.get("_method", "").upper()
    if method_override == "DELETE":
        db.session.delete(nav)
        db.session.commit()
        flash("Nav was successfully destroyed.", "notice")
        return redirect(url_for("navs.index", past_id=past_id))

    try:
        nav.parid = int(request.form.get("parid") or nav.parid)
    except (TypeError, ValueError):
        pass
    nav.name = request.form.get("name")
    nav.content = request.form.get("content")
    db.session.commit()
    flash("Nav was successfully updated.", "notice")
    return redirect(url_for("navs.show", past_id=past_id, nav_id=nav.id))


@navs_bp.route("/<int:nav_id>/delete", methods=["POST", "GET"])
@login_required
def destroy(past_id: int, nav_id: int):
    nav = Nav.query.filter_by(id=nav_id, past_id=past_id).first_or_404()
    db.session.delete(nav)
    db.session.commit()
    flash("Nav was successfully destroyed.", "notice")
    return redirect(url_for("navs.index", past_id=past_id))


@navs_bp.route("/<int:nav_id>/update_zero", methods=["GET"])
@login_required
def update_zero(past_id: int, nav_id: int):
    nav = Nav.query.filter_by(past_id=past_id, parid=0).first()
    past = Past.query.get(past_id)
    if nav and past:
        nav.content = (
            f"=====这里是分割线====={datetime.utcnow()}====={past.content or ''}====="
        )
        db.session.commit()
    return redirect(url_for("navs.index", past_id=past_id))


@navs_bp.route("/<int:nav_id>/update_zero_part", methods=["GET"])
@login_required
def update_zero_part(past_id: int, nav_id: int):
    nav = Nav.query.filter_by(id=nav_id, past_id=past_id).first()
    if nav:
        nav.updated_at = datetime.utcnow()
        db.session.commit()
    return redirect(url_for("navs.index", past_id=past_id))


@navs_bp.route("/<int:nav_id>/update_root", methods=["GET"])
@login_required
def update_root(past_id: int, nav_id: int):
    nav = Nav.query.filter_by(id=nav_id, past_id=past_id).first()
    if nav:
        nav.updated_at = datetime.utcnow()
        db.session.commit()
        db.session.add(Activation(past_id=past_id, parid=nav_id))
        db.session.commit()
    return redirect(url_for("navs.index", past_id=past_id) + f"#{nav_id}")


@navs_bp.route("/<int:nav_id>/add_root", methods=["GET"])
@login_required
def add_root(past_id: int, nav_id: int):
    db.session.add(Activation(past_id=past_id, parid=nav_id))
    db.session.commit()
    return redirect(url_for("navs.index", past_id=past_id))
