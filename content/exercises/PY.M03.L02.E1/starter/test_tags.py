from tags import count_tags, posts_by_tag, shared_tags

POSTS = {
    10: ["python", "web"],
    11: ["Go", "web", "WEB"],
    12: ["Python", "testing", "python"],
    13: [],
}


def test_count_tags():
    assert count_tags(POSTS) == {"python": 2, "web": 2, "go": 1, "testing": 1}


def test_count_tags_is_case_insensitive_and_once_per_post():
    assert count_tags({1: ["SQL", "sql", "Sql"]}) == {"sql": 1}


def test_count_tags_empty():
    assert count_tags({}) == {}
    assert count_tags({1: []}) == {}


def test_posts_by_tag():
    assert posts_by_tag(POSTS) == {
        "python": [10, 12],
        "web": [10, 11],
        "go": [11],
        "testing": [12],
    }


def test_posts_by_tag_lists_each_post_once():
    assert posts_by_tag({7: ["api", "API"], 3: ["api"]}) == {"api": [7, 3]}


def test_posts_by_tag_keys_in_first_seen_order():
    assert list(posts_by_tag(POSTS)) == ["python", "web", "go", "testing"]


def test_shared_tags():
    assert shared_tags(POSTS, 10, 12) == ["python"]
    assert shared_tags(POSTS, 10, 11) == ["web"]


def test_shared_tags_sorted_and_case_insensitive():
    posts = {1: ["b", "C", "a"], 2: ["c", "A", "B", "d"]}
    assert shared_tags(posts, 1, 2) == ["a", "b", "c"]


def test_shared_tags_none_or_unknown_post():
    assert shared_tags(POSTS, 11, 12) == []
    assert shared_tags(POSTS, 10, 99) == []


def test_input_not_modified():
    posts = {1: ["Py", "py"]}
    count_tags(posts)
    posts_by_tag(posts)
    shared_tags(posts, 1, 1)
    assert posts == {1: ["Py", "py"]}
