import pytest

from plottie.over_cut import (
    first_part_of_line,
    over_cut_lines,
)


class TestFirstPartOfLine(object):
    
    def test_empty(self):
        assert first_part_of_line([], 0.0) == []
        assert first_part_of_line([], 1.0) == []
    
    def test_zero_distance(self):
        assert first_part_of_line([(0, 0)], 0.0) == []
        assert first_part_of_line([(0, 0), (1, 2), (3, 4)], 0.0) == []
    
    @pytest.fixture
    def line(self):
        return [
            (10, 100),
            (12, 100),
            (12, 103),
            (10, 103),
            (10, 100),
        ]
    
    def test_exactly_on_vertex(self, line):
        assert first_part_of_line(line, 0.0) == []
        assert first_part_of_line(line, 2.0) == line[:2]
        assert first_part_of_line(line, 5.0) == line[:3]
        assert first_part_of_line(line, 7.0) == line[:4]
        assert first_part_of_line(line, 10.0) == line[:5]
    
    def test_beyond_ends_of_line(self, line):
        assert first_part_of_line(line, -1.0) == []
        assert first_part_of_line(line, 100.0) == line
    
    def test_midpoint_in_line(self, line):
        assert first_part_of_line(line, 0.5) == [
            (10.0, 100.0),
            (10.5, 100.0),
        ]
        assert first_part_of_line(line, 2.5) == [
            (10.0, 100.0),
            (12.0, 100.0),
            (12.0, 100.5),
        ]

class TestOverCutLines(object):
    
    def test_empty(self):
        assert over_cut_lines([], 0.0) == []
        assert over_cut_lines([], 1.0) == []
    
    def test_do_nothing_to_open_lines(self):
        open_lines = [[(100, 200), (300, 400)]]
        assert over_cut_lines(open_lines, 1.0) == open_lines
    
    def test_cut_closed_lines(self):
        closed_lines = [[
            (10, 100),
            (12, 100),
            (12, 103),
            (10, 103),
            (10, 100),
        ]]
        assert over_cut_lines(closed_lines, 1.5) == [[
            (10, 100),
            (12, 100),
            (12, 103),
            (10, 103),
            (10, 100),
            (11.5, 100),
        ]]
