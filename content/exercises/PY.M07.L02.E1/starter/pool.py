from contextlib import contextmanager


class Pool:
    """A fixed set of connections that callers lease for the duration of a with block."""

    def __init__(self, connections):
        self.free = list(connections)

    @contextmanager
    def lease(self):
        """with pool.lease() as conn: ...

        Takes the first free connection and gives it back when the block ends, whatever happens.
        An empty pool raises RuntimeError("pool exhausted").
        """
        raise NotImplementedError
