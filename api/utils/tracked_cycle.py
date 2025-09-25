from itertools import cycle


class TrackedCycle:
    """A cycle iterator that tracks its current offset."""

    def __init__(self, items: list, offset: int = 0):
        self.items = items
        self.offset = offset
        self._cycle = cycle(items)
        for _ in range(offset % len(items) if items else 0):
            next(self._cycle)

    def __next__(self):
        if self.items:
            self.offset = (self.offset + 1) % len(self.items)
        return next(self._cycle)
