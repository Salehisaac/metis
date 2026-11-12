def top_senders(messages: list[tuple[str, str]], n: int) -> list[str]:
    """Return the names of the `n` senders with the most messages, most messages first.

    messages: (sender, text) pairs. A message whose text is the empty string "" doesn't count.
    n is how many names to return (the size of the ranking), not a message count.
    Senders with equal counts are ordered alphabetically.
    If there are fewer than n senders, return all of them. n == 0 returns []; n < 0 raises ValueError.
    """
    raise NotImplementedError
