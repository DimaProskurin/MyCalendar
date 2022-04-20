from django.test import TestCase

from core.common.min_generator import min_stream
from core.common.segment_union import union_stream


class MinStreamTestCase(TestCase):
    def test_sanity(self):
        g1 = (i for i in range(3))
        g2 = (i**2 for i in range(3))
        g3 = (i for i in range(-3, 1))
        stream = min_stream([g1, g2, g3])
        self.assertListEqual([-3, -2, -1, 0, 0, 0, 1, 1, 2, 4], list(stream))


class UnionStreamTestCase(TestCase):
    def test_sanity(self):
        g1 = (it for it in [(-2, 1), (3, 5), (5, 8)])
        g2 = (it for it in [(-7, -5), (-5, 0), (9, 10)])
        self.assertListEqual([(-7, 1), (3, 8), (9, 10)], list(union_stream([g1, g2])))
