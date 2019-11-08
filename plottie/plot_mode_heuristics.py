"""
This module includes a simple hueristic for guessing whether an
Inkscape-originated SVG should be plotted or cut.
"""

import re

from enum import Enum

from plottie.svg_utils import (
    is_inkscape_layer,
    get_inkscape_layer_label,
)


CUT_LAYER_NAMES_REGEX = re.compile(r"\bcut(s|ting|out)?|\bedges?",
                                   re.IGNORECASE)
"""
Regex matching layer names typically associated with cutting.
"""

PLOT_LAYER_NAMES_REGEX = re.compile(r"\bplo?ts?",
                                    re.IGNORECASE)
"""
Regex matching layer names typically associated with plotting.
"""

class PlotMode(Enum):
    """The plotting/cutting mode selected."""
    
    plot = "plot"
    cut = "cut"


def guess_plot_mode(svg):
    """
    Given an SVG as an ElementTree, guess the PlotMode to use based on the
    layer names preesnt. This is based on the names of Inkscape layers in the
    SVG.
    """
    layer_names = [
        get_inkscape_layer_label(node)
        for node in svg.iter()
        if is_inkscape_layer(node)
    ]
    
    maybe_cut = any(CUT_LAYER_NAMES_REGEX.search(name) is not None
                    for name in layer_names)
    maybe_plot = any(PLOT_LAYER_NAMES_REGEX.search(name) is not None
                     for name in layer_names)
    
    # Only guess if not ambiguous
    if maybe_cut and not maybe_plot:
        return PlotMode.cut
    elif maybe_plot and not maybe_cut:
        return PlotMode.plot
    else:
        return None
