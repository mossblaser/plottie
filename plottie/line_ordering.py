"""
Functions for re-ordering/combining lines to reduce cutting and plotting time.
"""

from collections import defaultdict


def optimise_lines(lines, start_pos=(0, 0)):
    """
    Given a list of lines, return a new list of lines in an order which
    attempts to reduce the time spent moving between line endpoints or lifting
    the pen/cutter. Lines with coincident endpoints will be merged into a
    single contiguous line. 
    """
    
    # Enumerates the lines which may start or end at a given point.
    # {(x, y): [line_index, ...], ...}
    endpoints_to_lines = defaultdict(list)
    for line_index, line in enumerate(lines):
        if line[0] != line[-1]:
            # Open path (can only start/end at ends)
            endpoints_to_lines[line[0]].append(line_index)
            endpoints_to_lines[line[-1]].append(line_index)
        else:
            # Closed path (can start/end at any point)
            for point in line:
                endpoints_to_lines[point].append(line_index)
    
    # The optimised set of lines
    # [[(x, y), ...], ...]
    out = []
    
    cur_pos = start_pos
    for _ in range(len(lines)):
        # A simple greedly agorithm: pick the point nearest to our current
        # position and move to that
        endpoint = min(
            endpoints_to_lines,
            key=lambda ep: (ep[0] - cur_pos[0])**2 + (ep[1] - cur_pos[1])**2,
        )
        
        # Pick an arbitary line at this point
        next_line_index = endpoints_to_lines[endpoint][0]
        next_line = lines[next_line_index]
        
        if next_line[0] != next_line[-1]:
            # Open line segment.
            
            # Reverse line to connect to previous position more easily if necessary
            if next_line[0] == endpoint:
                next_line = next_line[:]
            else:
                next_line = next_line[::-1]
            
            # Remove this line from the lookup
            for point in [next_line[0], next_line[-1]]:
                endpoints_to_lines[point].remove(next_line_index)
                if not endpoints_to_lines[point]:
                    del endpoints_to_lines[point]
        else:
            # Closed line segment.
            
            # Remove the line from the lookup
            for point in next_line:
                endpoints_to_lines[point].remove(next_line_index)
                if not endpoints_to_lines[point]:
                    del endpoints_to_lines[point]
            
            # Re-order such that we start from the chosen point
            for start_index, point in enumerate(next_line):
                if point == endpoint:
                    break
            next_line = next_line[start_index:-1] + next_line[:start_index+1]
        
        # Add line to output (combining with previous line, if possible)
        if out and out[-1][-1] == endpoint:
            out[-1].extend(next_line[1:])
        else:
            out.append(next_line)
        
        cur_pos = next_line[-1]
    
    return out
