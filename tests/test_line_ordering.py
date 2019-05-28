import pytest

from plottie.line_ordering import optimise_lines


@pytest.mark.parametrize("lines,exp", [
    # No lines
    ([], []),
    # Single line
    ([[(0, 0)]], [[(0, 0)]]),
    # Non-connecting lines, already in ideal order
    ([[(0, 0), (1, 0)], [(2, 0), (3, 0)]], [[(0, 0), (1, 0)], [(2, 0), (3, 0)]]),
    # Lines in wrong order
    ([[(2, 0), (3, 0)], [(0, 0), (1, 0)]], [[(0, 0), (1, 0)], [(2, 0), (3, 0)]]),
    # Lines given backwards
    ([[(3, 0), (2, 0)], [(1, 0), (0, 0)]], [[(0, 0), (1, 0)], [(2, 0), (3, 0)]]),
    # Lines can be merged
    ([[(0, 0), (1, 0)], [(1, 0), (2, 0)]], [[(0, 0), (1, 0), (2, 0)]]),
    # Closed path
    ([[(0, 0), (1, 0), (0, 0)]], [[(0, 0), (1, 0), (0, 0)]]),
    # Join to different part of closed path
    (
        [[(0, 0), (1, 1)], [(1, 0), (1, 1), (2, 0), (1, 0)]],
        [[(0, 0), (1, 1), (2, 0), (1, 0), (1, 1)]],
    ),
])
def test_optimise_lines(lines, exp):
    assert optimise_lines(lines) == exp

