"""Merge content/_pending/*.json flag files into content/curriculum.json, then delete the merged files.

Usage: .venv/bin/python tools/merge_pending.py [ID ...]   (default: all pending files)
Run tools/validate.py afterwards.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_module import CONTENT, apply  # noqa: E402


def main(ids):
    path = CONTENT / "curriculum.json"
    cur = json.loads(path.read_text(encoding="utf-8"))
    files = [CONTENT / "_pending" / f"{i}.json" for i in ids] if ids else sorted((CONTENT / "_pending").glob("*.json"))
    for f in files:
        if not apply(cur, f.stem, json.loads(f.read_text(encoding="utf-8"))):
            print(f"{f.name}: unknown module, skipped")
            continue
        print(f"merged {f.name}")
    path.write_text(json.dumps(cur, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for f in files:
        f.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
