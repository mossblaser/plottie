"""
Group together line segments such that inner-most shapes are drawn first.
"""

from toposort import toposort


def find_dependencies(lines):
    """
    For each line in the input, return the indices of all lines which are
    completely enclosed by this line.
    
    Parameters
    ==========
    lines : [[(x, y), ...], ...]
    
    Returns
    =======
    dependencies : {line_index: {contained_line_index, ...}, ...}
    """
    bounding_boxes = [
        (
            min(x for x, y in line),
            min(y for x, y in line),
            max(x for x, y in line),
            max(y for x, y in line),
        )
        for line in lines
    ]
    
    return {
        outer_id: {
            inner_id
            for inner_id, (ix1, iy1, ix2, iy2) in enumerate(bounding_boxes)
            if (
                ox1 < ix1 and oy1 < iy1 and
                ox2 > ix2 and oy2 > iy2
            )
        }
        for outer_id, (ox1, oy1, ox2, oy2) in enumerate(bounding_boxes)
    }


def group_inside_first(lines):
    """
    Group the input lines into sets of lines which may be re-ordered without
    causing outer-most shapes to be drawn before inner-most shapes.
    """
    dependencies = find_dependencies(lines)
    
    out = []
    for line_indices in toposort(dependencies):
        group = []
        for index in sorted(line_indices):
            group.append(lines[index])
        out.append(group)
    
    return out
