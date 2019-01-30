"""
Utility functions for finding registration marks in SVGs.

For a full description of the registration marks identified by this module see
the documentation for
:py:meth:`py_silhouette.SilhouetteDevice.zero_on_registration_mark`.
"""

from collections import defaultdict

from attr import attrs, attrib


@attrs(frozen=True)
class RegmarkBox(object):
    """Parameters describing a regmark's top-left filled square box."""
    
    x = attrib()
    """
    X coordinate of the top-left corner of the mark (accounting for stroke
    width).
    """
    
    y = attrib()
    """
    Y coordinate of the top-left corner of the mark (accounting for stroke
    width).
    """
    
    size = attrib()
    """Width and height of the box (including stroke)."""
    
    thickness = attrib()
    """Stroke thickness of the box outline."""


@attrs(frozen=True)
class RegmarkBracket(object):
    """
    Base class for parameters describing a regmark's bottom-left or top-right
    bracket.
    """
    
    x = attrib()
    """
    X coordinate of the corner of the bracket (accounting for stroke width).
    """
    
    y = attrib()
    """
    Y coordinate of the corner of the bracket (accounting for stroke width).
    """
    
    length = attrib()
    """Length of the bracket's 'arms'."""
    
    thickness = attrib()
    """Stroke thickness of the bracket."""


class RegmarkBottomLeftBracket(RegmarkBracket):
    """Bottom left bracket dimensions."""

class RegmarkTopRightBracket(RegmarkBracket):
    """Bottom left bracket dimensions."""


def classify_regmark_component(colour, thickness, line):
    """
    For internal use. Given a line, classify what part of a registration mark
    it could be.
    
    Parameters
    ----------
    colour: (r, g, b, a) or None
    thickness: float or None
    line: [(x, y), ...]
    
    Returns
    -------
    regmark_type
        One of:
        
        * `RegmarkBox`
        * `RegmarkBottomLeftBracket`
        * `RegmarkTopRightBracket`
        * `None`
    """
    # Only consider lines with a simple, black stroke
    if colour is None or colour != (0, 0, 0, 1):
        return None
    if thickness is None or thickness == 0:
        return None
    
    # Don't bother considering at anything other than closed squares and
    # brackets described with the minimum number of lines
    if len(line) != 3 and len(line) != 5:
        return None
    
    # Check that the orientation of lines alternates between horizontal and
    # vertical and that all lines are the same length
    last_is_horizontal = None
    last_length = None
    segment_polarities = []  # 'True' if +ve, 'False' if -ve
    for (x1, y1), (x2, y2) in zip(line[0:], line[1:]):
        is_horizontal = y1 == y2
        is_vertical = x1 == x2
        
        # We've found a non-horizontal/vertical line which definately isn't
        # part of a registration mark.
        if is_horizontal is is_vertical:
            print("Not h or v")
            print(x1, y1, x2, y2)
            return None
        
        # Make sure the line orientation alternates
        if last_is_horizontal is None:
            last_is_horizontal = is_horizontal
        elif (last_is_horizontal == is_horizontal or
                last_is_horizontal != is_vertical):
            # Repeated horizontal/vertical line: not a regmark.
            print("Same orientation as last segment")
            print(last_is_horizontal, is_horizontal, is_vertical)
            return None
        last_is_horizontal = is_horizontal
        
        # Make sure the lines are the same length
        length = x2 - x1 if is_horizontal else y2 - y1
        if last_length is None:
            last_length = abs(length)
        elif last_length != abs(length):
            print("Lines different lengths")
            return None
        
        segment_polarities.append(length >= 0)
    
    if len(line) == 3:
        # This is a bracket, determine which type
        #
        # Valid brackets:
        #
        #                                           222      111
        #                         1        2           1        2
        #                         1        2           1        2
        #                          222      111
        #
        #     last_is_horizontal  T        F        T        F
        #     segment_polarities  TT       FF       FF       TT
        #
        # Invalid brackets:
        #
        #                                            222      111
        #                             1        2    1        2
        #                             1        2    1        2
        #                          222      111
        #
        #     last_is_horizontal  T        F        T        F
        #     segment_polarities  TF       TF       FT       FT
        p1, p2 = segment_polarities
        if last_is_horizontal == p1 == p2:
            return RegmarkBottomLeftBracket(
                x=min(line[0][0], line[2][0]) - (thickness/2.0),
                y=max(line[0][1], line[2][1]) + (thickness/2.0),
                length=last_length,
                thickness=thickness,
            )
        elif (not last_is_horizontal) == p1 == p2:
            return RegmarkTopRightBracket(
                x=max(line[0][0], line[2][0]) + (thickness/2.0),
                y=min(line[0][1], line[2][1]) - (thickness/2.0),
                length=last_length,
                thickness=thickness,
            )
        else:
            return None
    elif len(line) == 5:
        # If the line is closed, this *must* be a box since all sides are
        # perpendicular.
        if line[0] == line[4]:
            return RegmarkBox(
                x=min(line[0][0], line[2][0]) - (thickness/2.0),
                y=min(line[0][1], line[2][1]) - (thickness/2.0),
                size=last_length + thickness,
                thickness=thickness,
            )
        else:
            return None
        


@attrs
class RegmarkSpecification(object):
    """
    A specification of the key measurements of a set of registration marks.
    """
    
    x = attrib()
    """Global X coordinate (mm) of the top-left corner of the box."""
    
    y = attrib()
    """Global Y coordinate (mm) of the top-left corner of the box."""
    
    width = attrib()
    """Width (mm) of the registered area (to outermost bounds of the mark)."""
    
    height = attrib()
    """Height (mm) of the registered area (to outermost bounds of the mark)."""
    
    box_size = attrib(default=5.0)
    """The size of the square box (mm), including strokes."""
    
    line_length = attrib(default=20.0)
    """The length of the bracket lines (mm)."""
    
    line_thickness = attrib(default=0.5)
    """The thickness of the bracket line strokes (mm)."""
    
    def is_line_part_of_regmark(self, colour, thickness, line):
        """
        Is the specified line part of this registration mark?
        
        .. note:

            If a document (eroneously) has several overlapping registration
            marks with differing box-sizes/lengths/thicknesses brackets which
            are entirely covered by the brackets in this regmark are also
            considered part of the regmark.
        
        Parameters
        ----------
        colour: (r, g, b, a) or None
        thickness: float or None
        line: [(x, y), ...]
        
        Returns
        -------
        is_part_of_regmark : bool
        """
        c = classify_regmark_component(colour, thickness, line)
        
        if c is None:
            return False
        elif isinstance(c, RegmarkBox):
            return (
                c.x == self.x and
                c.y == self.y and
                c.size <= self.box_size
            )
        elif isinstance(c, RegmarkBottomLeftBracket):
            return (
                c.x == self.x and
                c.y == self.y + self.height and
                c.length <= self.line_length and
                c.thickness <= self.line_thickness
            )
        elif isinstance(c, RegmarkTopRightBracket):
            return (
                c.x == self.x + self.width and
                c.y == self.y and
                c.length <= self.line_length and
                c.thickness <= self.line_thickness
            )
        else:
            assert False


def find_regmarks(outlines,
                  required_box_size=None,
                  required_line_length=None,
                  required_line_thickness=None):
    """
    Find a set of registration marks given a list of outlines from an SVG (e.g.
    extracted by :py:func:`svgoutline.svg_to_outlines`).
    
    .. note::
    
        Because this function only takes outlines as an argument, the
        upper-left box in the registration mark *must* be stroked.
    
    Parameters
    ----------
    outlines : [(colour, thickness, line), ...]
        A series of lines from an SVG. ``colour`` should be a tuple (r, g, b,
        a) or None. ``thickness`` should be a float or None. ``line`` should be
        a list of (x, y) tuples.
    required_box_size : float or None
        If specified, ignore registration marks whose upper-left box is not
        this size.
    required_line_length : float or None
        If specified, ignore registration marks whose brackets are not this
        length.
    required_line_thickness : float or None
        If specified, ignore registration marks whose brackets are not this
        thickness.

    Returns
    -------
    spec : :py:class:`RegmarkSpecification`
        If registration marks are found, a description of those marks is
        returned. If multiple sets of registration marks are found, the
        outermost set will be assumed.
    
    Raises
    ------
    ValueError
        If no registration marks are found, a :py:exc:`ValueError` is raised
        with a message which also mentions what parts of the registration mark
        were found.
    """
    # A list of all boxes [RegmarkBox, ...]
    boxes = []
    
    # A dictionary {x: [RegmarkBottomLeftBracket, ...], ...} giving the
    # bottom-left corner brackets at a specified x-offset.
    bl_brackets = defaultdict(list)
    
    # A dictionary {(y, length, thickness): [RegmarkTopRightBracket, ...], ...}
    # giving the top-right corner brackets with a specified y-offset, length
    # and thickness.
    tr_brackets = defaultdict(list)
    
    for colour, thickness, line in outlines:
        c = classify_regmark_component(colour, thickness, line)
        if isinstance(c, RegmarkBox):
            if required_box_size is None or c.size == required_box_size:
                boxes.append(c)
        elif isinstance(c, RegmarkBottomLeftBracket):
            if ((required_line_length is None or c.length == required_line_length) and
                    (required_line_thickness is None or c.thickness == required_line_thickness)):
                bl_brackets[c.x].append(c)
        elif isinstance(c, RegmarkTopRightBracket):
            if ((required_line_length is None or c.length == required_line_length) and
                    (required_line_thickness is None or c.thickness == required_line_thickness)):
                tr_brackets[(c.y, c.length, c.thickness)].append(c)
    
    # Find all matching pairings of boxes and brackets
    #
    # [RegmarkSpecification, ...]
    regmarks = []
    for box in boxes:
        for bl_bracket in bl_brackets[box.x]:
            for tr_bracket in tr_brackets[(box.y, bl_bracket.length, bl_bracket.thickness)]:
                regmarks.append(RegmarkSpecification(
                    x=box.x,
                    y=box.y,
                    width=tr_bracket.x - box.x,
                    height=bl_bracket.y - box.y,
                    box_size=box.size,
                    line_length=bl_bracket.length,
                    line_thickness=bl_bracket.thickness,
                ))
    
    # Return the outer-most regmarks found
    if not regmarks:
        raise ValueError(
            "No regmarks found in SVG (found {} boxes, {} lower-left brackets "
            "and {} upper-right brackets which don't match up correctly).".format(
                len(boxes),
                sum(len(brackets) for brackets in bl_brackets.values()),
                sum(len(brackets) for brackets in tr_brackets.values()),
            )
        )
    else:
        return min(regmarks, key=lambda r: (
            # Outermost
            r.x, r.y,
            -r.width, -r.height,
            # With longest, thickest lines
            -r.line_length,
            -r.line_thickness,
        ))
