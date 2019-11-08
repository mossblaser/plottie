"""
The ``plottie`` command line interface.
"""

import sys

import re

import time

from xml.etree import ElementTree

from argparse import ArgumentParser

from functools import partial

from svgoutline import svg_to_outlines, get_svg_page_size

import py_silhouette

from plottie.dummy_device import DummyDevice

from plottie.plot_mode_heuristics import (
    CUT_LAYER_NAMES_REGEX,
    PLOT_LAYER_NAMES_REGEX,
    PlotMode,
    guess_plot_mode,
)

from plottie.svg_utils import (
    is_inkscape_layer,
    get_inkscape_layer_label,
    css_dimension_to_mm,
    css_colour_to_rgba,
    make_nodes_visible,
)

from plottie.regmarks import (
    RegmarkSpecification,
    find_regmarks,
)

from plottie.inside_first import group_inside_first

from plottie.line_ordering import optimise_lines

import logging


DEFAULT_TOOL_FORCE_PERC = 0.2
"""
Default force to use (in range 0 to 1, a proportion of the device's supported
range).
"""

DEFAULT_TOOL_SPEED_PERC = 1.0
"""
Default speed to use (in range 0 to 1, a proportion of the device's supported
range).
"""


def make_layer_matcher(regex):
    """
    Return a function which takes a ElementTree node and tests whether it is an
    Inkscape layer with a name matching the specified regex.
    """
    regex = re.compile(regex, re.IGNORECASE)
    
    def matcher(node):
        if not is_inkscape_layer(node):
            return False
        if not regex.match(get_inkscape_layer_label(node)):
            return False
        return True
    
    return matcher


def make_id_matcher(id):
    """
    Return a function which takes a ElementTree node and tests whether it has
    the specified ID.
    """
    def matcher(node):
        return node.attrib.get("id") == id
    
    return matcher


def make_class_matcher(classname):
    """
    Return a function which takes a ElementTree node and tests whether it has
    the specified class.
    """
    def matcher(node):
        return classname in node.attrib.get("class", "").split()
    
    return matcher


def make_argument_parser():
    """
    Return a fully configured :py:class:`argparse.ArgumentParser` instance.
    """
    parser = ArgumentParser(description="""
        Plot and cut SVG files using a Silhouette desktop plotter/cutter.
    """)
    
    parser.add_argument(
        "svg", nargs="?",
        help="""
            The SVG file to plot or cut.
        """,
    )
    action = parser.add_argument_group(
        "action arguments",
        description="""
            Select what mode the plotter should use: cutting or plotting mode.
            If neither argument is used, plottie will attempt to guess whether
            cutting or plotting is required based on Inkscape layer names found
            in the input SVG and, failing that, will assume cutting.  In
            cutting mode, additional movements will be made by the plotter to
            compensate for the movement of the knife within the cartridge.
        """
    ).add_mutually_exclusive_group()
    
    action.add_argument(
        "--cut", "-c",
        action="store_const", dest="plot_mode", const=PlotMode.cut,
    )
    
    action.add_argument(
        "--plot", "-p",
        action="store_const", dest="plot_mode", const=PlotMode.plot,
    )
    
    # #########################################################################
    
    device_selection = parser.add_argument_group(
        "device selection arguments",
    )
    
    device_selection.add_argument(
        "--device", "-d",
        type=str, default="0",
        help="""
            Specify the name (or number) of the device to use. (See
            --list-devices for device names and numbers). If this argument is
            not given, the first device discovered will be used.
        """
    )
    
    device_selection.add_argument(
        "--list-devices", "--ls",
        action="store_true",
        help="""
            Discover and list the devices connected to this machine and exit.
        """
    )
    
    device_selection.add_argument(
        "--use-dummy-device", "-D",
        nargs="?", metavar="FILENAME", default=False,
        help="""
            If this option is given, a dummy device (called 'Dummy Device')
            will be added to the list of discovered devices and will be used by
            default. When a filename is given, the cutting or plotting commands
            sent to the device will be written to the specified file in SVG
            format. Otherwise, all cutting and plotting commands will be
            ignored.
        """
    )
    
    # #########################################################################
    
    object_visibility = parser.add_argument_group(
        "object visibility arguments",
        description="""
            These options may be used to control which parts of the SVG will be
            plotted or cut out. The default behaviour for Inkscape SVGs is to
            select only layers whose names match the regular expression '{}'
            when cutting or '{}' when plotting (as if specified via --layer).
            If no matching Inkscape layers are found, `--all` mode is used.
            Alternatively, the parts of the SVG to plot may be specified
            explicitly using a combination of the following arguments.
        """.format(
            CUT_LAYER_NAMES_REGEX.pattern,
            PLOT_LAYER_NAMES_REGEX.pattern,
        )
    )
    
    object_visibility.add_argument(
        "--all", "-a",
        action="store_true",
        help="""
            Plot or cut outlines visible in the unchanged SVG.
        """,
    )
    
    object_visibility.add_argument(
        "--layer", "-l",
        type=make_layer_matcher, metavar="REGEX",
        dest="visible_object_matchers", action="append",
        help="""
            Plot or cut visible outlines only on the Inkscape layers whose
            names match the provided case-insensitive regex. If any matching
            layers are not visible, they will be made visible. May be given
            several times to select multiple layers to plot.
        """,
    )
    
    object_visibility.add_argument(
        "--id", "-i",
        type=make_id_matcher,
        dest="visible_object_matchers", action="append",
        help="""
            Plot or cut only visible outlines for SVG elements which have the
            specified object ID (or are visible children of that object). May
            be given several times to select multiple IDs to plot.
        """,
    )
    
    object_visibility.add_argument(
        "--class", "-s",
        type=make_class_matcher,
        dest="visible_object_matchers", action="append",
        help="""
            Plot or cut only visible outlines for SVG elements which have the
            specified class (or are visible children of an object with that
            class). May be given several times to select multiple IDs to plot.
        """,
    )
    
    # #########################################################################
    
    line_selection = parser.add_argument_group("line selection arguments")
    
    line_selection.add_argument(
        "--colour", "--color", "-C",
        type=css_colour_to_rgba, action="append",
        help="""
            Plot or cut only outlines with the listed stroke colour. Accepts
            CSS-style colour codes. May be given multiple times to include
            lines with multiple stroke colours. Lines with gradient or
            patterned strokes will be ignored. If not specified, all stroked
            lines (of all colours) will be plotted or cut.
        """,
    )
    
    # #########################################################################
    
    plotting_parameters = parser.add_argument_group(
        "plotting parameter arguments",
    )
    
    plotting_parameters.add_argument(
        "--speed", "-S",
        type=str, default="{:.0f}%".format(DEFAULT_TOOL_SPEED_PERC*100),
        help="""
            The speed with which to plot or cut. Either a number
            given in mm/s or a percentage ending with a '%%' symbol giving the
            percentage of the supported speed to run at. Defaults to
            %(default)s.
        """,
    )
    
    plotting_parameters.add_argument(
        "--force", "-F",
        type=str, default="{:.0f}%".format(DEFAULT_TOOL_FORCE_PERC*100),
        help="""
            The force with which to plot or cut. Either a number given in grams
            or a percentage ending with a '%%' symbol giving the percentage of
            the maximum supported force to apply. Defaults to
            %(default)s.
        """,
    )
    
    # #########################################################################
    
    ordering_parameters = parser.add_argument_group("plotting and cutting order arguments")
    
    ordering_parameters.add_argument(
        "--inside-first",
        action="store_true", dest="inside_first", default=None,
        help="""
            If some lines and shapes are contained within others, cut or plot
            these first. Inside first mode will be disabled by default in
            `--plot` mode and enabled by default for `--cut` mode. See also
            `--no-inside-first`.
        """,
    )
    
    ordering_parameters.add_argument(
        "--no-inside-first",
        action="store_false", dest="inside_first",
        help="""
            Don't try to plot or cut lines and shapes contained within others
            first. See also `--inside-first`.
        """,
    )
    
    ordering_parameters.add_argument(
        "--fast-order",
        action="store_true", dest="fast_order", default=True,
        help="""
            If specified, plot or cut paths in an order which attempts to
            reduce the time spent moving. Fast ordering is used by default.
            Opposite of `--native-order`.
        """,
    )
    
    ordering_parameters.add_argument(
        "--native-order",
        action="store_false", dest="fast_order",
        help="""
            If specified, plot/cuts paths in the order they appear in the input
            file.  Opposite of `--fast-order`.
        """,
    )
    
    # #########################################################################
    
    registration_parameters = parser.add_argument_group("registration arguments")
    
    registration_parameters.add_argument(
        "--regmarks", "-r",
        action="store_true", dest="regmarks", default=None,
        help="""
            Force detection of registration marks in the input SVG and throw an
            error if none are found. (By default registration marks will be
            used if found but no error is thrown if they are not). The
            registration marks must be visible and drawn as a 5x5mm
            stroked-and-filled black square (accounting for stroke thickness)
            at the top left and a pair of 'L' brackets 20x20mm at the bottom
            left and top right. Strokes should be black and 0.5mm thick. The
            registration marks will be excluded from plotting or cutting
            commands unless `--include-regmarks` is used.  This is the default
            mode if registration marks are detected in the design.
        """,
    )
    
    registration_parameters.add_argument(
        "--no-regmarks", "-R",
        action="store_false", dest="regmarks",
        help="""
            Disables auto-detection of registration marks in the input SVG.
        """,
    )
    
    registration_parameters.add_argument(
        "--manual-regmarks",
        nargs=4,
        metavar=("X-OFFSET", "Y-OFFSET", "WIDTH", "HEIGHT"),
        dest="regmarks",
        help="""
            Command the plotter to find registration marks denoting an area WIDTH x
            HEIGHT which is (X-OFFSET, Y-OFFSET) from the top-left of the input
            file. CSS-style absolute units should be used for all coordinates and
            dimensions (e.g.  '3mm'). Registration marks at the specified
            coordinates will be automatically removed from plotting/cutting paths
            unless `--include-regmarks` is used. The registration marks will be
            assumed to have 20mm brackets with 0.5mm black strokes.
        """,
    )
    
    registration_parameters.add_argument(
        "--include-regmarks",
        action="store_true", dest="include_regmarks", default=False,
        help="""
            Don't remove registration marks from the SVG before plotting or
            cutting.
        """,
    )
    
    return parser


def enumerate_devices(include_dummy=False, dummy_filename=None):
    """
    Enumerate all connected devices (including a dummy device, if specified).
    
    Returns
    =======
    [(name, func), ...]
        A list of names and :py:class:`py_silhouette.Device`-creating
        functions.
    """
    devices = []
    
    for device, params in py_silhouette.enumerate_devices():
        devices.append((
            params.product_name,
            partial(py_silhouette.SilhouetteDevice, device, params),
        ))
    
    if include_dummy:
        devices.insert(0, (
            "Dummy Device",
            partial(DummyDevice, dummy_filename),
        ))
    
    return devices


def print_device_list(include_dummy=False):
    """
    Print a (numbered) list of connected devices to stdout.
    """
    for number, (name, _) in enumerate(enumerate_devices(include_dummy)):
        print("{}: {}".format(number, name))


def parse_svg_argument(parser, args):
    if args.svg is None:
        parser.error("SVG filename required.")
    try:
        args.svg = ElementTree.parse(args.svg).getroot()
    except (IOError, SystemError):
        parser.error("{} does not exist or cannot be read".format(args.svg))
    except ElementTree.ParseError as e:
        parser.error("SVG file must be valid XML: {}".format(str(e)))
    logging.info("Loaded SVG")


def parse_device_arguments(parser, args):
    devices = enumerate_devices(
        args.use_dummy_device is not False,
        args.use_dummy_device,
    )
    if len(devices) == 0:
        parser.error("No connected devices found.")
    
    device_name = None
    connect_fn = None
    try:
        device_number = int(args.device)
        try:
            device_name, connect_fn = devices[device_number]
        except IndexError:
            pass
    except ValueError:
        device_string = args.device
        for name, fn in devices:
            if name.lower().startswith(device_string.lower()):
                device_name = name
                connect_fn = fn
                break
    
    if connect_fn is None:
        parser.error("Device {!r} not found.".format(args.device))
    
    logging.info("Connecting to device %s.", device_name)
    args.device = connect_fn()
    logging.info("Connected!")


def parse_visibility_arguments(parser, args):
    # Check that filters don't conflict
    if args.visible_object_matchers is not None and args.all:
        parser.error("""
            --all cannot be used with --layer, --id or --class
        """)
    
    # Add default filters
    if not args.all and args.visible_object_matchers is None:
        # Check to see if at least one layer is found and matched by the
        # default regexes before adding that as a filter (if not don't add any
        # filters)
        if args.plot_mode == PlotMode.cut:
            matcher = make_layer_matcher(CUT_LAYER_NAMES_REGEX.pattern)
        else:
            matcher = make_layer_matcher(PLOT_LAYER_NAMES_REGEX.pattern)
        if list(filter(matcher, args.svg.iter())):
            args.visible_object_matchers = [matcher]


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


def parse_speed_and_force(parser, args):
    try:
        args.speed = absolute_or_percentage_within(
            args.speed,
            args.device.params.tool_speed_min,
            args.device.params.tool_speed_max)
    except ValueError as e:
        parser.error(
            "--speed arguments must be valid ({})".format(str(e)))
    try:
        args.force = absolute_or_percentage_within(
            args.force,
            args.device.params.tool_force_min,
            args.device.params.tool_force_max)
    except ValueError as e:
        parser.error(
            "--force arguments must be valid ({})".format(str(e)))


def parse_regmarks(parser, args):
    if args.regmarks is False:
        # Regmark use is disabled
        args.regmarks = None
    elif isinstance(args.regmarks, list):
        # Manual regmarks
        try:
            svg_width, svg_height = get_svg_page_size(args.svg)
            x, y, width, height = (
                css_dimension_to_mm(
                    d, width_mm=svg_width, height_mm=svg_height)
                for d in args.regmarks
            )
            args.regmarks = RegmarkSpecification(x, y, width, height)
        except ValueError as e:
            parser.error(
                "--manual-regmarks arguments must be valid CSS dimensions ({})".format(
                    str(e)))
    else:
        # Automatic regmarks
        discovered_regmarks = find_regmarks(
            svg_to_outlines(args.svg),
            required_box_size=5.0,
        )
        
        if args.regmarks is True:
            # Automatic regmarks explicitly requested
            if discovered_regmarks is None:
                parser.error("""
                    --regmarks specified but no registration marks were found in
                    the input.  Check that: 1) all regmarks are visible 2) drawn
                    opaque in black 3) drawn with opaque black strokes (including
                    the box) 4) all brackets are the same length and thickness.
                """)
            else:
                args.regmarks = discovered_regmarks
        else:
            # Default mode: use regmarks if discovered but otherwise don't
            # bother
            args.regmarks = discovered_regmarks


def parse_arguments(arg_strings=None):
    """
    Parse a set of commandline arguments returning the resulting options in an
    argparse namespace with the following entries:
    
    * svg: The specified SVG file loaded as an ElementTree.
    * device: The connected :py:class:`py_silhouette.Device`.
    * plot_mode: One of :py:class:`PlotMode`
    * speed: A device speed in mm/sec
    * force: A device force in grams
    * inside_first: bool
    * fast_order: bool
    * regmarks: :py:class:`RegmarkSpecification` or None.
    * include_regmarks: bool
    * colour: list of (r, g, b, a) tuples of colours to be plotted or None if
      no colour filtering is to be applied.
    * visible_object_matchers: None or a list of ElementTree node test
      functions specifying which SVG elements should be made visible.
    """
    parser = make_argument_parser()
    args = parser.parse_args(arg_strings)
    
    if args.list_devices:
        print_device_list(args.use_dummy_device)
        return None
    
    parse_svg_argument(parser, args)
    
    # Guess default plot mode (if not specified)
    if args.plot_mode is None:
        args.plot_mode = guess_plot_mode(args.svg) or PlotMode.cut
        logging.info("Guessed plotting mode as %s", args.plot_mode.value)
    
    # Parse/validate filter arguments
    parse_visibility_arguments(parser, args)
    
    # Select device
    parse_device_arguments(parser, args)
    
    # Parse speed and force settings
    parse_speed_and_force(parser, args)
    
    # Set default inside-first
    if args.inside_first is None:
        args.inside_first = True if args.plot_mode == PlotMode.cut else False
    
    # Parse and detect regmarks
    parse_regmarks(parser, args)
    
    return args


def args_to_outlines(args):
    """
    Convert the SVG loaded by :py:func:`parse_arguments` into a series of line
    segments according to the command-line options given.
    """
    if args.visible_object_matchers:
        logging.info("Filtering SVG...")
        make_nodes_visible(
            args.svg,
            lambda n: any(m(n) for m in args.visible_object_matchers),
        )
    
    logging.info("Converting SVG into line segments...")
    filtered_lines = [
        line
        for colour, thickness, line in svg_to_outlines(args.svg)
        if (
            # Filter by colour
            (args.colour is None or colour in args.colour) and
            # Remove regmarks
            (
                args.include_regmarks or
                args.regmarks is None or
                not args.regmarks.is_line_part_of_regmark(
                    colour, thickness, line,
                )
            )
        )
    ]
    
    # Offset line coordinates according to registration marks
    if args.regmarks is not None:
        filtered_lines = [
            [
                (
                    x - args.regmarks.x,
                    y - args.regmarks.y,
                )
                for x, y in line
            ]
            for line in filtered_lines
        ]
    
    if args.inside_first:
        logging.info("Ordering inner lines first...")
        grouped_lines = group_inside_first(filtered_lines)
    else:
        grouped_lines = [filtered_lines]
    
    optimised_lines = []
    if args.fast_order:
        logging.info("Optimising line order...")
        cur_pos = (0, 0)
        for line_group in grouped_lines:
            optimised_lines.extend(optimise_lines(line_group, cur_pos))
            if optimised_lines:
                cur_pos = optimised_lines[-1][-1]
    else:
        for line_group in grouped_lines:
            optimised_lines.extend(line_group)
    
    logging.info(
        "Converted SVG into %d lines and %d line segments",
        len(optimised_lines),
        sum(map(len, optimised_lines)) - len(optimised_lines),
    )
    
    return optimised_lines


def zero_on_regmarks(device, regmarks):
    """
    Attempt to find and zero on the registration marks specified. Will allow
    the user to keep re-trying interactively.
    """
    while True:
        logging.info("Searching for registration marks...")
        try:
            device.zero_on_registration_mark(
                regmarks.width,
                regmarks.height,
                box_size=regmarks.box_size,
                line_thickness=regmarks.line_thickness,
                line_length=regmarks.line_length,
            )
            return
        except py_silhouette.RegistrationMarkNotFoundError:
            sys.stderr.write("Registration marks not found, try again?\n")
            sys.stderr.write("Y/n> ")
            char = input().strip().lower()
            if not char or char.startswith("y"):
                continue
            else:
                sys.exit(1)


def main(args=None):
    args = parse_arguments(args)
    
    if args is None:
        return 0
    
    lines = args_to_outlines(args)
    
    if args.regmarks:
        zero_on_regmarks(args.device, args.regmarks)
    
    args.device.set_force(args.force)
    args.device.set_speed(args.speed)
    args.device.set_tool_diameter(
        args.device.params.tool_diameters["Knife"]
        if args.plot_mode == PlotMode.cut else
        args.device.params.tool_diameters["Pen"]
    )
    args.device.flush()
    
    for line in lines:
        for i, (x, y) in enumerate(line):
            pen_down = i > 0
            args.device.move_to(x, y, pen_down)
        args.device.flush()
    
    args.device.move_home()
    args.device.flush()
    
    while args.device.get_state() == py_silhouette.DeviceState.moving:
        time.sleep(0.5)
    
    return 0


if __name__ == "__main__":
    main()
