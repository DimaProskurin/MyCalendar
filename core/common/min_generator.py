import heapq
from typing import Generator, Iterable


class Item:
    def __init__(self, it, gen):
        self.it = it
        self.gen = gen

    def __lt__(self, other):
        return self.it < other.it

    def __next__(self):
        return Item(it=next(self.gen), gen=self.gen)

    def __repr__(self):
        return self.it


def min_stream(generators: Iterable[Generator]) -> Generator:
    """
    From several "sorted inside" generators returns generator which merge input generators saving sorted ordering
    """
    items = []
    for gen in generators:
        try:
            items.append(Item(next(gen), gen))
        except StopIteration:
            continue
    heapq.heapify(items)

    while len(items) > 0:
        yield items[0].it
        try:
            items[0] = next(items[0])
        except StopIteration:
            items.pop(0)
        heapq.heapify(items)
