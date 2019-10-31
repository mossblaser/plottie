import pytest

from xml.etree import ElementTree

from plottie.plot_mode_heuristics import (
    PlotMode,
    guess_plot_mode,
)


@pytest.mark.parametrize("layer_names,exp_mode", [
    # No layers
    ([], None),
    # No significantly named layers
    (["Layer 1"], None),
    (["Layer 1", "Layer 2"], None),
    # Cut layers only
    (["Layer 1", "Cut", "Layer 2"], PlotMode.cut),
    (["Layer 1", "CUTS", "Layer 2"], PlotMode.cut),
    (["Layer 1", "CuTtInG", "Layer 2"], PlotMode.cut),
    (["Layer 1", "cutout", "Layer 2"], PlotMode.cut),
    (["Layer 1", "edge", "Layer 2"], PlotMode.cut),
    (["Layer 1", "Edges", "Layer 2"], PlotMode.cut),
    (["Layer 1", "Some other words in cut layer name", "Layer 2"], PlotMode.cut),
    # Not cutting layer
    (["Layer 1", "Don't take shortcuts", "Layer 2"], None),
    # Plot layers only
    (["Layer 1", "Plot", "Layer 2"], PlotMode.plot),
    (["Layer 1", "PlOtS", "Layer 2"], PlotMode.plot),
    (["Layer 1", "plt", "Layer 2"], PlotMode.plot),
    (["Layer 1", "plts", "Layer 2"], PlotMode.plot),
    (["Layer 1", "Things to plot out!", "Layer 2"], PlotMode.plot),
    # Not plotting layer
    (["Layer 1", "Not a splot", "Layer 2"], None),
    # Mixture results in None
    (["Layer 1", "Plot", "Cut", "Layer 2"], None),
])
def test_guess_plot_mode(layer_names, exp_mode):
    svg = ElementTree.fromstring("""<?xml version="1.0" encoding="UTF-8" standalone="no"?>
        <svg
           xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape">
          {}
        </svg>
    """.format(
        "\n".join(
            """
            <g
               inkscape:groupmode="layer"
               id="layer{}"
               inkscape:label="{}">
            </g>
            """.format(i, layer)
            for i, layer in enumerate(layer_names)
        )
    ))
    
    assert guess_plot_mode(svg) == exp_mode
