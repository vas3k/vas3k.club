from unittest import TestCase

from common.models import group_by


class _Obj:
    def __init__(self, group, name):
        self.group = group
        self.name = name

    def __repr__(self):
        return f"{self.group}:{self.name}"


class TestGroupBy(TestCase):

    def test_consecutive_groups(self):
        items = [_Obj("a", "a1"), _Obj("a", "a2"), _Obj("b", "b1")]
        result = group_by(items, "group")
        self.assertEqual(len(result["a"]), 2)
        self.assertEqual(len(result["b"]), 1)

    def test_non_consecutive_groups(self):
        items = [
            _Obj("a", "a1"),
            _Obj("b", "b1"),
            _Obj("a", "a2"),
        ]
        result = group_by(items, "group")

        self.assertEqual(len(result["a"]), 2)
        self.assertEqual(len(result["b"]), 1)

    def test_todict_false_returns_defaultdict(self):
        items = [_Obj("x", "x1"), _Obj("y", "y1"), _Obj("x", "x2")]
        result = group_by(items, "group", todict=False)
        self.assertEqual(len(result["x"]), 2)
        self.assertEqual(len(result["y"]), 1)
        self.assertEqual(result["missing"], [])

    def test_empty_input(self):
        result = group_by([], "group")
        self.assertEqual(result, {})
