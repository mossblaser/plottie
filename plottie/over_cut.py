"""
Functions to over-cut closed line segments slightly to ensure a complete cut.
"""

import math


def first_part_of_line(line, distance):
    """
    Given a line defined by [(x, y), ...], return a line which follows the
    first 'distance' along the line.
    """
    # Special case
    if distance <= 0:
        return []

    out = []
    for ((x1, y1), (x2, y2)) in zip(line, line[1:]):
        out.append((x1, y1))
        
        dx = x2 - x1
        dy = y2 - y1
        length = math.sqrt((dx*dx) + (dy*dy))

        if length < distance:
            distance -= length
        else:
            xm = x1 + (dx * (distance / length))
            ym = y1 + (dy * (distance / length))
            out.append((xm, ym))
            break
    else:
        # Distance is > length of line, don't go around again, just leave it at
        # the end.
        out.extend(line[-1:])

    return out


def over_cut_lines(lines, distance=1.0):
    """
    Over-cut closed lines to ensure a complete cut.
    
    Parameters
    ==========
    lines : [[(x ,y), ...], ...]
        The lines to be cut.
    distance : float
        The distance to over-cut by.
    
    Returns
    =======
    new_lines : [[(x ,y), ...], ...]
    """
    out = []
    
    for line in lines:
        if line[0] != line[-1]:
            # Not a closed cut
            out.append(line)
        else:
            # Closed line, extend as required
            out.append(line + first_part_of_line(line, distance)[1:])
    
    return out
