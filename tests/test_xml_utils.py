import pytest

from xml.etree import ElementTree

from plottie.xml_utils import (
    read_xml_file,
    xml_deep_child_index,
    xml_get_at_index,
)


class TestReadXmlFile(object):
    
    @pytest.fixture()
    def sample_svg(self, tmpdir):
        f = tmpdir.join("test.svg")
        # An extract from a modern Inkscape SVG file
        f.write("""<?xml version="1.0" encoding="UTF-8" standalone="no"?>
            <!-- Created with Inkscape (http://www.inkscape.org/) -->
            <svg
               xmlns="http://www.w3.org/2000/svg"
               xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
               xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
               width="210mm"
               height="297mm"
               viewBox="0 0 210 297"
               version="1.1"
               id="svg8"
               inkscape:version="0.92.2 2405546, 2018-03-11"
               sodipodi:docname="foo.svg">
            </svg>
        """)
        return str(f)
    
    def test_basic_read(self, sample_svg):
        root = read_xml_file(sample_svg)
        assert root.tag == "{http://www.w3.org/2000/svg}svg"
        print(root.attrib)
        assert root.attrib["width"] == "210mm"
        assert root.attrib["{http://www.inkscape.org/namespaces/inkscape}version"] == "0.92.2 2405546, 2018-03-11"
    
    def test_strip_namespaces(self, sample_svg):
        root = read_xml_file(sample_svg, ["http://www.w3.org/2000/svg"])
        assert root.tag == "svg"
        print(root.attrib)
        assert root.attrib["width"] == "210mm"
        assert root.attrib["{http://www.inkscape.org/namespaces/inkscape}version"] == "0.92.2 2405546, 2018-03-11"


class TestXmlDeepChildIndex(object):
    
    @pytest.fixture
    def root(self):
        return ElementTree.fromstring("""
            <a>
                <b />
                <b />
                <b>
                    <c />
                </b>
            </a>
        """)
    
    def test_find_root(self, root):
        assert xml_deep_child_index(root, root) == []
    
    def test_find_immediate_child(self, root):
        for index, child in enumerate(root):
            assert xml_deep_child_index(root, child) == [index]
    
    def test_find_nested_child(self, root):
        assert xml_deep_child_index(root, root[2][0]) == [2, 0]
    
    def test_doesnt_find_other_things(self, root):
        target = ElementTree.fromstring("<b/>")
        with pytest.raises(KeyError):
            xml_deep_child_index(root, target)


class TestXmlGetChildAtIndex(object):
    
    @pytest.fixture
    def root(self):
        return ElementTree.fromstring("""
            <a>
                <b />
                <b />
                <b>
                    <c />
                </b>
            </a>
        """)
    
    def test_get_root(self, root):
        assert xml_get_at_index(root, []) == root
    
    def test_get_child(self, root):
        assert xml_get_at_index(root, [0]) == root[0]
        assert xml_get_at_index(root, [1]) == root[1]
        assert xml_get_at_index(root, [2]) == root[2]
    
    def test_get_sub_child(self, root):
        assert xml_get_at_index(root, [2, 0]) == root[2][0]
