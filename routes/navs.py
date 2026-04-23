import os
import random
import subprocess
import sys
from datetime import datetime

from flask import (
    Blueprint,
    Response,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import login_required
from sqlalchemy import and_

from models import Activation, Nav, Past, db

navs_bp = Blueprint("navs", __name__)


def _search_by_keys(query, keys: list[str]):
    for v in keys:
        query = query.filter(Nav.content.ilike(f"%{v}%"))
    return query


def _wrap_label(text: str, width: int = 16) -> str:
    text = (text or "").replace('"', "").replace("\\", "").replace("\n", " ").replace("\r", " ")
    if not text:
        return ""
    break_chars = set("，。、；：,.!?！？ 　")
    parts: list[str] = []
    buf = ""
    for ch in text:
        buf += ch
        if len(buf) >= width and ch in break_chars:
            parts.append(buf)
            buf = ""
        elif len(buf) >= width * 2:
            parts.append(buf)
            buf = ""
    if buf:
        parts.append(buf)
    return "\\n".join(parts)


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
            parent_label = _wrap_label(parent.content if parent else "")
            kid_label = _wrap_label(kid.content or "")
            edges.append(f'"{parent_label}" -> "{kid_label}"')
            walk(kid.id)

    walk(root_id)
    return edges


def _find_paths(
    past_id: int, from_key: str, to_key: str, max_paths: int = 50, max_depth: int = 40
) -> list[list[Nav]]:
    navs = Nav.query.filter_by(past_id=past_id).all()
    children_map: dict[int, list[Nav]] = {}
    for n in navs:
        children_map.setdefault(n.parid or 0, []).append(n)

    fk = from_key.lower()
    tk = to_key.lower()
    start_nodes = [n for n in navs if n.content and fk in n.content.lower()]
    end_ids = {n.id for n in navs if n.content and tk in n.content.lower()}

    paths: list[list[Nav]] = []

    def dfs(node: Nav, path: list[Nav], visited: set[int], depth: int):
        if len(paths) >= max_paths or depth > max_depth:
            return
        if node.id in end_ids and (len(path) > 1 or fk == tk):
            paths.append(list(path))
            return
        for child in children_map.get(node.id, []):
            if child.id in visited:
                continue
            visited.add(child.id)
            path.append(child)
            dfs(child, path, visited, depth + 1)
            path.pop()
            visited.discard(child.id)

    for start in start_nodes:
        if len(paths) >= max_paths:
            break
        dfs(start, [start], {start.id}, 0)
    return paths


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

    path_from = request.args.get("path_from", "").strip()
    path_to = request.args.get("path_to", "").strip()
    path_results: list[list[Nav]] = []
    if path_from and path_to:
        path_results = _find_paths(past_id, path_from, path_to)

    return render_template(
        "navs/index.html",
        past=past,
        past_id=past_id,
        navs=navs,
        activation_id=activation_id,
        nav_part_root=nav_part_root,
        indents=indents,
        path_from=path_from,
        path_to=path_to,
        path_results=path_results,
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


def _paths_to_gv(paths: list[list[Nav]]) -> str:
    lines = ["digraph G {"]
    seen: set[tuple[str, str]] = set()
    for p in paths:
        for i in range(len(p) - 1):
            a = _wrap_label(p[i].content or "")
            b = _wrap_label(p[i + 1].content or "")
            key = (a, b)
            if key in seen:
                continue
            seen.add(key)
            lines.append(f'"{a}" -> "{b}"')
    lines.append("}")
    return "\n".join(lines) + "\n"


def _save_path_gv(past_id: int, paths: list[list[Nav]]) -> str:
    public_dir = current_app.config["PUBLIC_DIR"]
    os.makedirs(public_dir, exist_ok=True)
    path = os.path.join(public_dir, f"past_{past_id}_path.gv")
    with open(path, "w", encoding="utf-8") as f:
        f.write(_paths_to_gv(paths))
    return path


@navs_bp.route("/path.gv", methods=["GET"])
@login_required
def path_gv(past_id: int):
    path_from = request.args.get("path_from", "").strip()
    path_to = request.args.get("path_to", "").strip()
    if not path_from or not path_to:
        return "need path_from and path_to", 400
    paths = _find_paths(past_id, path_from, path_to)
    body = _paths_to_gv(paths)
    _save_path_gv(past_id, paths)
    resp = Response(body, mimetype="text/vnd.graphviz")
    resp.headers["Content-Disposition"] = (
        f'attachment; filename="past_{past_id}_path.gv"'
    )
    return resp


def _open_in_graphviz(gv_path: str) -> tuple[bool, str]:
    if sys.platform != "darwin":
        return False, f"open-in-app only works on macOS (server is {sys.platform})"
    if not os.path.exists(gv_path):
        return False, f"file not found: {gv_path}"
    try:
        subprocess.run(["open", "-a", "Graphviz", gv_path], check=True)
        return True, "opened in Graphviz"
    except (subprocess.CalledProcessError, FileNotFoundError):
        try:
            subprocess.run(["open", gv_path], check=True)
            return True, "opened with default app"
        except Exception as exc:  # noqa: BLE001
            return False, f"failed to open: {exc}"


@navs_bp.route("/open_gv", methods=["GET"])
@login_required
def open_gv(past_id: int):
    gv_path = os.path.join(
        current_app.config["PUBLIC_DIR"], f"past_{past_id}_navs.gv"
    )
    ok, msg = _open_in_graphviz(gv_path)
    flash(msg, "notice" if ok else "error")
    return redirect(url_for("navs.index", past_id=past_id))


@navs_bp.route("/open_path_gv", methods=["GET"])
@login_required
def open_path_gv(past_id: int):
    path_from = request.args.get("path_from", "").strip()
    path_to = request.args.get("path_to", "").strip()
    if not path_from or not path_to:
        flash("need path_from and path_to", "error")
        return redirect(url_for("navs.index", past_id=past_id))
    paths = _find_paths(past_id, path_from, path_to)
    gv_path = _save_path_gv(past_id, paths)
    ok, msg = _open_in_graphviz(gv_path)
    flash(msg, "notice" if ok else "error")
    return redirect(
        url_for(
            "navs.index",
            past_id=past_id,
            path_from=path_from,
            path_to=path_to,
        )
    )
