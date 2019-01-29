"""
Fairly generic XML utility functions.
"""

from xml.etree import ElementTree


def read_xml_file(filename, ignored_namespaces=[]):
    """
    Parse the provided XML file and return a
    :py:class:`xml.etree.ElementTree.Element`.
    
    For convenience, strips namespace prefixes from tag names  listed in the
    ``ignored_namespaces`` argument.
    """
    bracketed_namespaces = ["{{{}}}".format(ns) for ns in ignored_namespaces]
    
    with open(filename) as f:
        parser = ElementTree.iterparse(f)
        for _, element in parser:
            for namespace in bracketed_namespaces:
                if element.tag.startswith(namespace):
                    element.tag = element.tag[len(namespace):]
    
    return parser.root


def xml_deep_child_index(root, target):
    """
    Given an XML ElementTree and a child within that tree, return an 'index'
    into the tree.
    
    Indices are of the form [] indicates the root, [1] indicates the second
    child of the root and [1,2] indicates the third child of the second child
    of the root.
    
    Raises a KeyError if the target is not in the tree.
    """
    # Is root?
    if target is root:
        return []
    
    # Is direct child?
    for index, child in enumerate(root):
        if target is child:
            return [index]
    
    # Is descendent?
    for index, child in enumerate(root):
        try:
            return [index] + xml_deep_child_index(child, target)
        except KeyError:
            pass
    
    # Not found
    raise KeyError("{} not in {}".format(target, root))


def xml_get_at_index(root, index):
    """
    Given an index as produced by xml_deep_child_index, return the element at
    that index.
    """
    target = root
    for i in index:
        target = target[i]
    return target
