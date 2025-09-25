import pytest
from api.utils.tracked_cycle import TrackedCycle


def test_cycle_basic_iteration():
    items = ["a", "b", "c"]
    tc = TrackedCycle(items)

    result = [next(tc) for _ in range(6)]
    assert result == ["a", "b", "c", "a", "b", "c"]


def test_cycle_with_offset():
    items = [1, 2, 3, 4]
    tc = TrackedCycle(items, offset=2)

    result = [next(tc) for _ in range(6)]
    # With offset=2, we should start at items[2] == 3
    assert result == [3, 4, 1, 2, 3, 4]


def test_cycle_offset_wraps():
    items = [10, 20, 30]
    tc = TrackedCycle(items, offset=5)  # 5 % 3 = 2

    result = [next(tc) for _ in range(4)]
    assert result == [30, 10, 20, 30]


def test_cycle_empty_items():
    tc = TrackedCycle([])
    with pytest.raises(StopIteration):
        next(tc)


def test_cycle_single_item():
    tc = TrackedCycle([42])

    result = [next(tc) for _ in range(5)]
    assert result == [42, 42, 42, 42, 42]


def test_offset_tracking():
    items = ["x", "y", "z"]
    tc = TrackedCycle(items)

    assert tc.offset == 0  # initial
    next(tc)
    assert tc.offset == 1
    next(tc)
    assert tc.offset == 2
    next(tc)
    assert tc.offset == 0  # wrapped around


def test_offset_with_initial_nonzero():
    items = ["alpha", "beta", "gamma"]
    tc = TrackedCycle(items, offset=1)

    assert tc.offset == 1
    assert next(tc) == "beta"
    assert tc.offset == 2
    assert next(tc) == "gamma"
    assert tc.offset == 0
