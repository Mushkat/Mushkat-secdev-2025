"""Simple HTTP-based healthcheck used by Docker."""

from __future__ import annotations

import os
import sys
from urllib import request
from urllib.error import HTTPError, URLError


def check_health(url: str, timeout: float) -> int:
    req = request.Request(url, headers={"User-Agent": "parking-healthcheck"})
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            return 0 if resp.status == 200 else 1
    except (HTTPError, URLError, OSError):
        return 1


def main() -> int:
    url = os.getenv("HEALTHCHECK_URL", "http://127.0.0.1:8000/health")
    timeout = float(os.getenv("HEALTHCHECK_TIMEOUT", "3"))
    return check_health(url, timeout)


if __name__ == "__main__":
    sys.exit(main())
