"""Flask URL shortener.

Run:  python3 app.py          then open http://127.0.0.1:5000
"""

import os
from urllib.parse import urlsplit

from flask import (Flask, abort, jsonify, redirect, render_template,
                   request, url_for)

import store
from validate import ValidationError, check_not_self, normalize_url, validate_alias


def create_app(db_path=None):
    app = Flask(__name__)
    app.config["DB"] = db_path or os.environ.get("SHORTENER_DB", "links.db")
    conn = store.connect(app.config["DB"])
    app.config["CONN"] = conn

    def own_hosts():
        host = urlsplit(request.host_url).hostname or ""
        return {host, "localhost", "127.0.0.1"}

    def shorten(raw_url, raw_alias):
        """Shared by the form and the JSON API so they cannot drift apart."""
        url = check_not_self(normalize_url(raw_url), own_hosts())
        alias = validate_alias(raw_alias)
        code, _ = store.create_link(conn, url, alias)
        return code, url

    @app.get("/")
    def index():
        return render_template("index.html", links=store.recent_links(conn),
                               totals=store.totals(conn), error=None, created=None)

    @app.post("/")
    def create_from_form():
        try:
            code, url = shorten(request.form.get("url"), request.form.get("alias"))
        except ValidationError as e:
            return render_template("index.html", links=store.recent_links(conn),
                                   totals=store.totals(conn), error=str(e),
                                   created=None), 400
        except store.CodeTaken as e:
            return render_template("index.html", links=store.recent_links(conn),
                                   totals=store.totals(conn),
                                   error=f"The alias '{e}' is already taken.",
                                   created=None), 409
        return render_template("index.html", links=store.recent_links(conn),
                               totals=store.totals(conn), error=None,
                               created={"code": code, "url": url,
                                        "short": request.host_url.rstrip("/") + "/" + code})

    @app.post("/api/shorten")
    def api_shorten():
        data = request.get_json(silent=True) or {}
        try:
            code, url = shorten(data.get("url"), data.get("alias"))
        except ValidationError as e:
            return jsonify(error=str(e)), 400
        except store.CodeTaken as e:
            return jsonify(error=f"alias '{e}' is already taken"), 409
        except store.OutOfCodes:
            return jsonify(error="could not allocate a code"), 503
        return jsonify(code=code, url=url,
                       short_url=request.host_url.rstrip("/") + "/" + code), 201

    @app.get("/api/stats/<code>")
    def api_stats(code):
        s = store.link_stats(conn, code)
        if s is None:
            return jsonify(error="no such link"), 404
        return jsonify(s)

    @app.get("/s/<code>")
    def stats_page(code):
        s = store.link_stats(conn, code)
        if s is None:
            abort(404)
        return render_template("stats.html", s=s)

    @app.get("/<code>")
    def follow(code):
        row = store.find(conn, code)
        if row is None:
            abort(404)
        store.record_click(conn, row["id"],
                           referrer=request.referrer,
                           user_agent=request.headers.get("User-Agent"))
        # 302, not 301: a permanent redirect is cached by the browser and the
        # click is never counted again
        return redirect(row["url"], code=302)

    @app.errorhandler(404)
    def not_found(_):
        return render_template("404.html"), 404

    return app


if __name__ == "__main__":
    create_app().run(debug=False, port=int(os.environ.get("PORT", 5000)))
