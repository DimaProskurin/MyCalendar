from typing import Generator, Iterable

from core.common.min_generator import min_stream


def union_stream(generators: Iterable[Generator]) -> Generator:
    """
    From several "sorted inside" generators which returning segments [a, b], ...
    Returns generator of segments which is union of input ones
    """
    stream = min_stream(generators)
    try:
        cur_left, cur_right = next(stream)
    except StopIteration:
        return
    for left, right in stream:
        if left > cur_right:
            yield cur_left, cur_right
            cur_left, cur_right = left, right
        else:
            cur_right = right
    yield cur_left, cur_right
