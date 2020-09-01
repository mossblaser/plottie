import pytest

from mock import Mock

from xml.etree import ElementTree

import shlex

from shapely.geometry import MultiLineString
from shapely.affinity import translate
from shapely.ops import cascaded_union

from plottie.plot_mode_heuristics import PlotMode

from plottie.dummy_device import DummyDevice

from plottie.regmarks import RegmarkSpecification

import plottie.cli as plottie_cli

from plottie.cli import (
    make_layer_matcher,
    make_id_matcher,
    make_class_matcher,
    make_argument_parser,
    parse_svg_argument,
    parse_device_arguments,
    parse_visibility_arguments,
    absolute_or_percentage_within,
    parse_speed_and_force,
    parse_regmarks,
    parse_arguments,
    args_to_outlines,
    main,
)


class TestMatchers(object):
    
    @pytest.fixture
    def svg(self):
        return ElementTree.fromstring("""<?xml version="1.0" encoding="UTF-8" standalone="no"?>
            <svg
              xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape">
            <g
               inkscape:groupmode="layer"
               id="layer1"
               inkscape:label="Foo bar">
            </g>
            <g
               inkscape:groupmode="layer"
               id="layer2"
               inkscape:label="Baz qux">
            </g>
            <g
               inkscape:groupmode="layer"
               id="layer3"
               class="hello there"
               inkscape:label="Quo arb">
            </g>
            </svg>
        """)
    
    def test_make_layer_matcher(self, svg):
        m = make_layer_matcher(".*.Oo.*")
        assert m(svg) is False
        assert m(svg.find(".//*[@id='layer1']")) is True
        assert m(svg.find(".//*[@id='layer2']")) is False
        assert m(svg.find(".//*[@id='layer3']")) is False
    
    def test_make_id_matcher(self, svg):
        m = make_id_matcher("layer2")
        assert m(svg) is False
        assert m(svg.find(".//*[@id='layer1']")) is False
        assert m(svg.find(".//*[@id='layer2']")) is True
        assert m(svg.find(".//*[@id='layer3']")) is False
    
    def test_make_class_matcher(self, svg):
        m = make_class_matcher("there")
        assert m(svg) is False
        assert m(svg.find(".//*[@id='layer1']")) is False
        assert m(svg.find(".//*[@id='layer2']")) is False
        assert m(svg.find(".//*[@id='layer3']")) is True


class TestParseSVGArgument(object):
    
    @pytest.fixture
    def parser(self):
        return make_argument_parser()
    
    def test_no_argument(self, parser, capsys):
        with pytest.raises(SystemExit):
            parse_svg_argument(parser, parser.parse_args([]))
        
        out, err = capsys.readouterr()
        
        assert "name" in err
    
    def test_missing_file(self, parser, tmpdir, capsys):
        non_existant = str(tmpdir.join("nope.svg"))
        
        with pytest.raises(SystemExit):
            parse_svg_argument(parser, parser.parse_args([non_existant]))
        
        out, err = capsys.readouterr()
        
        assert str(non_existant) in err
        assert "not exist" in err
    
    def test_invalid_svg(self, parser, tmpdir, capsys):
        filename = str(tmpdir.join("bad.svg"))
        
        with open(filename, "w") as f:
            f.write("fail")
        
        with pytest.raises(SystemExit):
            parse_svg_argument(parser, parser.parse_args([filename]))
        
        out, err = capsys.readouterr()
        
        assert "must be valid XML" in err
    
    def test_valid_svg(self, parser, tmpdir, capsys):
        filename = str(tmpdir.join("bad.svg"))
        
        with open(filename, "w") as f:
            f.write("<svg />")
        
        args = parser.parse_args([filename])
        
        parse_svg_argument(parser, args)
        
        assert isinstance(args.svg, ElementTree.Element)


class TestParseDeviceArguments(object):
    
    @pytest.fixture
    def enumerate_devices(self, monkeypatch):
        enumerate_devices = Mock(return_value=[])
        monkeypatch.setattr(plottie_cli, "enumerate_devices", enumerate_devices)
        return enumerate_devices
    
    def test_no_devices(self, enumerate_devices, capsys):
        enumerate_devices.return_value = []
        
        parser = make_argument_parser()
        args = parser.parse_args(["-"])
        
        with pytest.raises(SystemExit):
            parse_device_arguments(parser, args)
        
        out, err = capsys.readouterr()
        
        assert "No connected devices found" in err
    
    @pytest.fixture
    def mock_devices(self, enumerate_devices):
        enumerate_devices.return_value = [
            ("one", lambda: 100),
            ("two", lambda: 200),
        ]
    
    def test_use_first_by_default(self, mock_devices):
        parser = make_argument_parser()
        args = parser.parse_args(["-"])
        
        parse_device_arguments(parser, args)
        assert args.device == 100
    
    @pytest.mark.parametrize("arg,exp", [
        # By index
        (["--device", "0"], 100),
        (["--device", "1"], 200),
        # By name
        (["--device", "one"], 100),
        (["--device", "two"], 200),
        # By partial/case-insensitive name
        (["--device", "O"], 100),
        (["--device", "T"], 200),
    ])
    def test_specify_device(self, mock_devices, arg, exp):
        parser = make_argument_parser()
        args = parser.parse_args(["-"] + arg)
        
        parse_device_arguments(parser, args)
        assert args.device == exp
    
    @pytest.mark.parametrize("arg", [
        # Index out of range
        ["--device", "2"],
        # Undefined name
        ["--device", "foo"],
    ])
    def test_specify_missing_device(self, mock_devices, arg, capsys):
        parser = make_argument_parser()
        args = parser.parse_args(["-"] + arg)
        
        with pytest.raises(SystemExit):
            parse_device_arguments(parser, args)
        
        out, err = capsys.readouterr()
        
        assert "Device {!r} not found".format(arg[-1]) in err

class TestParseVisibilityArguments(object):
    
    @pytest.mark.parametrize("arg", [
        ["--layer", "Foo bar"],
        ["--id", "layer2"],
        ["--class", "hello"],
    ])
    def test_conflicts(self, arg, capsys):
        parser = make_argument_parser()
        args = parser.parse_args(["-", "--all"] + arg)
        
        with pytest.raises(SystemExit):
            parse_visibility_arguments(parser, args)
        
        out, err = capsys.readouterr()
        
        assert "--all cannot be used with" in err
    
    def test_pass_through_matchers(self):
        svg = ElementTree.fromstring("""<?xml version="1.0" encoding="UTF-8" standalone="no"?>
            <svg
              xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape">
            <g
               inkscape:groupmode="layer"
               id="layer1"
               inkscape:label="Foo bar">
            </g>
            <g
               inkscape:groupmode="layer"
               id="layer2"
               inkscape:label="Baz qux">
            </g>
            <g
               inkscape:groupmode="layer"
               id="layer3"
               class="hello there"
               inkscape:label="Quo arb">
            </g>
            </svg>
        """)
        
        parser = make_argument_parser()
        args = parser.parse_args([
            "-",
            "--layer", "Foo bar",
            "--id", "layer2",
            "--class", "hello",
        ])
        
        parse_visibility_arguments(parser, args)
        
        assert len(args.visible_object_matchers) == 3
        
        m = args.visible_object_matchers[0]
        assert m(svg) is False
        assert m(svg.find(".//*[@id='layer1']")) is True
        assert m(svg.find(".//*[@id='layer2']")) is False
        assert m(svg.find(".//*[@id='layer3']")) is False
        
        m = args.visible_object_matchers[1]
        assert m(svg) is False
        assert m(svg.find(".//*[@id='layer1']")) is False
        assert m(svg.find(".//*[@id='layer2']")) is True
        assert m(svg.find(".//*[@id='layer3']")) is False
        
        m = args.visible_object_matchers[2]
        assert m(svg) is False
        assert m(svg.find(".//*[@id='layer1']")) is False
        assert m(svg.find(".//*[@id='layer2']")) is False
        assert m(svg.find(".//*[@id='layer3']")) is True
    
    @pytest.mark.parametrize("plot_mode,layer_name", [
        (PlotMode.cut, "Cut"),
        (PlotMode.plot, "Plot"),
    ])
    def test_default_matcher(self, plot_mode, layer_name):
        svg = ElementTree.fromstring("""<?xml version="1.0" encoding="UTF-8" standalone="no"?>
            <svg
              xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape">
            <g
               inkscape:groupmode="layer"
               id="layer1"
               inkscape:label="{}">
            </g>
            <g
               inkscape:groupmode="layer"
               id="layer2"
               inkscape:label="Drawing">
            </g>
            </svg>
        """.format(layer_name))
        
        parser = make_argument_parser()
        args = parser.parse_args(["-"])
        
        args.svg = svg
        args.plot_mode = plot_mode
        
        parse_visibility_arguments(parser, args)
        
        assert len(args.visible_object_matchers) == 1
        
        m = args.visible_object_matchers[0]
        assert m(svg) is False
        assert m(svg.find(".//*[@id='layer1']")) is True
        assert m(svg.find(".//*[@id='layer2']")) is False
    
    @pytest.mark.parametrize("plot_mode", [
        PlotMode.cut,
        PlotMode.plot,
    ])
    def test_no_default_matcher_if_no_layers_match(self, plot_mode):
        svg = ElementTree.fromstring("""<?xml version="1.0" encoding="UTF-8" standalone="no"?>
            <svg
              xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape">
            <g
               inkscape:groupmode="layer"
               id="layer1"
               inkscape:label="Background">
            </g>
            <g
               inkscape:groupmode="layer"
               id="layer2"
               inkscape:label="Drawing">
            </g>
            </svg>
        """)
        
        parser = make_argument_parser()
        args = parser.parse_args(["-"])
        
        args.svg = svg
        args.plot_mode = plot_mode
        
        parse_visibility_arguments(parser, args)
        
        assert args.visible_object_matchers is None


class TestAbsoluteOrPercentageWithin(object):
    
    @pytest.mark.parametrize("string,exp", [
        # Values
        ("10000", 10000.0),
        ("10555.5", 10555.5),
        ("11000", 11000.0),
        # Percentages
        ("0%", 10000.0),
        ("55.55%", 10555.5),
        ("100%", 11000.0),
    ])
    def test_in_range(self, string, exp):
        assert absolute_or_percentage_within(string, 10000, 11000) == exp
    
    @pytest.mark.parametrize("string", [
        # Values
        "9999.9",
        "11000.1",
        # Percentages
        "-0.1%",
        "100.1%",
    ])
    def test_out_of_range(self, string):
        with pytest.raises(ValueError):
            absolute_or_percentage_within(string, 10000, 11000)


class TestSpeedForceAndDepth(object):
    
    def test_valid_speed(self):
        parser = make_argument_parser()
        args = parser.parse_args(["-", "--speed", "100%"])
        args.device = DummyDevice()
        parse_speed_and_force(parser, args)
        assert args.speed == args.device.params.tool_speed_max
    
    def test_valid_force(self):
        parser = make_argument_parser()
        args = parser.parse_args(["-", "--force", "100%"])
        args.device = DummyDevice()
        parse_speed_and_force(parser, args)
        assert args.force == args.device.params.tool_force_max
    
    def test_invalid_speed(self, capsys):
        parser = make_argument_parser()
        args = parser.parse_args(["-", "--speed", "101%"])
        args.device = DummyDevice()
        
        with pytest.raises(SystemExit):
            parse_speed_and_force(parser, args)
        
        out, err = capsys.readouterr()
        
        assert "--speed" in err
    
    def test_invalid_force(self, capsys):
        parser = make_argument_parser()
        args = parser.parse_args(["-", "--force", "101%"])
        args.device = DummyDevice()
        
        with pytest.raises(SystemExit):
            parse_speed_and_force(parser, args)
        
        out, err = capsys.readouterr()
        
        assert "--force" in err


class TestParseRegmarks(object):
    
    @pytest.fixture
    def svg(self):
        return ElementTree.fromstring("""<?xml version="1.0" encoding="UTF-8" standalone="no"?>
            <svg
              xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
              width="100mm"
              height="200mm"
            >
            </svg>
        """)
    
    @pytest.fixture
    def find_regmarks(self, monkeypatch):
        find_regmarks = Mock(return_value=RegmarkSpecification(
            x=100,
            y=200,
            width=300,
            height=400,
        ))
        monkeypatch.setattr(plottie_cli, "find_regmarks", find_regmarks)
        return find_regmarks
    
    def test_disable_regmarks(self):
        parser = make_argument_parser()
        args = parser.parse_args(["-", "--no-regmarks"])
        
        parse_regmarks(parser, args)
        
        assert args.regmarks is None
    
    def test_manual_regmarks(self, svg):
        parser = make_argument_parser()
        args = parser.parse_args(["-", "--manual-regmarks", "10mm", "20mm", "30mm", "40mm"])
        args.svg = svg
        
        parse_regmarks(parser, args)
        
        assert args.regmarks.x == 10
        assert args.regmarks.y == 20
        assert args.regmarks.width == 30
        assert args.regmarks.height == 40
    
    def test_invalid_manual_regmarks(self, svg, capsys):
        parser = make_argument_parser()
        args = parser.parse_args(["-", "--manual-regmarks", "10furlongs", "20mm", "30mm", "40mm"])
        args.svg = svg
        
        with pytest.raises(SystemExit):
            parse_regmarks(parser, args)
        
        out, err = capsys.readouterr()
        
        assert "--manual-regmarks" in err
    
    def test_automatic_regmarks_none_on_page(self, svg):
        parser = make_argument_parser()
        args = parser.parse_args(["-"])
        args.svg = svg
        
        parse_regmarks(parser, args)
        
        assert args.regmarks is None
    
    def test_automatic_regmarks_none_on_page_forced(self, svg, capsys):
        parser = make_argument_parser()
        args = parser.parse_args(["-", "--regmarks"])
        args.svg = svg
        
        with pytest.raises(SystemExit):
            parse_regmarks(parser, args)
        
        out, err = capsys.readouterr()
        
        assert "--regmarks" in err
    
    @pytest.mark.parametrize("force", [["--regmarks"], []])
    def test_automatic_regmarks(self, svg, find_regmarks, force):
        parser = make_argument_parser()
        args = parser.parse_args(["-"] + force)
        args.svg = svg
        
        parse_regmarks(parser, args)
        
        assert args.regmarks == find_regmarks()


class TestArgsToOutlines(object):
    
    @pytest.fixture
    def svg_string(self):
        return """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
            <svg
                xmlns="http://www.w3.org/2000/svg"
                xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
                width="100mm"
                height="200mm"
                viewBox="0 0 100 200"
            >
                <g
                    inkscape:groupmode="layer"
                    id="regmarks"
                    inkscape:label="Registration Marks"
                >
                    <path fill="black" stroke="black" stroke-width="1" d="
                        M10.5,10.5
                        L14.5,10.5
                        L14.5,14.5
                        L10.5,14.5
                        Z
                    " />
                    <path fill="none" stroke="black" stroke-width="1" d="
                        M69.5,10.5
                        L89.5,10.5
                        L89.5,30.5
                    " />
                    <path fill="none" stroke="black" stroke-width="1" d="
                        M10.5,69.5
                        L10.5,89.5
                        L30.5,89.5
                    " />
                </g>
                <g
                    inkscape:groupmode="layer"
                    id="cut"
                    inkscape:label="Cutting"
                >
                    <path fill="none" stroke="#FF0000" stroke-width="1" d="
                        M50,50
                        L60,60
                    " />
                </g>
                <g
                    inkscape:groupmode="layer"
                    id="print"
                    inkscape:label="Printing"
                >
                    <path fill="none" stroke="#00FF00" stroke-width="1" d="
                        M30,15
                        L30,85
                        L70,85
                        L70,15
                        Z
                    " />
                    <path fill="none" stroke="#0000FF" stroke-width="1" d="
                        M50,20
                        L60,30
                    " />
                </g>
            </svg>
        """
    
    @pytest.fixture
    def regmarks(self):
        return MultiLineString([
            [
                (10.5, 10.5),
                (14.5, 10.5),
                (14.5, 14.5),
                (10.5, 14.5),
                (10.5, 10.5),
            ],
            [
                (69.5, 10.5),
                (89.5, 10.5),
                (89.5, 30.5),
            ],
            [
                (10.5, 69.5),
                (10.5, 89.5),
                (30.5, 89.5),
            ],
        ])
    
    @pytest.fixture
    def red(self):
        return MultiLineString([[
            (50, 50),
            (60, 60),
        ]])
    
    @pytest.fixture
    def green(self):
        return MultiLineString([[
            (30, 15),
            (30, 85),
            (70, 85),
            (70, 15),
            (30, 15),
        ]])
    
    @pytest.fixture
    def blue(self):
        return MultiLineString([[
            (50, 20),
            (60, 30),
        ]])
    
    def dereg(self, geom):
        # Translate to compensate for regmarks offset
        return translate(
            geom,
            -10,
            -10,
        )
    
    @pytest.fixture
    def make_args(self, tmpdir, svg_string):
        def make_args(arg_string):
            filename = str(tmpdir.join("test.svg"))
            
            with open(filename, "w") as f:
                f.write(svg_string)
            
            return parse_arguments([
                filename,
                "--use-dummy-device",
            ] + shlex.split(arg_string))
        
        return make_args
    
    def test_defaults(self, make_args, red):
        # By default:
        # * The registration marks should be used
        # * Just the cutting layer should be used (red line)
        # * The red line should be drawn from the (0, 0) end first
        args = make_args("")
        
        outlines = MultiLineString(args_to_outlines(args))
        expected = self.dereg(red)
        assert outlines == expected
    
    def test_regmarks_disabled(self, make_args, red):
        # When regmarks are disabled
        # * The registration marks should not be used (and the coordinates
        #   should not be offset)
        # * Just the cutting layer should be used (red line) as the regmarks
        #   aren't on a cutting layer anyway.
        # * The red line should be drawn from the (0, 0) end first
        args = make_args("--no-regmarks")
        
        outlines = MultiLineString(args_to_outlines(args))
        expected = red
        assert outlines == expected
    
    def test_colour(self, make_args, blue):
        # Check that colour filtering works
        args = make_args("--all --color #0000FF")
        
        outlines = MultiLineString(args_to_outlines(args))
        expected = self.dereg(blue)
        assert not outlines.is_empty
        assert outlines.difference(expected).is_empty
    
    def test_regmarks_included_when_not_used(self, make_args, regmarks, red, green, blue):
        args = make_args("--all --no-regmarks")
        
        outlines = MultiLineString(args_to_outlines(args))
        expected = cascaded_union([
            regmarks,
            red,
            green,
            blue,
        ])
        assert not outlines.is_empty
        assert outlines.difference(expected).is_empty
    
    def test_include_regmarks_option(self, make_args, regmarks, red, green, blue):
        args = make_args("--all --include-regmarks")
        
        outlines = MultiLineString(args_to_outlines(args))
        expected = cascaded_union([
            self.dereg(regmarks),
            self.dereg(red),
            self.dereg(green),
            self.dereg(blue),
        ])
        assert not outlines.is_empty
        assert outlines.difference(expected).is_empty
    
    def test_exclude_regmarks(self, make_args, regmarks, red, green, blue):
        args = make_args("--all")
        
        outlines = MultiLineString(args_to_outlines(args))
        expected = cascaded_union([
            self.dereg(red),
            self.dereg(green),
            self.dereg(blue),
        ])
        assert not outlines.is_empty
        assert outlines.difference(expected).is_empty
    
    def test_inside_first_and_optimised(self, make_args, red, green, blue):
        args = make_args("--all --no-over-cut")
        
        # Re-order points so definition starts with bottom-right corner (which
        # is nearest point to end of red line)
        green_shifted = MultiLineString([[
            (70, 85),
            (70, 15),
            (30, 15),
            (30, 85),
            (70, 85),
        ]])
        # Sanity check
        assert green_shifted.difference(green).is_empty
        
        outlines = MultiLineString(args_to_outlines(args))
        expected = MultiLineString(
            list(self.dereg(blue).geoms) +
            list(self.dereg(red).geoms) +
            list(self.dereg(green_shifted).geoms)
        )
        assert outlines == expected
    
    @pytest.mark.parametrize("extra_args", [
        # In plot mode, no over-cutting should be done
        "--plot",
        # Explicitly disable over-cutting
        "--cut --no-over-cut",
    ])
    def test_no_over_cut(self, make_args, red, green, blue, extra_args):
        args = make_args("--all --fast-order --inside-first " + extra_args)
        green_shifted = MultiLineString([[
            (70, 85),
            (70, 15),
            (30, 15),
            (30, 85),
            (70, 85),
        ]])
        # Sanity check
        assert green_shifted.difference(green).is_empty
        
        outlines = MultiLineString(args_to_outlines(args))
        expected = MultiLineString(
            list(self.dereg(blue).geoms) +
            list(self.dereg(red).geoms) +
            list(self.dereg(green_shifted).geoms)
        )
        assert outlines == expected
    
    @pytest.mark.parametrize("extra_args,exp_over_cut", [
        # Over-cut used by default when cutting
        ("--cut", 1.0),
        # Default distance
        ("--cut --over-cut", 1.0),
        # Distance overridden
        ("--cut --over-cut 2.5", 2.5),
        # Custom over-cut specified, overriding default plot mode of no overcut
        ("--plot --over-cut", 1.0),
        ("--plot --over-cut 2.5", 2.5),
    ])
    def test_over_cut(self, make_args, red, green, blue, extra_args, exp_over_cut):
        args = make_args("--all --fast-order --inside-first " + extra_args)
        green_shifted = MultiLineString([[
            (70, 85),
            (70, 15),
            (30, 15),
            (30, 85),
            (70, 85),
            (70, 85 - exp_over_cut),
        ]])
        # Sanity check
        assert green_shifted.difference(green).is_empty
        
        outlines = MultiLineString(args_to_outlines(args))
        expected = MultiLineString(
            list(self.dereg(blue).geoms) +
            list(self.dereg(red).geoms) +
            list(self.dereg(green_shifted).geoms)
        )
        assert outlines == expected
    
    def test_no_inside_first_and_optimised(self, make_args, red, green, blue):
        args = make_args("--all --no-inside-first --no-over-cut")
        
        outlines = MultiLineString(args_to_outlines(args))
        expected = MultiLineString(
            list(self.dereg(green).geoms) +
            list(self.dereg(blue).geoms) +
            list(self.dereg(red).geoms)
        )
        assert outlines == expected
    
    def test_no_inside_first_native_order(self, make_args, red, green, blue):
        args = make_args("--all --no-inside-first --native-order --no-over-cut")
        
        outlines = MultiLineString(args_to_outlines(args))
        expected = MultiLineString(
            list(self.dereg(red).geoms) +
            list(self.dereg(green).geoms) +
            list(self.dereg(blue).geoms)
        )
        assert outlines == expected
    
    def test_native_order(self, make_args, red, green, blue):
        args = make_args("--all --native-order --no-over-cut")
        
        outlines = MultiLineString(args_to_outlines(args))
        expected = MultiLineString(
            list(self.dereg(red).geoms) +
            list(self.dereg(blue).geoms) +
            list(self.dereg(green).geoms)
        )
        assert outlines == expected


def test_integration(tmpdir):
    # Just a simple test which feeds a test picture and checks the output of
    # the dummy SVG.
    input_filename = str(tmpdir.join("input.svg"))
    output_filename = str(tmpdir.join("output.svg"))
    
    with open(input_filename, "w") as f:
        f.write("""<?xml version="1.0" encoding="UTF-8" standalone="no"?>
            <svg
                xmlns="http://www.w3.org/2000/svg"
                xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
                width="100mm"
                height="200mm"
                viewBox="0 0 100 200"
            >
                <g
                    inkscape:groupmode="layer"
                    id="regmarks"
                    inkscape:label="Registration Marks"
                >
                    <path fill="black" stroke="black" stroke-width="1" d="
                        M10.5,10.5
                        L14.5,10.5
                        L14.5,14.5
                        L10.5,14.5
                        Z
                    " />
                    <path fill="none" stroke="black" stroke-width="1" d="
                        M69.5,10.5
                        L89.5,10.5
                        L89.5,30.5
                    " />
                    <path fill="none" stroke="black" stroke-width="1" d="
                        M10.5,69.5
                        L10.5,89.5
                        L30.5,89.5
                    " />
                </g>
                <g
                    inkscape:groupmode="layer"
                    id="cut"
                    inkscape:label="Cutting"
                >
                    <path fill="none" stroke="#FF0000" stroke-width="1" d="
                        M50,50
                        L60,60
                    " />
                </g>
            </svg>
        """)
    
    assert main([input_filename, "--use-dummy-device", output_filename]) == 0
    
    assert open(output_filename).read() == (
        '<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n'
        '<svg\n'
        '  xmlns="http://www.w3.org/2000/svg"\n'
        '  xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"\n'
        '  width="80.0mm"\n'
        '  height="80.0mm"\n'
        '  viewBox="0 0 80.0 80.0"\n'
        '>\n'
        '  <!-- tool_diameter = 0.9 mm -->\n'
        '  <!-- speed = 1000.0 mm/s -->\n'
        '  <!-- force = 51.800000000000004 g -->\n'
        '  <!-- regmarks_used = True -->\n'
        '  <path\n'
        '    d="M40.0,40.0L50.0,50.0"\n'
        '    stroke="hsl(0, 100%, 50%)"\n'
        '    stroke-width="0.2"\n'
        '  />\n'
        '</svg>\n'
    )
