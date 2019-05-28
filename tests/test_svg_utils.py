import pytest

from xml.etree import ElementTree

from plottie.xml_utils import read_xml_file

from plottie.svg_utils import (
    css_dimension_to_mm,
    css_colour_to_rgba,
    is_inkscape_layer,
    get_inkscape_layer_label,
    is_visible,
    set_visibility,
    make_nodes_visible,
)


class TestCssDimensionToMm(object):
    
    @pytest.mark.parametrize("ppmm", [96.0/25.4, 90.0/25.4])
    def test_mm_and_formatting(self, ppmm):
        # Integer and float support
        assert css_dimension_to_mm("123mm", ppmm) == 123
        assert css_dimension_to_mm("1.23mm", ppmm) == 1.23
        
        # With optional plus
        assert css_dimension_to_mm("+1mm", ppmm) == 1
        
        # With whitespace
        assert css_dimension_to_mm(" 1 mm ", ppmm) == 1
        assert css_dimension_to_mm(" + 1 mm ", ppmm) == 1
    
    @pytest.mark.parametrize("ppmm", [96.0/25.4, 90.0/25.4])
    def test_cm(self, ppmm):
        assert css_dimension_to_mm("1.2cm", ppmm) == 12.0
    
    @pytest.mark.parametrize("ppmm", [96.0/25.4, 90.0/25.4])
    def test_Q(self, ppmm):
        assert css_dimension_to_mm("1Q", ppmm) == 0.25
        assert css_dimension_to_mm("4Q", ppmm) == 1.0
    
    @pytest.mark.parametrize("ppmm", [96.0/25.4, 90.0/25.4])
    def test_inches(self, ppmm):
        assert css_dimension_to_mm("1in", ppmm) == 25.4
        assert css_dimension_to_mm("2in", ppmm) == 50.8
    
    @pytest.mark.parametrize("ppmm", [96.0/25.4, 90.0/25.4])
    def test_pica(self, ppmm):
        assert css_dimension_to_mm("6pc", ppmm) == css_dimension_to_mm("1in", ppmm)
    
    @pytest.mark.parametrize("ppmm", [96.0/25.4, 90.0/25.4])
    def test_point(self, ppmm):
        assert css_dimension_to_mm("72pt", ppmm) == css_dimension_to_mm("1in", ppmm)
    
    def test_viewport_relative(self):
        assert css_dimension_to_mm("1vw", 90.0/25.4, 200, 400) == 2.0
        assert css_dimension_to_mm("1vh", 90.0/25.4, 200, 400) == 4.0
        assert css_dimension_to_mm("1vmin", 90.0/25.4, 200, 400) == 2.0
        assert css_dimension_to_mm("1vmax", 90.0/25.4, 200, 400) == 4.0
    
    @pytest.mark.parametrize("ppmm", [96.0/25.4, 90.0/25.4])
    def test_pixels(self, ppmm):
        assert css_dimension_to_mm("1px", ppmm) == 1.0 / ppmm
        assert css_dimension_to_mm("1", ppmm) == 1.0 / ppmm
        
        assert css_dimension_to_mm("2px", ppmm) == 2.0 / ppmm
        assert css_dimension_to_mm("2", ppmm) == 2.0 / ppmm
    
    @pytest.mark.parametrize("ppmm", [96.0/25.4, 90.0/25.4])
    def test_unsupported_units(self, ppmm):
        # No font-relative sizes
        with pytest.raises(ValueError):
            css_dimension_to_mm("1em", ppmm)
        
        # No viewport-relative sizes w/out width/height
        with pytest.raises(ValueError):
            css_dimension_to_mm("1vw", ppmm)
        with pytest.raises(ValueError):
            css_dimension_to_mm("1vh", ppmm)
        with pytest.raises(ValueError):
            css_dimension_to_mm("1vmin", ppmm)
        with pytest.raises(ValueError):
            css_dimension_to_mm("1vmin", ppmm)
        
        # No percentages...
        with pytest.raises(ValueError):
            css_dimension_to_mm("1%", ppmm)
    
    @pytest.mark.parametrize("ppmm", [96.0/25.4, 90.0/25.4])
    def test_negative(self, ppmm):
        with pytest.raises(ValueError):
            css_dimension_to_mm("-1mm", ppmm)
    
    @pytest.mark.parametrize("value", [
        # No number
        "",
        "mm",
        # Invalid/malformed number
        "1.2.3",  # >1 decimal
        "1,2mm",  # Comma
        "1 2mm",  # Space
        # Other content in string
        "foo 10 mm",
        "10 bar mm",
        "10 mm baz",
        # Multiple units
        "1 px mm",
        # Wrong case
        "1MM",
    ])
    @pytest.mark.parametrize("ppmm", [96.0/25.4, 90.0/25.4])
    def test_malformed(self, value, ppmm):
        with pytest.raises(ValueError):
            css_dimension_to_mm(value, ppmm)

class TestCssColourToRGBA(object):
    
    @pytest.mark.parametrize("colour_string,rgba", [
        # Three digits
        ("#000", (0/255.0, 0/255.0, 0/255.0, 1)),
        ("#fff", (255/255.0, 255/255.0, 255/255.0, 1)),
        ("#FFF", (255/255.0, 255/255.0, 255/255.0, 1)),
        ("#123", (17/255.0, 34/255.0, 51/255.0, 1)),
        # Four digits
        ("#0000", (0/255.0, 0/255.0, 0/255.0, 0)),
        ("#ffff", (255/255.0, 255/255.0, 255/255.0, 1)),
        ("#FFFF", (255/255.0, 255/255.0, 255/255.0, 1)),
        ("#1234", (17/255.0, 34/255.0, 51/255.0, 68/255.0)),
        # Six digits
        ("#000000", (0/255.0, 0/255.0, 0/255.0, 1)),
        ("#ffffff", (255/255.0, 255/255.0, 255/255.0, 1)),
        ("#FFFFFF", (255/255.0, 255/255.0, 255/255.0, 1)),
        ("#123456", (18/255.0, 52/255.0, 86/255.0, 1)),
        # Eight digits
        ("#00000000", (0/255.0, 0/255.0, 0/255.0, 0)),
        ("#ffffffff", (255/255.0, 255/255.0, 255/255.0, 1)),
        ("#FFFFFFFF", (255/255.0, 255/255.0, 255/255.0, 1)),
        ("#12345678", (18/255.0, 52/255.0, 86/255.0, 120/255.0)),
    ])
    def test_hex_colours(self, colour_string, rgba):
        assert css_colour_to_rgba(colour_string) == rgba
    
    @pytest.mark.parametrize("colour_string,rgba", [
        # Number formatting
        ("rgb(0,0,0)", (0/255.0, 0/255.0, 0/255.0, 1)),
        ("rgb(255,255,255)", (255/255.0, 255/255.0, 255/255.0, 1)),
        ("rgb(12,34,56)", (12/255.0, 34/255.0, 56/255.0, 1)),
        # Number formatting rgba
        ("rgba(0,0,0,0)", (0/255.0, 0/255.0, 0/255.0, 0)),
        ("rgba(0,0,0,0.)", (0/255.0, 0/255.0, 0/255.0, 0)),
        ("rgba(0,0,0,.0)", (0/255.0, 0/255.0, 0/255.0, 0)),
        ("rgba(0,0,0,0.0)", (0/255.0, 0/255.0, 0/255.0, 0)),
        ("rgba(255,255,255,1)", (255/255.0, 255/255.0, 255/255.0, 1)),
        ("rgba(12,34,56,.7)", (12/255.0, 34/255.0, 56/255.0, 0.7)),
        # Percentage formatting
        ("rgb(0%,0%,0%)", (0/100.0, 0/100.0, 0/100.0, 1)),
        ("rgb(100%,100%,100%)", (100/100.0, 100/100.0, 100/100.0, 1)),
        ("rgb(12%,34%,56%)", (12/100.0, 34/100.0, 56/100.0, 1)),
        ("rgb(12.%,34.%,56.%)", (12/100.0, 34/100.0, 56/100.0, 1)),
        ("rgb(12.3%,45.6%,78.9%)", (12.3/100.0, 45.6/100.0, 78.9/100.0, 1)),
        # Percentage formatting rgba
        ("rgba(0%,0%,0%,0)", (0/100.0, 0/100.0, 0/100.0, 0)),
        ("rgba(0%,0%,0%,0.)", (0/100.0, 0/100.0, 0/100.0, 0)),
        ("rgba(0%,0%,0%,.0)", (0/100.0, 0/100.0, 0/100.0, 0)),
        ("rgba(0%,0%,0%,0.0)", (0/100.0, 0/100.0, 0/100.0, 0)),
        ("rgba(100%,100%,100%,1)", (100/100.0, 100/100.0, 100/100.0, 1)),
        ("rgba(12%,34%,56%,.7)", (12/100.0, 34/100.0, 56/100.0, 0.7)),
        # Case/space flexibility
        (" RGB ( 12 , 34 , 56 ) ", (12/255.0, 34/255.0, 56/255.0, 1)),
        (" RGB ( 12. % , 34. % , 56. % ) ", (12/100.0, 34/100.0, 56/100.0, 1)),
        (" RGBA ( 12 , 34 , 56 , 0.7 ) ", (12/255.0, 34/255.0, 56/255.0, 0.7)),
        (" RGBA ( 12. % , 34. % , 56. % , 0.7 ) ", (12/100.0, 34/100.0, 56/100.0, 0.7)),
    ])
    def test_rgb_colours(self, colour_string, rgba):
        assert css_colour_to_rgba(colour_string) == rgba
    
    @pytest.mark.parametrize("colour_string,rgba", [
        # Primary colours
        ("hsl(0,100%,50%)", (1, 0, 0, 1)),
        ("hsl(120,100%,50%)", (0, 1, 0, 1)),
        ("hsl(240,100%,50%)", (0, 0, 1, 1)),
        # White
        ("hsl(0,100%,100%)", (1, 1, 1, 1)),
        ("hsl(120,100%,100%)", (1, 1, 1, 1)),
        ("hsl(120,0%,100%)", (1, 1, 1, 1)),
        # Black
        ("hsl(0,100%,0%)", (0, 0, 0, 1)),
        ("hsl(120,100%,0%)", (0, 0, 0, 1)),
        ("hsl(120,0%,0%)", (0, 0, 0, 1)),
        # Gray
        ("hsl(0,0%,25%)", (0.25, 0.25, 0.25, 1)),
        ("hsl(0,0%,50%)", (0.5, 0.5, 0.5, 1)),
        ("hsl(0,0%,75%)", (0.75, 0.75, 0.75, 1)),
        # HSLA
        ("hsla(0,100%,50%,0)", (1, 0, 0, 0)),
        ("hsla(0,100%,50%,0.)", (1, 0, 0, 0)),
        ("hsla(0,100%,50%,.0)", (1, 0, 0, 0)),
        ("hsla(0,100%,50%,0.0)", (1, 0, 0, 0)),
        ("hsla(120,100%,50%,.5)", (0, 1, 0, 0.5)),
        ("hsla(240,100%,50%,1)", (0, 0, 1, 1)),
        # Spacing
        (" HSL ( 0 , 0 % , 25 % ) ", (0.25, 0.25, 0.25, 1)),
        (" HSLA ( 0, 100 % , 50 % , 0 ) ", (1, 0, 0, 0)),
    ])
    def test_hsl_colours(self, colour_string, rgba):
        assert css_colour_to_rgba(colour_string) == rgba
    
    @pytest.mark.parametrize("colour_string,rgba", [
        # Varying case and spacing
        ("transparent", (0, 0, 0, 0)),
        (" white ", (1, 1, 1, 1)),
        ("BLACK", (0, 0, 0, 1)),
        (" rEd", (1, 0, 0, 1)),
        ("BlUe ", (0, 0, 1, 1)),
    ])
    def test_named_colours(self, colour_string, rgba):
        assert css_colour_to_rgba(colour_string) == rgba
    
    @pytest.mark.parametrize("colour_string", [
        # Empty
        "",
        " ",
        # Unknown colour name
        "foobar",
        # Wrong number of hex digits
        "#a",
        "#aa",
        "#aaaaa",
        "#aaaaaaa",
        "#aaaaaaaaa",
        # Non-hex digits
        "#ggg",
        "#gggg",
        "#gggggg",
        "#gggggggg",
        # Mixed/incorrect percentage/not
        "rgb(1,2%,3)",
        "rgba(1,2%,3,0)",
        "rgba(1,2,3,0%)",
        "hsl(1,2%,3)",
        "hsla(1,2%,3,0)",
        "hsla(1,2%,3%,0%)",
        # Non-numbers in rgb etc
        "rgb(a,b,c)",
        "rgb(a%,b%,c%)",
        "rgba(a%,b%,c%,d)",
        "hsl(a,b%,c%)",
        "hsla(a,b%,c%,d)",
        # Out of range values
        "rgb(256,0,0)",
        "rgb(0,256,0)",
        "rgb(0,0,256)",
        "rgb(101%,0%,0%)",
        "rgb(0%,101%,0%)",
        "rgb(0%,0%,101%)",
        "rgba(256,0,0,0)",
        "rgba(0,256,0,0)",
        "rgba(0,0,256,0)",
        "rgba(0,0,0,1.1)",
        "rgba(101%,0%,0%,0)",
        "rgba(0%,101%,0%,0)",
        "rgba(0%,0%,101%,0)",
        "rgba(0%,0%,0%,1.1)",
        "hsl(360,0%,0%)",
        "hsl(0,101%,0%)",
        "hsl(0,0%,101%)",
        "hsla(360,0%,0%,0)",
        "hsla(0,101%,0%,0)",
        "hsla(0,0%,101%,0)",
        "hsla(0,0%,0%,1.1)",
        # Malformed prefixes
        "foo(0,0,0)",
        "r gb(0,0,0)",
        "rbg(0,0,0)",
        "rgb a(0,0,0,0)",
        "rgab(0,0,0,0)",
        "hs l(0,0%,0%)",
        "hls(0,0%,0%)",
        "hsl a(0,0%,0%,0)",
        "hsal(0,0%,0%,0)",
        # Wrong number of args
        "rgb(0,0)",
        "rgb(0%,0%)",
        "rgb(0%,0%,0%,0)",
        "rgb(0%,0%,0%,0%)",
        "hsl(0,0%)",
        "hsl(0,0%,0%,0)",
        "hsl(0,0%,0%,0%)",
        "rgba(0,0,0)",
        "rgba(0%,0%,0%)",
        "rgba(0%,0%,0%,0,0)",
        "rgba(0%,0%,0%,0%,0)",
        "hsla(0,0%,0%)",
        "hsla(0,0%,0%,0,0)",
        "hsla(0,0%,0%,0,0%)",
        # Missing brackets
        "rgb(0,0,0",
        "rgb 0,0,0)",
        "rgb0,0,0",
        "rgb(0%,0%,0%",
        "rgb 0%,0%,0%)",
        "rgb0%,0%,0%",
        "rgba(0,0,0,0",
        "rgba 0,0,0,0)",
        "rgba0,0,0,0",
        "rgba(0%,0%,0%,0",
        "rgba 0%,0%,0%,0)",
        "rgba0%,0%,0%,0",
        "hsl(0,0%,0%",
        "hsl 0,0%,0%)",
        "hsl0,0%,0%",
        "hsla(0,0%,0%,0",
        "hsla 0,0%,0%,0)",
        "hsla0,0%,0%,0",
        # Missing commas
        "rgb(0 0,0)",
        "rgb(0,0 0)",
        "rgb(0 0 0)",
        "rgb(0% 0%,0%)",
        "rgb(0%,0% 0%)",
        "rgb(0% 0% 0%)",
        "rgba(0 0,0,0)",
        "rgba(0,0 0,0)",
        "rgba(0 0 0,0)",
        "rgba(0 0 0 0)",
        "rgba(0% 0%,0%,0)",
        "rgba(0%,0% 0%,0)",
        "rgba(0% 0% 0%,0)",
        "rgba(0% 0% 0% 0)",
        "hsl(0 0%,0%)",
        "hsl(0,0% 0%)",
        "hsl(0 0% 0%)",
        "hsla(0 0%,0%,0)",
        "hsla(0,0% 0%,0)",
        "hsla(0 0% 0%,0)",
        "hsla(0 0% 0% 0)",
    ])
    def test_malformed(self, colour_string):
        with pytest.raises(ValueError):
            css_colour_to_rgba(colour_string)

def test_is_inkscape_layer():
    svg = ElementTree.fromstring("""<?xml version="1.0" encoding="UTF-8" standalone="no"?>
        <svg
           xmlns="http://www.w3.org/2000/svg"
           xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape">
          <g
             inkscape:groupmode="layer"
             id="layer2"
             inkscape:label="Layer Name Here">
          </g>
          <g />
        </svg>
    """)
    
    assert is_inkscape_layer(svg) is False
    assert is_inkscape_layer(svg[0]) is True
    assert is_inkscape_layer(svg[1]) is False


def test_get_inkscape_layer_label():
    svg = ElementTree.fromstring("""<?xml version="1.0" encoding="UTF-8" standalone="no"?>
        <svg
           xmlns="http://www.w3.org/2000/svg"
           xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape">
          <g
             inkscape:groupmode="layer"
             id="layer2"
             inkscape:label="Layer Name Here">
          </g>
        </svg>
    """)
    
    assert get_inkscape_layer_label(svg) is None
    assert get_inkscape_layer_label(svg[0]) == "Layer Name Here"


@pytest.mark.parametrize("xmlns_line", ["", 'xmlns="http://www.w3.org/2000/svg"'])
def test_is_visible(xmlns_line):
    svg = ElementTree.fromstring("""<?xml version="1.0" encoding="UTF-8" standalone="no"?>
        <svg
           {}
           xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape">
          <g
             inkscape:groupmode="layer"
             id="layer2"
             inkscape:label="Layer 1">
          </g>
          <g
             inkscape:groupmode="layer"
             id="layer2"
             style="display:none"
             inkscape:label="Layer 2">
          </g>
          <g
             inkscape:groupmode="layer"
             id="layer2"
             style="foo : bar; display : none; baz: qux"
             inkscape:label="Layer 3">
          </g>
          <g
             inkscape:groupmode="layer"
             id="layer2"
             style="display:visible"
             inkscape:label="Layer 4">
          </g>
          <g
             inkscape:groupmode="layer"
             id="layer2"
             style="foo : bar; display : visible; baz: qux"
             inkscape:label="Layer 5">
          </g>
        </svg>
    """.format(xmlns_line))
    
    assert is_visible(svg[0]) is True
    assert is_visible(svg[1]) is False
    assert is_visible(svg[2]) is False
    assert is_visible(svg[3]) is True
    assert is_visible(svg[4]) is True


class TestSetSvgVisibility(object):
    
    @pytest.fixture
    def svg(self):
        return ElementTree.fromstring("""<?xml version="1.0" encoding="UTF-8" standalone="no"?>
            <svg
               xmlns="http://www.w3.org/2000/svg"
               xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape">
              <g
                 inkscape:groupmode="layer"
                 id="visible, no style"
                 inkscape:label="Layer 1">
              </g>
              <g
                 inkscape:groupmode="layer"
                 id="hidden, no style"
                 style="display:none"
                 inkscape:label="Layer 2">
              </g>
              <g
                 inkscape:groupmode="layer"
                 id="hidden, with style"
                 style="foo : bar; display : none; baz : qux"
                 inkscape:label="Layer 3">
              </g>
              <g
                 inkscape:groupmode="layer"
                 id="hidden, no style, collapsed whitespace"
                 style="display:visible"
                 inkscape:label="Layer 4">
              </g>
              <g
                 inkscape:groupmode="layer"
                 id="hidden, with style, collapsed whitespace"
                 style="foo:bar;display:visible;baz:qux"
                 inkscape:label="Layer 5">
              </g>
            </svg>
        """)
    
    def test_show(self, svg):
        set_visibility(svg[0], True)
        assert "style" not in svg[0].attrib
        
        set_visibility(svg[1], True)
        assert "style" not in svg[1].attrib
        
        set_visibility(svg[2], True)
        assert sorted(map(str.strip, svg[2].attrib["style"].split(";"))) == [
            "baz : qux",
            "foo : bar",
        ]
        
        set_visibility(svg[3], True)
        assert "style" not in svg[3].attrib
        
        set_visibility(svg[4], True)
        assert sorted(map(str.strip, svg[4].attrib["style"].split(";"))) == [
            "baz:qux",
            "foo:bar",
        ]
    
    def test_hide(self, svg):
        set_visibility(svg[0], False)
        assert svg[0].attrib["style"] == "display:none"
        
        set_visibility(svg[1], False)
        assert svg[1].attrib["style"] == "display:none"
        
        set_visibility(svg[2], False)
        assert sorted(map(str.strip, svg[2].attrib["style"].split(";"))) == [
            "baz : qux",
            "display:none",
            "foo : bar",
        ]
        
        set_visibility(svg[3], False)
        assert svg[3].attrib["style"] == "display:none"
        
        set_visibility(svg[4], False)
        assert sorted(map(str.strip, svg[4].attrib["style"].split(";"))) == [
            "baz:qux",
            "display:none",
            "foo:bar",
        ]


class TestMakeNodesVisible(object):
    
    def test_all_at_same_level(self):
        svg = ElementTree.fromstring(
            """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
                <svg xmlns="http://www.w3.org/2000/svg" >
                  <g class=""></g>
                  <g class="target"></g>
                  <g class="" style="display:none"></g>
                  <g class="target" style="display:none"></g>
                </svg>
            """
        )
        
        make_nodes_visible(svg, lambda n: n.attrib.get("class") == "target")
        
        assert is_visible(svg[0]) is False
        assert is_visible(svg[1]) is True
        assert is_visible(svg[2]) is False
        assert is_visible(svg[3]) is True
    
    def test_nested_not_changed(self):
        svg = ElementTree.fromstring(
            """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
                <svg xmlns="http://www.w3.org/2000/svg" >
                  <g class="target" style="display:none">
                    <g></g>
                    <g style="display:none"></g>
                  </g>
                  <g></g>
                  <g style="display:none"></g>
                </svg>
            """
        )
        
        make_nodes_visible(svg, lambda n: n.attrib.get("class") == "target")
        
        assert is_visible(svg[0]) is True
        assert is_visible(svg[0][0]) is True
        assert is_visible(svg[0][1]) is False  # Not changed
        assert is_visible(svg[1]) is False
        assert is_visible(svg[2]) is False
