import pytest

from plottie.regmarks import (
    classify_regmark_component,
    find_regmarks,
    RegmarkBox,
    RegmarkBottomLeftBracket,
    RegmarkTopRightBracket,
    RegmarkSpecification
)


def rotate_array(a, n):
    n %= len(a)
    return a[n:] + a[:n]


class TestClassifyRegmarkComponent(object):
    
    @pytest.mark.parametrize("colour", [(0, 0, 0, 1), (1, 1, 1, 1,), None])
    @pytest.mark.parametrize("thickness", [0, 0.5, 1, None])
    def test_empty(self, colour, thickness):
        assert classify_regmark_component(colour, thickness, []) is None
    
    @pytest.mark.parametrize("thickness", [0.5, 1])
    @pytest.mark.parametrize("x,y,size,open_line", [
        (x, y, size,
            rotate_array(
                [(x, y), (x+size, y), (x+size, y+size), (x, y+size)],
                rotation,
            )[::order]
        )
        for x, y in [(0, 0), (50, 100)]
        for size in [5, 8.5]
        for rotation in range(4)
        for order in [1, -1]
    ])
    def test_box(self, thickness, x, y, size, open_line):
        # Close the line
        closed_line = open_line + [open_line[0]]
        
        assert classify_regmark_component(
            (0, 0, 0, 1),
            thickness,
            closed_line,
        ) == RegmarkBox(
            x=x - (thickness/2.0),
            y=y - (thickness/2.0),
            size=size + thickness,
            thickness=thickness,
        )
    
    @pytest.mark.parametrize("thickness", [0.5, 1])
    @pytest.mark.parametrize("x,y,length,line", [
        (x, y, length, [(x, y-length), (x, y), (x+length, y)][::order])
        for x, y in [(0, 0), (50, 100)]
        for length in [15.5, 20]
        for order in [1, -1]
    ])
    def test_bottom_left_bracket(self, thickness, x, y, length, line):
        assert classify_regmark_component(
            (0, 0, 0, 1),
            thickness,
            line,
        ) == RegmarkBottomLeftBracket(
            x=x - (thickness/2.0),
            y=y + (thickness/2.0),
            length=length,
            thickness=thickness,
        )
    
    @pytest.mark.parametrize("thickness", [0.5, 1])
    @pytest.mark.parametrize("x,y,length,line", [
        (x, y, length, [(x-length, y), (x, y), (x, y+length)][::order])
        for x, y in [(0, 0), (50, 100)]
        for length in [15.5, 20]
        for order in [1, -1]
    ])
    def test_top_right_bracket(self, thickness, x, y, length, line):
        assert classify_regmark_component(
            (0, 0, 0, 1),
            thickness,
            line,
        ) == RegmarkTopRightBracket(
            x=x + (thickness/2.0),
            y=y - (thickness/2.0),
            length=length,
            thickness=thickness,
        )
    
    @pytest.mark.parametrize("colour", [None, (1, 1, 1, 1), (0, 0, 0, 0)])
    def test_colour_rules_out_lines(self, colour):
        assert classify_regmark_component(
            colour,
            1,
            [(0, 0), (10, 0), (10, 10)],
        ) is None
    
    @pytest.mark.parametrize("thickness", [None, 0])
    def test_thickness_rules_out_lines(self, thickness):
        assert classify_regmark_component(
            (0, 0, 0, 1),
            thickness,
            [(0, 0), (10, 0), (10, 10)],
        ) is None
    
    @pytest.mark.parametrize("line", [
        # Too few to be anything
        [],
        [(0, 0)],
        [(0, 0), (10, 0)],
        # Too many for a bracket, too few for a box
        [(0, 0), (10, 0), (10, 5), (10, 10)],
        # Too many for a box
        [(0, 0), (10, 0), (10, 10), (0, 10), (0, 5), (0, 0)],
    ])
    def test_vertex_count_rules_out_lines(self, line):
        assert classify_regmark_component((0, 0, 0, 1), 1, line) is None
    
    @pytest.mark.parametrize("line", [
        # All/some vertices are at same point
        [(0, 0), (0, 0), (0, 0)],
        [(0, 0), (0, 0), (10, 0)],
        # Non horizontal/vertical lines (first segment)
        [(0, 0), (1, 1), (0, 0)],
        [(0, 0), (1, -1), (0, 0)],
        [(0, 0), (-1, -1), (0, 0)],
        [(0, 0), (-1, 1), (0, 0)],
        # Non horizontal/vertical lines (second segment)
        [(0, 0), (2, 0), (1, 1)],
        [(0, 0), (2, 0), (1, -1)],
        [(0, 0), (2, 0), (-1, -1)],
        [(0, 0), (2, 0), (-1, 1)],
    ])
    def test_contains_non_h_or_v_lines(self, line):
        assert classify_regmark_component((0, 0, 0, 1), 1, line) is None
    
    @pytest.mark.parametrize("line", [
        # Multiple horizontal
        [(0, 0), (1, 0), (2, 0)],
        # Multiple vertical
        [(0, 0), (0, 1), (0, 2)],
    ])
    def test_contains_non_alternating_h_and_v(self, line):
        assert classify_regmark_component((0, 0, 0, 1), 1, line) is None
    
    @pytest.mark.parametrize("line", [
        # Mishapen bottom-left bracket
        [(0, 0), (0, 2), (3, 2)],
        # Mishapen top-right bracket
        [(0, 0), (2, 0), (2, 3)],
        # Mishapen box
        [(0, 0), (2, 0), (2, 3), (0, 3), (0, 0)],
    ])
    def test_contains_differing_line_lengths(self, line):
        assert classify_regmark_component((0, 0, 0, 1), 1, line) is None
    
    @pytest.mark.parametrize("line", [
        # Top-left bracket
        [(0, 2), (0, 0), (2, 0)],
        [(2, 0), (0, 0), (0, 2)],
        # Bottom-right bracket
        [(2, 0), (2, 2), (0, 2)],
        [(0, 2), (2, 2), (2, 0)],
    ])
    def test_illigal_bracket_orientation(self, line):
        assert classify_regmark_component((0, 0, 0, 1), 1, line) is None
    
    @pytest.mark.parametrize("line", [
        # Alternates in direction but never closes
        [(0, 0), (2, 0), (2, 2), (4, 2), (4, 0)],
    ])
    def test_unclosed_box(self, line):
        assert classify_regmark_component((0, 0, 0, 1), 1, line) is None


class TestIsLinePartOfRegmark(object):

    @pytest.fixture
    def spec(self):
        return RegmarkSpecification(
            x=10,
            y=20,
            width=100,
            height=200,
            box_size=5,
            line_length=20,
            line_thickness=2,
        )
    
    @pytest.mark.parametrize("colour", [None, (1, 1, 1, 1), (0, 0, 0, 1)])
    @pytest.mark.parametrize("thickness", [None, 1])
    def test_empty_line(self, spec, colour, thickness):
        assert spec.is_line_part_of_regmark(colour, thickness, []) is False
    
    @pytest.mark.parametrize("expectation,colour,thickness,line", [
        # Boxes which do correctly align with the box
        (True, (0, 0, 0, 1), 2, [(11, 21), (14, 21), (14, 24), (11, 24), (11, 21)]),
        (True, (0, 0, 0, 1), 1, [(10.5, 20.5), (14.5, 20.5), (14.5, 24.5), (10.5, 24.5), (10.5, 20.5)]),
        # Box is in the wrong place
        (False, (0, 0, 0, 1), 2, [(10, 20), (13, 20), (13, 23), (10, 23), (10, 20)]),
        # Box is wrong shape
        (False, (0, 0, 0, 1), 2, [(12, 21), (14, 21), (14, 24), (12, 24), (12, 21)]),
        # Box thickness means box is smaller/bigger than actual regmark
        (False, (1, 1, 1, 1), 3, [(11, 21), (14, 21), (14, 24), (11, 24), (11, 21)]),
        (False, (1, 1, 1, 1), 1, [(11, 21), (14, 21), (14, 24), (11, 24), (11, 21)]),
        # Box is the wrong colour
        (False, (1, 1, 1, 1), 2, [(11, 21), (14, 21), (14, 24), (11, 24), (11, 21)]),
    ])
    def test_box(self, spec, colour, thickness, line, expectation):
        assert spec.is_line_part_of_regmark(
            colour, thickness, line) is expectation
    
    @pytest.mark.parametrize("expectation,colour,thickness,line", [
        # Brackets which exactly match
        (True, (0, 0, 0, 1), 2, [(11, 199), (11, 219), (31, 219)]),
        (True, (0, 0, 0, 1), 2, [(31, 219), (11, 219), (11, 199)]),
        # Brackets which match but are thinner
        (True, (0, 0, 0, 1), 1, [(10.5, 199.5), (10.5, 219.5), (30.5, 219.5)]),
        # Brackets which match but are shorter
        (True, (0, 0, 0, 1), 2, [(11, 209), (11, 219), (21, 219)]),
        # Brackets which are in the wrong place
        (False, (0, 0, 0, 1), 2, [(21, 199), (21, 219), (41, 219)]),
        (False, (0, 0, 0, 1), 2, [(11, 209), (11, 229), (31, 229)]),
        # Brackets which are the wrong colour
        (False, (1, 1, 1, 1), 2, [(11, 199), (11, 219), (31, 219)]),
        # Brackets which are asymmetric
        (False, (0, 0, 0, 1), 2, [(11, 199), (11, 219), (21, 219)]),
        # Brackets which are too long
        (False, (0, 0, 0, 1), 2, [(11, 189), (11, 219), (41, 219)]),
        # Brackets which are too thick
        (False, (0, 0, 0, 1), 4, [(12, 199), (12, 218), (32, 218)]),
    ])
    def test_bottom_left_bracket(self, spec, colour, thickness, line, expectation):
        assert spec.is_line_part_of_regmark(
            colour, thickness, line) is expectation
    
    @pytest.mark.parametrize("expectation,colour,thickness,line", [
        # Brackets which exactly match
        (True, (0, 0, 0, 1), 2, [(89, 21), (109, 21), (109, 41)]),
        (True, (0, 0, 0, 1), 2, [(109, 41), (109, 21), (89, 21)]),
        # Brackets which match but are thinner
        (True, (0, 0, 0, 1), 1, [(89.5, 20.5), (109.5, 20.5), (109.5, 40.5)]),
        # Brackets which match but are shorter
        (True, (0, 0, 0, 1), 2, [(99, 21), (109, 21), (109, 31)]),
        # Brackets which are in the wrong place
        (False, (0, 0, 0, 1), 2, [(99, 21), (119, 21), (119, 41)]),
        (False, (0, 0, 0, 1), 2, [(89, 31), (109, 31), (109, 51)]),
        # Brackets which are the wrong colour
        (False, (1, 1, 1, 1), 2, [(89, 21), (109, 21), (109, 41)]),
        # Brackets which are asymmetric
        (False, (0, 0, 0, 1), 2, [(89, 21), (109, 21), (109, 31)]),
        # Brackets which are too long
        (False, (0, 0, 0, 1), 2, [(79, 21), (109, 21), (109, 61)]),
        # Brackets which are too thick
        (False, (0, 0, 0, 1), 4, [(88, 22), (108, 22), (108, 42)]),
    ])
    def test_top_right_bracket(self, spec, colour, thickness, line, expectation):
        assert spec.is_line_part_of_regmark(
            colour, thickness, line) is expectation
        


class TestFindRegmarks(object):
    
    @pytest.mark.parametrize("required_box_size", [None, 5])
    @pytest.mark.parametrize("required_line_length", [None, 20])
    @pytest.mark.parametrize("required_line_thickness", [None, 2])
    def test_just_regmarks(self,
                           required_box_size,
                           required_line_length,
                           required_line_thickness):
        regmarks = find_regmarks([
            ((0, 0, 0, 1), 2, [(21, 11), (24, 11), (24, 14), (21, 14), (21, 11)]),
            ((0, 0, 0, 1), 2, [(80, 11), (100, 11), (100, 31)]),
            ((0, 0, 0, 1), 2, [(21, 50), (21, 70), (41, 70)]),
        ], required_box_size, required_line_length, required_line_thickness)
        
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
            
            # Outer but thinner lines
            ((0, 0, 0, 1), 2, [(21, 11), (24, 11), (24, 14), (21, 14), (21, 11)]),
            ((0, 0, 0, 1), 1, [(80, 10.5), (100, 10.5), (100, 30.5)]),
            ((0, 0, 0, 1), 1, [(20.5, 50), (20.5, 70), (40.5, 70)]),
            
            # Outer but shorter lines
            ((0, 0, 0, 1), 2, [(21, 11), (24, 11), (24, 14), (21, 14), (21, 11)]),
            ((0, 0, 0, 1), 2, [(90, 11), (100, 11), (100, 21)]),
            ((0, 0, 0, 1), 2, [(31, 60), (31, 70), (41, 70)]),
            
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
    
    @pytest.mark.parametrize("outlines", [
        # Box not 5x5
        [
            ((0, 0, 0, 1), 2, [(21, 11), (25, 11), (25, 15), (21, 15), (21, 11)]),
            ((0, 0, 0, 1), 2, [(80, 11), (100, 11), (100, 31)]),
            ((0, 0, 0, 1), 2, [(21, 50), (21, 70), (41, 70)]),
        ],
        # Length not 20
        [
            ((0, 0, 0, 1), 2, [(21, 11), (24, 11), (24, 14), (21, 14), (21, 11)]),
            ((0, 0, 0, 1), 2, [(90, 11), (100, 11), (100, 21)]),
            ((0, 0, 0, 1), 2, [(31, 60), (31, 70), (41, 70)]),
        ],
        # Thickness not 2
        [
            ((0, 0, 0, 1), 2, [(21, 11), (24, 11), (24, 14), (21, 14), (21, 11)]),
            ((0, 0, 0, 1), 1, [(80, 10.5), (100, 10.5), (100, 30.5)]),
            ((0, 0, 0, 1), 1, [(20.5, 50), (20.5, 70), (40.5, 70)]),
        ],
    ])
    def test_restrict_parameters(self, outlines):
        assert find_regmarks(
            outlines,
            required_box_size=5,
            required_line_length=20,
            required_line_thickness=2,
        ) is None
    
    def test_no_lines(self):
        assert find_regmarks([]) is None
    
    def test_just_the_box_isnt_enough(self):
        assert find_regmarks([
            ((0, 0, 0, 1), 4, [(22, 12), (23, 12), (23, 13), (22, 13), (22, 12)]),
        ]) is None
    
    def test_just_one_bracket_isnt_enough(self):
        assert find_regmarks([
            ((0, 0, 0, 1), 4, [(22, 12), (23, 12), (23, 13), (22, 13), (22, 12)]),
            ((0, 0, 0, 1), 2, [(90, 11), (100, 11), (100, 21)]),
        ]) is None
    
    def test_line_lengths_must_be_same(self):
        assert find_regmarks([
            ((0, 0, 0, 1), 4, [(22, 12), (23, 12), (23, 13), (22, 13), (22, 12)]),
            ((0, 0, 0, 1), 2, [(90, 11), (100, 11), (100, 21)]),
            ((0, 0, 0, 1), 2, [(21, 50), (21, 70), (41, 70)]),
        ]) is None
    
    def test_line_thickness_must_be_the_same(self):
        assert find_regmarks([
            ((0, 0, 0, 1), 4, [(22, 12), (23, 12), (23, 13), (22, 13), (22, 12)]),
            ((0, 0, 0, 1), 4, [(80, 12), (100, 12), (100, 32)]),
            ((0, 0, 0, 1), 2, [(21, 50), (21, 70), (41, 70)]),
        ]) is None
