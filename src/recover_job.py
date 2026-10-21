"""Explicit manual recovery of a stale job. NEVER kills a process or deletes data."""
import argparse
from src import db


def main():
    parser = argparse.ArgumentParser(description="Mark stale crawl as FAILED after verifying worker stopped")
    parser.add_argument("--job-id", required=True, type=int)
    parser.add_argument("--confirm", action="store_true", help="I have confirmed the worker is no longer running")
    args = parser.parse_args()
    if not args.confirm:
        parser.error("--confirm is required; verify process is stopped and back up database")
    job = db.get_job(args.job_id)
    if not job:
        parser.error("Job not found")
    if job["status"] not in db.ACTIVE_STATUSES:
        parser.error("Job is already terminal; no change was made")
    db.finish_job(args.job_id, "FAILED", "Manually recovered after worker stopped")
    print(f"Job #{args.job_id} marked FAILED. Books were not removed.")


if __name__ == "__main__":
    main()
