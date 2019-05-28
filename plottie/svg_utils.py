"""
Utilities for manipulating/querying aspects of SVGs relevant to this
application (not a generic SVG library). All methods expect SVGs parsed as XML
using Python's ElementTree library.
"""

import re

from xml.etree import ElementTree

from collections import OrderedDict

from colorsys import hls_to_rgb

from plottie.xml_utils import xml_deep_child_index, xml_get_at_index
from plottie.css_colour_names import CSS_COLOUR_NAMES


# Relevant XML namespace URIs used by SVGs
SVG_NAMESPACE = "http://www.w3.org/2000/svg"
INKSCAPE_NAMESPACE = "http://www.inkscape.org/namespaces/inkscape"
XLINK_NAMESPACE = "http://www.w3.org/1999/xlink"

namespaces = {
    "svg": SVG_NAMESPACE,
    "inkscape": INKSCAPE_NAMESPACE,
    "xlink": XLINK_NAMESPACE,
}

# Unit conversion ratios
MM_PER_CM = 10.0
MM_PER_QUARTER_MM = 0.25
MM_PER_INCH = 25.4
MM_PER_PICA = MM_PER_INCH / 6.0
MM_PER_POINT = MM_PER_INCH / 72.0

CSS_COLOUR_HEX3 = re.compile(r"^#"
                             r"([0-9a-f])"
                             r"([0-9a-f])"
                             r"([0-9a-f])"
                             r"$", re.I)
CSS_COLOUR_HEX4 = re.compile(r"^#"
                             r"([0-9a-f])"
                             r"([0-9a-f])"
                             r"([0-9a-f])"
                             r"([0-9a-f])"
                             r"$", re.I)
CSS_COLOUR_HEX6 = re.compile(r"^#"
                             r"([0-9a-f]{2})"
                             r"([0-9a-f]{2})"
                             r"([0-9a-f]{2})"
                             r"$", re.I)
CSS_COLOUR_HEX8 = re.compile(r"^#"
                             r"([0-9a-f]{2})"
                             r"([0-9a-f]{2})"
                             r"([0-9a-f]{2})"
                             r"([0-9a-f]{2})"
                             r"$", re.I)
CSS_COLOUR_RGB = re.compile(r"^rgb\s*[(]\s*"
                            r"([0-9]{1,3})\s*,\s*"
                            r"([0-9]{1,3})\s*,\s*"
                            r"([0-9]{1,3})\s*"
                            r"[)]$", re.I)
CSS_COLOUR_RGB_PERC = re.compile(r"^rgb\s*[(]\s*"
                                 r"([0-9]{1,3}(?:[.][0-9]*)?)\s*%\s*,\s*"
                                 r"([0-9]{1,3}(?:[.][0-9]*)?)\s*%\s*,\s*"
                                 r"([0-9]{1,3}(?:[.][0-9]*)?)\s*%\s*"
                                 r"[)]$", re.I)
CSS_COLOUR_RGBA = re.compile(r"^rgba\s*[(]\s*"
                             r"([0-9]{1,3})\s*,\s*"
                             r"([0-9]{1,3})\s*,\s*"
                             r"([0-9]{1,3})\s*,\s*"
                             r"([0-9]+|[0-9]+[.][0-9]*|[.][0-9]+)\s*"
                             r"[)]$", re.I)
CSS_COLOUR_RGBA_PERC = re.compile(r"^rgba\s*[(]\s*"
                                  r"([0-9]{1,3}(?:[.][0-9]*)?)\s*%\s*,\s*"
                                  r"([0-9]{1,3}(?:[.][0-9]*)?)\s*%\s*,\s*"
                                  r"([0-9]{1,3}(?:[.][0-9]*)?)\s*%\s*,\s*"
                                  r"([0-9]+|[0-9]+[.][0-9]*|[.][0-9]+)\s*"
                                  r"[)]$", re.I)
CSS_COLOUR_HSL_PERC = re.compile(r"^hsl\s*[(]\s*"
                                 r"([0-9]{1,3})\s*,\s*"
                                 r"([0-9]{1,3}(?:[.][0-9]*)?)\s*%\s*,\s*"
                                 r"([0-9]{1,3}(?:[.][0-9]*)?)\s*%\s*"
                                 r"[)]$", re.I)
CSS_COLOUR_HSLA_PERC = re.compile(r"^hsla\s*[(]\s*"
                                  r"([0-9]{1,3})\s*,\s*"
                                  r"([0-9]{1,3}(?:[.][0-9]*)?)\s*%\s*,\s*"
                                  r"([0-9]{1,3}(?:[.][0-9]*)?)\s*%\s*,\s*"
                                  r"([0-9]+|[0-9]+[.][0-9]*|[.][0-9]+)\s*"
                                  r"[)]$", re.I)


def css_dimension_to_mm(dimension, pixels_per_mm=96.0/MM_PER_INCH,
                        width_mm=None, height_mm=None):
    """
    Convert a CSS dimension string (e.g. '3cm') into a number of mm. Fails for
    viewport-precentage length units of size if 'width_mm' and 'height_mm' are
    None.
    """
    match = re.match(r"^\s*[+]?\s*([0-9.]+)\s*(vw|vh|vmin|vmax|cm|mm|Q|in|pc|pt|px|)\s*$", dimension)
    if not match:
        raise ValueError("{} is not a positive, absolute unit of size".format(
            repr(dimension)))
    
    number, unit = match.groups()
    number = float(number)
    
    if unit == "mm":
        pass
    elif unit == "cm":
        number *= MM_PER_CM
    elif unit == "Q":
        number *= MM_PER_QUARTER_MM
    elif unit == "in":
        number *= MM_PER_INCH
    elif unit == "pc":
        number *= MM_PER_PICA
    elif unit == "pt":
        number *= MM_PER_POINT
    elif unit == "px" or unit == "":
        number /= pixels_per_mm
    elif unit == "vw":
        if width_mm is None:
            raise ValueError("Relative dimensions not allowed.")
        number = (number / 100.0) * width_mm
    elif unit == "vh":
        if height_mm is None:
            raise ValueError("Relative dimensions not allowed.")
        number = (number / 100.0) * height_mm
    elif unit == "vmin":
        if width_mm is None or height_mm is None:
            raise ValueError("Relative dimensions not allowed.")
        number = (number / 100.0) * min(width_mm, height_mm)
    elif unit == "vmax":
        if width_mm is None or height_mm is None:
            raise ValueError("Relative dimensions not allowed.")
        number = (number / 100.0) * max(width_mm, height_mm)
    else:
        assert False, "Supposedly-supported unit not implemented!"
    
    return number


def css_colour_to_rgba(colour_string):
    """
    Parses colours according to the SVG/CSS specification (see
    https://www.w3.org/TR/css-color-3/#svg-color) into (r, g, b, a) tuples with
    all values being in the range 0.0 to 1.0. Also parses non-standard 4 and 8
    didgit hex colour codes with alpha information in the final nyble/byte (as
    used in Inkscape).
    """
    colour_string = colour_string.strip().lower()
    
    # If we've got a named colour, swap it for a concrete colour string
    colour_string = CSS_COLOUR_NAMES.get(colour_string, colour_string)
    
    # Normalise hex representations into 8-digit hex (with alpha)
    match = CSS_COLOUR_HEX3.match(colour_string)
    if match:
        r, g, b = match.groups()
        colour_string = "#{}{}{}ff".format(r*2, g*2, b*2)
    match = CSS_COLOUR_HEX4.match(colour_string)
    if match:
        r, g, b, a = match.groups()
        colour_string = "#{}{}{}{}".format(r*2, g*2, b*2, a*2)
    if CSS_COLOUR_HEX6.match(colour_string):
        colour_string = "{}ff".format(colour_string)
    
    # Parse hex colour codes
    match = CSS_COLOUR_HEX8.match(colour_string)
    if match:
        return tuple(int(x, 16)/255.0 for x in match.groups())
    
    # Normalise RGB into RGBA
    match = CSS_COLOUR_RGB.match(colour_string)
    if match:
        r, g, b = match.groups()
        colour_string = "rgba({},{},{},1)".format(r, g, b)
    match = CSS_COLOUR_RGB_PERC.match(colour_string)
    if match:
        r, g, b = match.groups()
        colour_string = "rgba({}%,{}%,{}%,1)".format(r, g, b)
    
    # Parse RGBA colour codes
    match = CSS_COLOUR_RGBA.match(colour_string)
    if match:
        r, g, b, a = match.groups()
        rgba = (int(r)/255.0, int(g)/255.0, int(b)/255.0, float(a))
        if max(rgba) > 1.0:
            raise ValueError("Colour value out of range.")
        return rgba
    match = CSS_COLOUR_RGBA_PERC.match(colour_string)
    if match:
        r, g, b, a = match.groups()
        rgba = (float(r)/100.0, float(g)/100.0, float(b)/100.0, float(a))
        if max(rgba) > 1.0:
            raise ValueError("Colour value out of range.")
        return rgba
    
    # Normalise HSL into HSLA
    match = CSS_COLOUR_HSL_PERC.match(colour_string)
    if match:
        h, s, l = match.groups()
        colour_string = "hsla({},{}%,{}%,1)".format(h, s, l)
    
    # Parse HSLA colour codes
    match = CSS_COLOUR_HSLA_PERC.match(colour_string)
    if match:
        h, s, l, a = map(float, match.groups())
        h /= 360.0
        s /= 100.0
        l /= 100.0
        if h >= 1.0 or max(s, l, a) > 1.0:
            raise ValueError("Colour value out of range.")
        r, g, b = hls_to_rgb(h, l, s)
        return (r, g, b, a)
    
    raise ValueError("Unrecognised colour format or name.")


def is_inkscape_layer(tag):
    """
    Is a given XML tag an Inkscape layer?
    """
    return (tag.tag in ("g", "{{{}}}g".format(SVG_NAMESPACE)) and
            tag.attrib.get("{{{}}}groupmode".format(INKSCAPE_NAMESPACE)) == "layer")


def get_inkscape_layer_label(tag):
    """
    Given an inkscape layer 'g' tag, return the label assigned to that layer.
    """
    return tag.attrib.get("{{{}}}label".format(INKSCAPE_NAMESPACE))


def is_visible(tag):
    """
    Given an svg tag, return True if it is visible and False if hidden.
    """
    style = tag.attrib.get("style")
    if style is None:
        return True
    else:
        match = re.match(r"(^|.*;)\s*display\s*:\s*none\s*($|;.*)", style)
        return match is None


def set_visibility(tag, visibility):
    """
    Given an SVG tag, mutate it to add or remove 'display:none' to the style
    attribute.
    """
    style = tag.attrib.get("style", "")
    
    # Remove visibility specifier
    style = re.sub(r"(^|;+)\s*display\s*:\s*[^\s;]+\s*($|;)", ";", style)
    style = style.strip("; \t\n")
    
    # Change/remove the style attribute
    if not visibility:
        style += ";display:none"
        style = style.strip(";")
    
    if style:
        tag.attrib["style"] = style
    else:
        tag.attrib.pop("style", None)


def make_nodes_visible(root, predicate):
    """
    Given an SVG document root and a predicate function, make all elements
    which the predicate returns True for visible and all others hidden.
    """
    if predicate(root):
        set_visibility(root, True)
        return True
    else:
        child_is_visible = False
        for child in root:
            child_is_visible |= make_nodes_visible(child, predicate)
        set_visibility(root, child_is_visible)
        return child_is_visible
