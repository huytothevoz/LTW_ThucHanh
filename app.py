"""CrawlInsight local Flask web app / JSON API (SRS 2.0)."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from src import db

ROOT = Path(__file__).resolve().parent
app = Flask(__name__)
app.json.ensure_ascii = False
app.config["JSON_SORT_KEYS"] = False


def api_error(code: str, message: str, status: int):
    return jsonify({"error": {"code": code, "message": message}}), status


@app.get("/")
def dashboard_page():
    return render_template("dashboard.html", active_page="dashboard")


@app.get("/books")
def books_page():
    return render_template("books.html", active_page="books")


@app.get("/api/summary")
def summary_endpoint():
    return jsonify(db.summary())


@app.post("/api/jobs")
def create_job_endpoint():
    if not request.is_json:
        return api_error("INVALID_MAX_PAGES", "Request body must be JSON with max_pages", 400)
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or set(payload) != {"max_pages"}:
        return api_error("INVALID_MAX_PAGES", "Provide only max_pages as an integer from 1 to 3", 400)
    max_pages = payload["max_pages"]
    if type(max_pages) is not int or max_pages not in (1, 2, 3):
        return api_error("INVALID_MAX_PAGES", "max_pages must be an integer from 1 to 3", 400)
    try:
        job = db.create_job(max_pages)
    except db.ActiveJobError:
        return api_error("JOB_ALREADY_ACTIVE", "Another crawl is pending or running", 409)
    log_dir = ROOT / "data" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"crawl-job-{job['id']}.log"
    try:
        with log_path.open("a", encoding="utf-8") as log_file:
            subprocess.Popen(
                [sys.executable, "-m", "crawler.run_job", "--job-id", str(job["id"])],
                cwd=str(ROOT), stdin=subprocess.DEVNULL,
                stdout=log_file, stderr=subprocess.STDOUT,
                shell=False, close_fds=True,
            )
    except OSError:
        db.finish_job(job["id"], "FAILED", "Crawler process could not start")
        return api_error("CRAWLER_LAUNCH_FAILED", "Could not start the crawler", 503)
    return jsonify({"job": {
        "id": job["id"], "status": job["status"],
        "max_pages": job["max_pages"], "created_at": job["created_at"],
    }}), 202


@app.get("/api/jobs/<int:job_id>")
def get_job_endpoint(job_id: int):
    job = db.get_job(job_id)
    if job is None:
        return api_error("JOB_NOT_FOUND", "Crawl job not found", 404)
    return jsonify({"job": job})


@app.get("/api/books")
def books_endpoint():
    query = request.args.get("q", "")
    raw_page = request.args.get("page", "1")
    if not raw_page.isascii() or not raw_page.isdecimal() or not 1 <= len(raw_page) <= 6:
        return api_error("INVALID_FILTER", "page must be an integer between 1 and 100000", 400)
    try:
        result = db.search_books(
            q=query,
            min_price=request.args.get("min_price"),
            max_price=request.args.get("max_price"),
            page=int(raw_page),
        )
    except ValueError as exc:
        return api_error("INVALID_FILTER", str(exc), 400)
    return jsonify(result)


@app.errorhandler(404)
def not_found(_error):
    if request.path.startswith("/api/"):
        return api_error("NOT_FOUND", "API endpoint not found", 404)
    return render_template("404.html", active_page=None), 404


@app.errorhandler(500)
def server_error(_error):
    if request.path.startswith("/api/"):
        return api_error("INTERNAL_ERROR", "An unexpected error occurred", 500)
    return render_template("500.html", active_page=None), 500


if __name__ == "__main__":
    db.init_db()
    host = os.environ.get("FLASK_HOST", "127.0.0.1")
    # Always local-only: a demo without authentication must not be public.
    if host not in {"127.0.0.1", "localhost"}:
        raise SystemExit("CrawlInsight is local-only; FLASK_HOST must be 127.0.0.1")
    port = int(os.environ.get("FLASK_PORT", "5000"))
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)
