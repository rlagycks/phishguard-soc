"""Renew Gmail watch (run this before the 7-day expiry via cron).

Cron example: renew every 6 days
  0 9 */6 * * /path/to/venv/bin/python /path/to/scripts/renew_watch.py

The FastAPI server also auto-renews via APScheduler, but this script
is a manual fallback.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import requests

API_BASE = "http://localhost:8000"


def main():
    resp = requests.post(f"{API_BASE}/api/admin/watch/renew")
    if resp.ok:
        print("Watch renewed:", resp.json())
    else:
        print("Failed:", resp.status_code, resp.text)


if __name__ == "__main__":
    main()
