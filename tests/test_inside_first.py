import pytest

from plottie.inside_first import find_dependencies, group_inside_first


@pytest.mark.parametrize("lines,exp", [
    # Empty
    ([], {}),
    # Singleton
    ([[(0, 0), (10, 10)]], {0: set()}),
    # Non-overlapping
    ([[(0, 0), (10, 10)], [(20, 20), (30, 30)]], {0: set(), 1: set()}),
    # Overlapping
    ([[(0, 0), (10, 10)], [(5, 5), (15, 15)]], {0: set(), 1: set()}),
    # Not strictly contained
    ([[(0, 0), (10, 10)], [(5, 5), (10, 10)]], {0: set(), 1: set()}),
    # 0 contains 1
    ([[(0, 0), (10, 10)], [(5, 5), (7, 7)]], {0: {1}, 1: set()}),
])
def test_find_dependencies(lines, exp):
    assert find_dependencies(lines) == exp


@pytest.mark.parametrize("lines,exp", [
    # Empty
    ([], []),
    # Singleton
    ([[(0, 0), (10, 10)]], [[[(0, 0), (10, 10)]]]),
    # Not contained
    (
        [[(0, 0), (10, 10)], [(20, 20), (30, 30)]],
        [[[(0, 0), (10, 10)], [(20, 20), (30, 30)]]]
    ),
    # Nesting
    (
        [
            # Inner-most
            [(5, 5), (6, 6)],
            [(25, 25), (26, 26)],
            # Middle layer
            [(4, 4), (7, 7)],
            [(24, 24), (27, 27)],
            # Outer layer
            [(0, 0), (30, 30)],
        ],
        [
            [[(5, 5), (6, 6)], [(25, 25), (26, 26)]],
            [[(4, 4), (7, 7)], [(24, 24), (27, 27)]],
            [[(0, 0), (30, 30)]],
        ],
    ),
])
def test_group_inside_first(lines, exp):
    assert group_inside_first(lines) == exp
