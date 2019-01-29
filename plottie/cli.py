import re

from xml.etree import ElementTree

from argparse import ArgumentParser, REMAINDER
from enum import Enum

from attr import attrs, attrib

from svgoutline import svg_to_outlines, get_svg_page_size
from plottie.svg_utils import (
    find_inkscape_layers,
    css_dimension_to_mm,
    css_colour_to_rgba,
)

import logging


CUT_LAYER_NAMES_REGEX = re.compile(r"\bcut(s|ting|out)?|\bedges?",
                                   re.IGNORECASE)
"""
Regex matching layer names typically associated with cutting.
"""

PLOT_LAYER_NAMES_REGEX = re.compile(r"\boutlines?|\bborders?|\bplo?ts?",
                                    re.IGNORECASE)
"""
Regex matching layer names typically associated with plotting.
"""


ALL_LAYER_NAMES_REGEX = re.compile(
    r"{}|{}".format(CUT_LAYER_NAMES_REGEX.pattern,
                    PLOT_LAYER_NAMES_REGEX.pattern),
    re.IGNORECASE)
"""
Union of CUT_LAYER_NAMES_REGEX and PLOT_LAYER_NAMES_REGEX.
"""


def make_argument_parser():
    """
    Return a fully configured :py:class:`argparse.ArgumentParser` instance.
    """
    parser = ArgumentParser(description="""
        Plot and cut SVG files using a Silhouette desktop plotter/cutter.
    """)
    
    parser.add_argument(
        "svg",
        help="""
            The SVG file to plot or cut.
        """,
    )
    action = parser.add_argument_group(
        "action arguments",
        description="""
            The following arguments create a new cutting or plotting 'group' which
            will consist of the SVG objects selected by one of the 'content
            selection arguments'. These arguments must be placed before other
            plotting or cutting arguments.  If neither argument is used, plottie
            will attempt to guess whether cutting or plotting is required based on
            Inkscape layer names found in the input SVG and, failing that, will
            assume plotting is to be used.
        """
    )
    
    action.add_argument(
        "--cut", "-c",
        dest="cut_args", nargs=REMAINDER,
        help="""
            Cut the lines described by the arguments which follow. May be given
            multiple times to cut different parts of the file separately.
        """
    )
    
    action.add_argument(
        "--plot", "-p",
        dest="plot_args", nargs=REMAINDER,
        help="""
            Plot the lines described by the arguments which follow. May be given
            multiple times to plot different parts of the file separately.
        """
    )
    
    # #########################################################################
    
    content_selection = parser.add_argument_group(
        "content selection arguments",
        description="""
            These options all specify parts of the input which should be
            plotted or cut in the current `--plot` or `--cut` 'group'. If
            multiple arguments are specified, only objects matching all of the
            provided filters will be included. If no arguments are provided,
            `--layer='{}|{}'` will be used if at least one matching layer is
            found, otherwise `--all` will be used.
        """.format(CUT_LAYER_NAMES_REGEX.pattern,
                   PLOT_LAYER_NAMES_REGEX.pattern)
    )
    
    content_selection.add_argument(
        "--all", "-A",
        action="store_true",
        help="""
            Plot or cut all visible outlines in the current SVG (excluding
            registration marks unless `--include-regmarks` is used too).
            Overrides the default behaviour which is to plot based on --layer.
        """,
    )
    
    content_selection.add_argument(
        "--layer", "-l",
        type=str, metavar="REGEX", action="append",
        help="""
            Plot or cut visible outlines only on the Inkscape layers whose
            names match the provided case-insensitive regex. If the layer is
            not visible, it will be made visible. May be given several times to
            select multiple layers to plot.
        """,
    )
    
    content_selection.add_argument(
        "--id", "-i",
        nargs=1, action="append",
        help="""
            Plot or cut only visible outlines for SVG elements which have the
            specified object ID (or are children of that object). May be given
            several times to select multiple IDs to plot.
        """,
    )
    
    content_selection.add_argument(
        "--class", "-s",
        nargs=1, dest="class_name", action="append",
        help="""
            Plot or cut only visible outlines for SVG elements which have the
            specified class (or are children of an object with that class). May be
            given several times to select multiple IDs to plot.
        """,
    )
    
    content_selection.add_argument(
        "--colour", "-C",
        type=str, action="append",
        help="""
            Plot or cut visible outlines with the listed stroke colour. Accepts
            CSS-style hexadecimal colour codes. May be given multiple times to
            select multiple stroke colours to plot. Lines with gradient or
            patterned strokes will be ignored.
        """,
    )
    
    content_selection.add_argument(
        "--width", "-w",
        type=str, action="append",
        help="""
            Plot or cut visible outlines with the listed stroke width given
            with CSS size units (after scaling). Relative dimensions will be
            treated as relative to the document dimensions or registered area
            (if used). May be given multiple times to select multiple widths to
            include.
        """,
    )
    
    # #########################################################################
    
    plotting_parameters = parser.add_argument_group(
        "plotting parameter arguments",
        description="""
            Control the ploter's behaviour. Changes to these parameters will be
            used in the current and all subsequent `--plot` or `--cut` groups,
            unless overridden.
        """
    )
    
    plotting_parameters.add_argument(
        "--speed", "-S",
        type=str,
        help="""
            The speed with which to plot or cut. Either a floating point number
            given in mm/s or a floating point percentage ending with a '%%' symbol
            giving the percentage of the maximum supported speed. Defaults to
            '100%' and is remembered in all subsequent groups.
        """,
    )
    
    plotting_parameters.add_argument(
        "--force", "-F",
        type=str,
        help="""
            The force with which to plot or cut. Either a floating point number
            given in grams or a floating point percentage ending with a '%%' symbol
            giving the percentage of the maximum supported force. Defaults to
            '20%' and is remembered in all subsequent groups.
        """,
    )
    
    # #########################################################################
    
    ordering_parameters = parser.add_argument_group("plotting and cutting order arguments")
    
    ordering_parameters.add_argument(
        "--inside-first",
        action="store_true", dest="inside_first", default=None,
        help="""
            If some lines and shapes are contained within others, cut or plot these
            first. Inside first mode will be disabled by default in `--plot`
            groups and enabled in `--cut` groups. See also `--no-inside-first`.
        """,
    )
    
    ordering_parameters.add_argument(
        "--no-inside-first",
        action="store_false", dest="inside_first",
        help="""
            Don't try to plot or cut lines and shapes contained within others
            first. Inside first mode will be disabled by default in `--plot`
            groups and enabled in `--cut` groups. See also `--inside-first`.
        """,
    )
    
    ordering_parameters.add_argument(
        "--fast-order",
        action="store_true", dest="fast_order", default=None,
        help="""
            If specified, cuts paths in an order which attempts to reduce the time
            taken to cut or plot the shape. Fast ordering will be used by default
            but, if disabled, this will be remembered in subsequent `--cut` and
            `--plot` groups. Opposite of `--native-order`.
        """,
    )
    
    ordering_parameters.add_argument(
        "--native-order",
        action="store_false", dest="fast_order",
        help="""
            If specified, cuts paths in the order they appear in the input file.
            Opposite of `--fast-order`. This setting will be remembered between
            `--cut` and `--plot` groups.
        """,
    )
    
    # #########################################################################
    
    registration_parameters = parser.add_argument_group("registration arguments")
    
    registration_parameters.add_argument(
        "--regmarks", "-r",
        action="store_true", dest="regmarks", default=None,
        help="""
            Detect registration marks in the input SVG and then use these when
            plotting. The registration marks must be visible and drawn as a
            5x5mm stroked-and-filled black square (including stroke thickness)
            at the top left and a pair of 'L' brackets 20x20mm at the bottom
            left and top right. The registration marks will be excluded from
            plotting or cutting commands unless `--include-regmarks` is used.
            This will be remembered for subsequent groups.
        """,
    )
    
    registration_parameters.add_argument(
        "--manual-regmarks",
        nargs=4, metavar=("X-OFFSET", "Y-OFFSET", "WIDTH", "HEIGHT"), dest="regmarks",
        help="""
            Command the plotter to find registration marks denoting an area WIDTH x
            HEIGHT which is (X-OFFSET, Y-OFFSET) from the top-left of the input
            file. CSS-style absolute units should be used for all coordinates and
            dimensions (e.g.  '3mm'). Registration marks at the specified
            coordinates will be automatically removed from ploting/cuting paths
            unless `--include-regmarks` is used. This will be remembered for
            subsequent groups.
        """,
    )
    
    registration_parameters.add_argument(
        "--ignore-regmarks", "-R",
        action="store_false", dest="regmarks",
        help="""
            Do not use registration marks to line up the cutter or plotter, even if
            they are found in the input SVG. Detected registration marks will
            still be removed from ploting/cuting paths unless `--include-regmarks`
            is also used. This will be remembered for subsequent groups.
        """,
    )
    
    registration_parameters.add_argument(
        "--include-regmarks",
        action="store_true", dest="include_regmarks", default=None,
        help="""
            Do not remove registration marks from plotting/cutting commands.
            This option will be remembered in subsequent groups.
        """,
    )
    
    registration_parameters.add_argument(
        "--exclude-regmarks",
        action="store_false", dest="include_regmarks",
        help="""
            Remove registration marks from plotting/cutting commands. Opposite
            of --include-regmarks. This option will be remembered in subsequent
            groups.
        """,
    )
    
    registration_parameters.add_argument(
        "--reregister-on-group", "-e",
        action="store_true", dest="register_on_group", default=None,
        help="""
            Re-find the registration marks before starting each group (started with
            `--plot` and `--cut`). This option will be remembered in subsequent
            groups.
        """,
    )
    
    registration_parameters.add_argument(
        "--no-reregister-on-group", "-E",
        action="store_false",  dest="register_on_group",
        help="""
            Disable registration re-finding as previously enabled by
            `--register-on-group`.
        """,
    )
    
    registration_parameters.add_argument(
        "--reregister-on-distance", "-y",
        nargs=1, metavar="DISTANCE", default=None,
        help="""
            Re-find the registration marks every time the plotter moves more than
            the specified distance in the 'Y' direction (given in CSS absolute
            units, e.g. '10m'). Set to 'none' to disable (the default). Will be
            remembered in subsequent groups.
        """,
    )
    
    # #########################################################################
    
    group = parser.add_argument_group("group arguments")
    
    group.add_argument(
        "--pause-between-groups", "-W",
        action="store_true", dest="pause_between_groups", default=None,
        help="""
            Move the plotter to the home position and wait for confirmation on
            the command-line before continuing to plot or cut after each
            `--cut` or `--plot` group. Will be remembered between groups.
        """
    )
    
    group.add_argument(
        "--no-pause-between-groups", "-u",
        action="store_false", dest="pause_between_groups",
        help="""
            Do not pause between groups when plotting or cutting. Will be
            remembered between groups.
        """
    )
    
    group.add_argument(
        "--repeat", "-N",
        nargs=1, type=int, default=1, metavar="NUM-TIMES",
        help="""
            Plot or cut the current group NUM-TIMES. This argument is reset to
            '1' in every group.
        """
    )
    
    return parser

class PlotMode(Enum):
    """The plotting/cutting mode selected."""
    
    plot = "plot"
    cut = "cut"


@attrs(frozen=True)
class PlotParameters(object):
    """
    This object contains a set of parameters which describes a desired plotting
    operation.
    """
    
    plot_mode = attrib()
    """
    Plotting mode to use; one of :py:class:`PlotMode`.
    """
    
    filter_layer = attrib()
    """
    A list of compiled Regex objects to try and match to Inkscape layer
    names or None if no layer filter should be used.
    """
    
    filter_id = attrib()
    """
    A list of objcet IDs to include in the plot or None if no ID filtering is
    required.
    """
    
    filter_class = attrib()
    """
    A list of class names of objects to include in the plot or None if no class
    filtering is required.
    """
    
    filter_colour = attrib()
    """
    A list of (r, g, b, a) stroke colours (with values in range 0.0 to 1.0) to
    include or None if no colour filtering is required.
    """
    
    filter_width = attrib()
    """
    A list of stroke widths (in mm) to include or None if no stroke width
    filtering is required.
    """
    
    speed = attrib()
    """
    The speed at which the plotter should move in mm/s.
    """
    
    force = attrib()
    """
    The force with which plotter should press in grams.
    """
    
    inside_first = attrib()
    """
    Bool. Should internal lines be cut before containing lines?
    """
    
    fast_order = attrib()
    """
    Bool. Should lines be sorted to reduce plotting time?
    """
    
    regmarks_width = attrib()
    """
    Width of the regmarked area (in mm) or None if not found/known.
    """
    
    regmarks_height = attrib()
    """
    Height of the regmarked area (in mm) or None if not found/known.
    """
    
    regmarks_x_offset = attrib()
    """
    The x-offset of the top-left registration mark or None if not found/known.
    """
    
    regmarks_y_offset = attrib()
    """
    The y-offset of the top-left registration mark or None if not found/known.
    """
    
    include_regmarks = attrib()
    """
    Bool. Should registration marks be included in the plotted/cut output?
    """
    
    use_regmarks = attrib()
    """
    Bool. Should the device search for registration marks?
    """
    
    reregister_on_group = attrib()
    """
    Bool. Should the device re-register itself at the start of this group?
    """
    
    reregister_on_distance = attrib()
    """
    Re-register the device every this many mm moved in the 'Y' axis or None to
    disable.
    """
    
    pause_between_groups = attrib()
    """
    Bool. Should plotting pause and wait for user input before moving onto the
    next group?
    """


def guess_plot_mode(svg):
    """
    Given an SVG as an ElementTree, guess the PlotMode to use based on the
    layer names preesnt.
    """
    layer_names = [
        "/".join(name_tuple)
        for name_tuple in find_inkscape_layers(svg)
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


def has_known_layer_name(svg):
    """
    Has this SVG got an Inkscape layer matching a known layer name for
    cutting/plotting?
    """
    return any(
        ALL_LAYER_NAMES_REGEX.search("/".join(name_tuple))
        for name_tuple in find_inkscape_layers(svg)
    )


def absolute_or_percentage_within(string, low, high):
    """
    Parse a string giving a value as either an absolute float value or a
    percentage. Throws a ValueError when outside the stated range.
    """
    string = string.strip()
    
    # Parse value
    if string.endswith("%"):
        perc = float(string.rstrip("%")) / 100.0
        value = low + ((high - low) * perc)
    else:
        value = float(string)
    
    # Check range
    if not (low <= value <= high):
        raise ValueError("Value must be between {} and {}".format(
            low, high))
    
    return value


def parse_arguments(arguments=None):
    """
    Generate a series of :py:class:`PlotParameters` objects, one for each
    plotting group.
    """
    parser = make_argument_parser()
    args = parser.parse_args(arguments)
    
    # Load the SVG
    try:
        svg = ElementTree.parse(args.svg).getroot()
    except (IOError, SystemError):
        parser.error("SVG file must be exist and be readable.")
    except ElementTree.ParseError as e:
        parser.error("SVG file must be valid XML: {}".format(str(e)))
    
    svg_width, svg_height = get_svg_page_size(svg)
    logging.info("Loaded %f x %f mm SVG.", svg_width, svg_height)
    
    guessed_plot_mode = guess_plot_mode(svg)
    if guessed_plot_mode is None:
        guessed_plot_mode = PlotMode.plot
    
    # Automatically use default filter if none provided
    some_filter_applied = (
        not args.all or
        args.layer is not None or
        args.id is not None or
        args.class_name is not None or
        args.colour is not None or
        args.width is not None
    )
    if not some_filter_applied:
        if has_known_layer_name(svg):
            args.layer = [ALL_LAYER_NAMES_REGEX.pattern]
        else:
            args.all = True
    
    # Parse layer regexes
    if args.layer:
        try:
            args.layer = [re.compile(r, re.IGNORECASE) for r in args.layer]
        except re.error as e:
            parser.error(
                "--layer arguments must be valid regular expressions ({})".format(
                    str(e)))
    
    # Parse colours
    if args.colour:
        try:
            args.colour = list(map(css_colour_to_rgba, args.colour))
        except ValueError as e:
            parser.error(
                "--colour arguments must be valid CSS colours ({})".format(
                    str(e)))
    
    # Parse thicknesses
    if args.width:
        try:
            args.width = [css_dimension_to_mm(w,
                                              width_mm=svg_width,
                                              height_mm=svg_height)
                          for w in  args.width]
        except ValueError as e:
            parser.error(
                "--width arguments must be valid CSS dimension ({})".format(
                    str(e)))
    
    # Validate and set default speed
    XXX_LOW = 10
    XXX_HIGH = 200
    try:
        args.speed = absolute_or_percentage_within(args.speed or "100%",
                                                   XXX_LOW, XXX_HIGH)
    except ValueError as e:
        parser.error(
            "--speed arguments must be valid ({})".format(str(e)))
    
    # Validate and set default force
    try:
        args.force = absolute_or_percentage_within(args.force or "100%",
                                                   XXX_LOW, XXX_HIGH)
    except ValueError as e:
        parser.error(
            "--force arguments must be valid ({})".format(str(e)))
    
    # Defaults for ordering params
    if args.inside_first is None:
        if guessed_plot_mode == PlotMode.cut:
            args.inside_first = True
        elif guessed_plot_mode == PlotMode.plot:
            args.inside_first = False
    if args.fast_order is None:
        args.fast_order = True
    
    # Find regmarks in SVG
    
    # Parse manual regmark values
    if isinstance(args.regmarks, list):
        try:
            args.regmarks = [css_dimension_to_mm(d,
                                              width_mm=svg_width,
                                              height_mm=svg_height)
                          for d in  args.regmarks]
        except ValueError as e:
            parser.error(
                "--manual-regmarks arguments must be valid CSS dimension ({})".format(
                    str(e)))
    
    #initial_params = PlotParameters(
    #    plot_mode=guessed_plot_mode,
    #    filter_layer=args.layer,
    #    filter_id=args.id,
    #    filter_class=args.class_name,
    #    filter_colour=args.colour,
    #    filter_width=args.width,
    #)

parse_arguments()
