import pytest

from plottie.regmarks import (
    find_horizontal_and_vertical_segments,
    find_regmarks,
)

class TestFindHorizontalAndVerticalSegments(object):
    
    def test_empty(self):
        assert find_horizontal_and_vertical_segments([]) == ([], [])
    
    def test_singleton(self):
        assert find_horizontal_and_vertical_segments([(0, 0)]) == ([], [])
    
    def test_not_vertical_or_horizontal(self):
        assert find_horizontal_and_vertical_segments([(0, 0), (1, 1)]) == ([], [])
    
    @pytest.mark.parametrize("line", [
        # Simple backward/forward
        [(0, 0), (1, 0)],
        [(1, 0), (0, 0)],
        # Multiple vertices along length
        [(0, 0), (0.5, 0), (1, 0)],
        # Goes full length back over itself
        [(0, 0), (1, 0), (0, 0)],
        [(1, 0), (0, 0), (1, 0)],
        # Goes back over itself in middle
        [(0, 0), (0.75, 0), (0.25, 0), (1, 0)],
    ])
    def test_horizontal(self, line):
        h, v = find_horizontal_and_vertical_segments(line)
        assert h == [(0, 0, 1)]
        assert v == []
    
    @pytest.mark.parametrize("line", [
        # Simple backward/forward
        [(0, 0), (0, 1)],
        [(0, 1), (0, 0)],
        # Multiple vertices along length
        [(0, 0), (0, 0.5), (0, 1)],
        # Goes full length back over itself
        [(0, 0), (0, 1), (0, 0)],
        [(0, 1), (0, 0), (0, 1)],
        # Goes back over itself in middle
        [(0, 0), (0, 0.75), (0, 0.25), (0, 1)],
    ])
    def test_vertical(self, line):
        h, v = find_horizontal_and_vertical_segments(line)
        assert h == []
        assert v == [(0, 0, 1)]
    
    @pytest.mark.parametrize("line", [
        # Simple single segments, all horizontal or vertical
        [(1, 0), (0, 0), (0, 1)],
        [(0, 1), (0, 0), (1, 0)],
        # Multi-segment, self-intersecting lines connected by non-vertical
        # lines.
        [(0, 0), (0.75, 0), (0.25, 0), (1, 0), (0, 1), (0, 0), (0, 1)],
    ])
    def test_combined_horizontal_and_vertical_and_other(self, line):
        h, v = find_horizontal_and_vertical_segments(line)
        assert h == [(0, 0, 1)]
        assert v == [(0, 0, 1)]

class TestFindRegmarks(object):
    
    def test_just_regmarks(self):
        regmarks = find_regmarks([
            ((0, 0, 0, 1), 2, [(21, 11), (24, 11), (24, 14), (21, 14), (21, 11)]),
            ((0, 0, 0, 1), 2, [(80, 11), (100, 11), (100, 31)]),
            ((0, 0, 0, 1), 2, [(21, 50), (21, 70), (41, 70)]),
        ])
        
        assert regmarks.x == 20
        assert regmarks.y == 10
        
        assert regmarks.width == 81
        assert regmarks.height == 61
        
        assert regmarks.box_size == 5
        assert regmarks.line_thickness == 2
        assert regmarks.line_length == 20
    
    def test_box_thickness_can_be_different(self):
        regmarks = find_regmarks([
            ((0, 0, 0, 1), 4, [(22, 12), (23, 12), (23, 13), (22, 13), (22, 12)]),
            ((0, 0, 0, 1), 2, [(80, 11), (100, 11), (100, 31)]),
            ((0, 0, 0, 1), 2, [(21, 50), (21, 70), (41, 70)]),
        ])
        
        assert regmarks.x == 20
        assert regmarks.y == 10
        
        assert regmarks.width == 81
        assert regmarks.height == 61
        
        assert regmarks.box_size == 5
        assert regmarks.line_thickness == 2
        assert regmarks.line_length == 20
    
    def test_choose_outermost_regmarks(self):
        regmarks = find_regmarks([
            # Outer (chosen regmark)
            ((0, 0, 0, 1), 2, [(21, 11), (24, 11), (24, 14), (21, 14), (21, 11)]),
            ((0, 0, 0, 1), 2, [(80, 11), (100, 11), (100, 31)]),
            ((0, 0, 0, 1), 2, [(21, 50), (21, 70), (41, 70)]),
            
            # Duplicate (shouldn't break anything!)
            ((0, 0, 0, 1), 2, [(21, 11), (24, 11), (24, 14), (21, 14), (21, 11)]),
            ((0, 0, 0, 1), 2, [(80, 11), (100, 11), (100, 31)]),
            ((0, 0, 0, 1), 2, [(21, 50), (21, 70), (41, 70)]),
            
            # Inner (but same top-left corner)
            ((0, 0, 0, 1), 2, [(21, 11), (24, 11), (24, 14), (21, 14), (21, 11)]),
            ((0, 0, 0, 1), 2, [(70, 11), (90, 11), (90, 31)]),
            ((0, 0, 0, 1), 2, [(21, 40), (21, 60), (41, 60)]),
            
            # Inner (completely)
            ((0, 0, 0, 1), 2, [(31, 21), (34, 21), (34, 24), (31, 24), (31, 21)]),
            ((0, 0, 0, 1), 2, [(70, 21), (90, 21), (90, 41)]),
            ((0, 0, 0, 1), 2, [(31, 40), (31, 60), (51, 60)]),
        ])
        
        assert regmarks.x == 20
        assert regmarks.y == 10
        
        assert regmarks.width == 81
        assert regmarks.height == 61
        
        assert regmarks.box_size == 5
        assert regmarks.line_thickness == 2
        assert regmarks.line_length == 20
    
    def test_no_lines(self):
        with pytest.raises(ValueError):
            find_regmarks([])
    
    def test_just_the_box_isnt_enough(self):
        with pytest.raises(ValueError):
            find_regmarks([
                ((0, 0, 0, 1), 4, [(22, 12), (23, 12), (23, 13), (22, 13), (22, 12)]),
            ])
    
    def test_just_one_bracket_isnt_enough(self):
        with pytest.raises(ValueError):
            find_regmarks([
                ((0, 0, 0, 1), 4, [(22, 12), (23, 12), (23, 13), (22, 13), (22, 12)]),
                ((0, 0, 0, 1), 2, [(90, 11), (100, 11), (100, 21)]),
            ])
    
    def test_line_lengths_must_be_same(self):
        with pytest.raises(ValueError):
            find_regmarks([
                ((0, 0, 0, 1), 4, [(22, 12), (23, 12), (23, 13), (22, 13), (22, 12)]),
                ((0, 0, 0, 1), 2, [(90, 11), (100, 11), (100, 21)]),
                ((0, 0, 0, 1), 2, [(21, 50), (21, 70), (41, 70)]),
            ])
    
    def test_line_thickness_must_be_the_same(self):
        with pytest.raises(ValueError):
            find_regmarks([
                ((0, 0, 0, 1), 4, [(22, 12), (23, 12), (23, 13), (22, 13), (22, 12)]),
                ((0, 0, 0, 1), 4, [(80, 12), (100, 12), (100, 32)]),
                ((0, 0, 0, 1), 2, [(21, 50), (21, 70), (41, 70)]),
            ])
