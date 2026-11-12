"""Command line: pingwatch URL [URL ...]"""

import sys

import httpx


def main() -> int:
    status = 0
    for url in sys.argv[1:]:
        code = httpx.get(url, timeout=5).status_code
        print(f"{code} {url}")
        if code != 200:
            status = 1
    return status
