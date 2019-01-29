"""
Utility functions for finding registration marks in SVGs.
"""

from collections import defaultdict

from attr import attrs, attrib


def find_horizontal_and_vertical_segments(line):
    """
    Given a line defined by a list of (x, y) coordinates, return two lists
    enumerating the horizontal lines (as (x1, y1, x2) tuples) and vertical
    lines (as (x1, y1, y2) tuples) .
    
    In both tuple types, the (x1, y1) part will always have the lower-valued
    coordinates.
    """
    # Special case
    if not line:
        return ([], [])
    
    vertical_lines = []
    horizontal_lines = []
    
    # The starting point of the current vertical and horizontal line
    # segments
    vx1 = line[0][0]
    vy1 = vy2 = line[0][1]
    
    hx1 = hx2 = line[0][0]
    hy1 = line[0][1]
    
    # NB: Adding the (None, None) coordinate as the final coordinate causes
    # the last iteration of the following loop to determine that the final
    # (non-existant) line segment is niether vertical nor horizontal and
    # thus will push the last h/v line into the accumulating buffers.
    for x, y in line[1:] + [(None, None)]:
        # Attempt to extend the current horizontal/vertical being drawn (or
        # start again if we cease to be horizontal/vertical
        if x == vx1:
            vy1 = min(vy1, y)
            vy2 = max(vy2, y)
        else:
            if vy1 != vy2:
                vertical_lines.append((vx1, vy1, vy2))
            vx1 = x
            vy1 = vy2 = y
        
        if y == hy1:
            hx1 = min(hx1, x)
            hx2 = max(hx2, x)
        else:
            if hx1 != hx2:
                horizontal_lines.append((hx1, hy1, hx2))
            hy1 = y
            hx1 = hx2 = x
    
    return (horizontal_lines, vertical_lines)


@attrs
class RegmarkSpecification(object):
    """
    A specification of the key measurements of a registration mark in an SVG
    file.
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
    
    line_thickness = attrib(default=0.5)
    """The thickness of the bracket line strokes (mm)."""
    
    line_length = attrib(default=20.0)
    """The length of the bracket lines (mm)."""


def find_regmarks(outlines):
    """
    Given a list of outlines from SVG (extracted by
    `svgoutline.svg_to_outlines`), attempt to find the outermost set of
    registration marks in the design.
    """
    # A set([(x1, y1, y2, width), ...]) of all vertical black lines (and their
    # thicknesses).
    vertical_lines = set()
    
    # A set([(x1, y1, x2, width), ...]) of all horizontal black lines (and
    # their thicknesses).
    horizontal_lines = set()
    
    for colour, width, line in outlines:
        # Skip non-black lines
        if colour != (0, 0, 0, 1):
            continue
        
        h, v = find_horizontal_and_vertical_segments(line)
        for x1, y1, x2 in h:
            horizontal_lines.add((x1, y1, x2, width))
        for x1, y1, y2 in v:
            vertical_lines.add((x1, y1, y2, width))
    
    # A list of (x1, y1, size) tuples which give the upper-left coordinate and
    # size of the box, accounting for any stroke.
    boxes = []
    for x1, y1, x2, width in horizontal_lines:
        size = x2 - x1
        if ((x1, y1+size, x2, width) in horizontal_lines and
                (x1, y1, y1+size, width) in vertical_lines and
                (x2, y1, y1+size, width) in vertical_lines):
            boxes.append((
                x1 - (width/2),
                y1 - (width/2),
                size + width,
            ))
    
    # A dictionary {x1: [(y1, thickness, length), ...], ...} giving the bottom-left corner
    # of all bottom left brackets (accounting for stroke thickness).
    bl_brackets = defaultdict(list)
    for x1, y1, x2, thickness in horizontal_lines:
        length = x2 - x1
        if (x1, y1-length, y1, thickness) in vertical_lines:
            bl_brackets[x1 - (thickness/2)].append((
                y1 + (thickness/2),
                thickness,
                length,
            ))
    
    # A dictionary {(y1, thickness, length): [x1, ...]), ...} giving the top-right
    # corner of all top-right brackets (accounting for stroke thickness).
    tr_brackets = defaultdict(list)
    for x1, y1, x2, thickness in horizontal_lines:
        length = x2 - x1
        if (x1+length, y1, y1+length, thickness) in vertical_lines:
            tr_brackets[(
                y1 - (thickness/2),
                thickness,
                length,
            )].append(x1 + length + (thickness/2))
    
    # Filter for box-and-bracket-pair sets accoumulating RegmarkSpecifications
    regmarks = []
    for x1, y1, box_size in boxes:
        for y2, line_thickness, line_length in bl_brackets[x1]:
            for x2 in tr_brackets[(y1, line_thickness, line_length)]:
                # NB: Don't allow the sides of the box to be treated brackets!
                if y2 > y1 + box_size and x2 > x1 + box_size:
                    regmarks.append(RegmarkSpecification(
                        x=x1,
                        y=y1,
                        width=x2-x1,
                        height=y2-y1,
                        box_size=box_size,
                        line_thickness=line_thickness,
                        line_length=line_length,
                    ))
    
    # Return the outer-most regmarks found
    if not regmarks:
        raise ValueError(
            "No regmarks found in SVG (found {} boxes, {} lower-left brackets "
            "and {} upper-right brackets which don't match up correctly).".format(
                len(boxes),
                len(bl_brackets),
                len(tr_brackets),
            )
        )
    else:
        return min(regmarks, key=lambda r: (r.x, r.y, -r.width, -r.height))
