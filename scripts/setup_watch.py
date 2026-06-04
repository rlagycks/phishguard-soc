"""One-time script: register Gmail watch via API.

Run after completing OAuth:
  cd scripts
  python setup_watch.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import requests

API_BASE = "http://localhost:8000"


def main():
    resp = requests.post(f"{API_BASE}/api/admin/watch/setup")
    if resp.ok:
        print("Watch registered:", resp.json())
    else:
        print("Failed:", resp.status_code, resp.text)


if __name__ == "__main__":
    main()
