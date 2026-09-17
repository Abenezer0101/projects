"""Job application tracker -- Flask + SQLite + dashboard.

Run:  python3 app.py            then open http://127.0.0.1:5001
      SEED=1 python3 app.py     start with 120 sample applications
"""

import os
from datetime import date

from flask import Flask, abort, flash, jsonify, redirect, render_template, request, url_for

import db


def create_app(db_path=None, seed=False, today=None):
    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY", os.urandom(24))
    conn = db.connect(db_path or os.environ.get("TRACKER_DB", "tracker.db"))
    if seed and conn.execute("SELECT COUNT(*) n FROM applications").fetchone()["n"] == 0:
        db.seed(conn)
    app.config["CONN"] = conn
    app.config["TODAY"] = today or date.today().isoformat()

    def today_str():
        return app.config["TODAY"]

    @app.get("/")
    def index():
        return render_template(
            "index.html",
            apps=db.list_applications(conn, request.args.get("stage") or None,
                                      request.args.get("source") or None,
                                      request.args.get("q") or None),
            stages=db.STAGES + db.TERMINAL, sources=db.SOURCES,
            companies=conn.execute("SELECT * FROM companies ORDER BY name").fetchall(),
            totals=db.totals(conn, today_str()), today=today_str(),
            filters={k: request.args.get(k, "") for k in ("stage", "source", "q")})

    @app.post("/applications")
    def create():
        f = request.form
        name = (f.get("company") or "").strip()
        role = (f.get("role") or "").strip()
        if not name or not role:
            flash("A company and a role are both required.")
            return redirect(url_for("index"))
        cid = db.add_company(conn, name, (f.get("industry") or "Unknown").strip() or "Unknown")
        db.add_application(conn, cid, role, f.get("source") or "Job board",
                           f.get("applied_on") or today_str(), (f.get("notes") or "").strip() or None)
        flash(f"Added {role} at {name}.")
        return redirect(url_for("index"))

    @app.get("/applications/<int:app_id>")
    def detail(app_id):
        row = db.get_application(conn, app_id)
        if row is None:
            abort(404)
        return render_template("detail.html", **row, stages=db.STAGES,
                               terminal=db.TERMINAL, sources=db.SOURCES, today=today_str())

    @app.post("/applications/<int:app_id>/advance")
    def advance(app_id):
        if db.get_application(conn, app_id) is None:
            abort(404)
        stage = request.form.get("stage") or ""
        try:
            db.advance(conn, app_id, stage, request.form.get("occurred_on") or today_str())
        except ValueError:
            flash(f"'{stage}' is not a stage.")
            return redirect(url_for("detail", app_id=app_id)), 400
        return redirect(url_for("detail", app_id=app_id))

    @app.post("/applications/<int:app_id>/edit")
    def edit(app_id):
        if db.get_application(conn, app_id) is None:
            abort(404)
        db.update_application(conn, app_id, role=request.form.get("role"),
                              source=request.form.get("source"),
                              notes=request.form.get("notes"))
        flash("Saved.")
        return redirect(url_for("detail", app_id=app_id))

    @app.post("/applications/<int:app_id>/delete")
    def delete(app_id):
        if db.get_application(conn, app_id) is None:
            abort(404)
        db.delete_application(conn, app_id)
        flash("Application deleted.")
        return redirect(url_for("index"))

    @app.get("/dashboard")
    def dashboard():
        return render_template("dashboard.html",
                               funnel=db.funnel(conn), naive=db.funnel_naive(conn),
                               response=db.response_times(conn), sources=db.by_source(conn),
                               monthly=db.monthly(conn), totals=db.totals(conn, today_str()),
                               today=today_str())

    @app.get("/api/analytics")
    def api_analytics():
        return jsonify(funnel=db.funnel(conn), naive_funnel=db.funnel_naive(conn),
                       response_times=db.response_times(conn), by_source=db.by_source(conn),
                       monthly=db.monthly(conn), totals=db.totals(conn, today_str()))

    @app.errorhandler(404)
    def missing(_):
        return render_template("404.html"), 404

    return app


if __name__ == "__main__":
    create_app(seed=bool(os.environ.get("SEED"))).run(port=int(os.environ.get("PORT", 5001)))
