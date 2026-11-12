"""Verify 'output' quiz answers by running their code. Stdlib only.

For every output quiz whose `code` is Python (not a '#'-comment describing a shell command), run it with the current
interpreter and require the normalised stdout to equal the answer. Shell-command quizzes are listed as 'manual'.
Usage: .venv/bin/python tools/check_quizzes.py [content_dir]
"""

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate import FENCE, ROOT, parse_front_matter  # noqa: E402


def normalise(s):
    """Same rule as site/assets/js/content.js normalizeOutput."""
    # trim each line and collapse runs of whitespace inside it; drop trailing blank lines
    lines = [" ".join(line.split()) for line in s.replace("\r\n", "\n").split("\n")]
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)


def output_quizzes(content, prefix=""):
    """Yield (filename, quiz) for output quizzes. Malformed files/blocks are skipped: the validator reports them."""
    for path in sorted([*content.glob(f"lessons/{prefix}*.md"), *content.glob(f"assessments/{prefix}*.md")]):
        try:
            _, body = parse_front_matter(path.read_text(encoding="utf-8"))
        except ValueError:
            continue
        for kind, raw in FENCE.findall(body):
            if kind == "quiz":
                try:
                    q = json.loads(raw)
                except ValueError:
                    continue
                if q.get("type") == "output":
                    yield path.name, q


def check_one(name, q):
    """-> (problems, executed count, manual list) for one output quiz."""
    code = q.get("code", "")
    if not code or code.lstrip().startswith("#"):
        return [], 0, [f"{name}#{q['id']}"]
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=30)
    if r.returncode != 0 or normalise(r.stdout) != normalise(q["answer"]):
        return [f"{name}#{q['id']}: answer {q['answer']!r} but code printed {r.stdout!r} (exit {r.returncode})"], 1, []
    return [], 1, []


def check(content):
    problems, checked, manual = [], 0, []
    for name, q in output_quizzes(content):
        p, n, m = check_one(name, q)
        problems += p
        checked += n
        manual += m
    return problems, checked, manual


def main(content=ROOT / "content"):
    problems, checked, manual = check(content)
    for p in problems:
        print(p)
    print(f"{checked} output quiz(zes) executed, {len(problems)} wrong; verify by hand (shell commands): {', '.join(manual) or 'none'}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "content"))
