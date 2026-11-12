import re
from pathlib import Path

DOC = Path(__file__).parent / "DESIGN.md"
SECTIONS = ["Context and scope", "Goals", "Non-goals", "Estimates", "Data model", "API",
            "Alternatives considered", "Failure modes", "Cross-cutting concerns"]


def text():
    """The doc without HTML comments."""
    return re.sub(r"<!--.*?-->", "", DOC.read_text(encoding="utf-8"), flags=re.DOTALL)


def sections():
    found = {}
    for block in re.split(r"^## ", text(), flags=re.MULTILINE)[1:]:
        title, _, body = block.partition("\n")
        found[title.strip()] = body
    return found


def bullets(body):
    return [line for line in body.splitlines() if re.match(r"^\s*[-*] \S", line)]


def test_all_sections_present_in_order():
    titles = [t.strip() for t in re.findall(r"^## (.+)$", text(), flags=re.MULTILINE)]
    assert titles == SECTIONS


def test_no_todo_left():
    assert "TODO" not in text(), "replace every TODO"


def test_short_enough():
    words = len(text().split())
    assert words <= 1200, f"{words} words: a mini design doc should stay under 1200"


def test_goals_and_non_goals_are_lists():
    s = sections()
    assert len(bullets(s.get("Goals", ""))) >= 3, "at least 3 goals"
    assert len(bullets(s.get("Non-goals", ""))) >= 2, "at least 2 non-goals"


def test_estimates_have_numbers():
    body = sections().get("Estimates", "")
    assert "rps" in body.lower(), "state the load in requests per second (rps)"
    assert len(re.findall(r"\d", body)) >= 6, "estimates need actual numbers"


def test_data_model_has_a_table_and_a_key():
    body = sections().get("Data model", "")
    assert "```sql" in body and "CREATE TABLE" in body.upper()
    assert "UNIQUE" in body.upper() or "PRIMARY KEY" in body.upper()


def test_api_lists_endpoints_and_redirect_status():
    body = sections().get("API", "")
    assert len(re.findall(r"\b(GET|POST|PUT|PATCH|DELETE) /", body)) >= 2, "list at least two endpoints"
    assert re.search(r"\b30[1278]\b", body), "say which redirect status you use"


def test_alternatives_give_reasons():
    body = sections().get("Alternatives considered", "")
    assert len(bullets(body)) >= 2
    assert "because" in body.lower(), "each alternative needs a reason"


def test_failure_modes_table():
    body = sections().get("Failure modes", "")
    rows = [line for line in body.splitlines() if line.strip().startswith("|")]
    assert len(rows) >= 5, "header, separator and at least 3 failure rows"
    assert re.match(r"^\|\s*:?-{3,}", rows[1].strip()), "the second table line must be the |---| separator"


def test_cross_cutting_concerns():
    body = sections().get("Cross-cutting concerns", "").lower()
    for word in ("security", "privacy", "observability"):
        assert word in body, f"mention {word}"
