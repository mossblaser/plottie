from plottie.dummy_device import DummyDevice


def test_crude(tmpdir):
    filename = str(tmpdir.join("test.svg"))
    
    d = DummyDevice(filename)
    d.set_speed(123)
    d.set_force(321)
    d.set_tool_diameter(10)
    
    d.zero_on_registration_mark(100, 200)
    
    d.move_to(10, 20, False)
    d.move_to(30, 40, True)
    d.move_to(50, 60, True)
    
    d.move_to(20, 30, False)
    d.move_to(40, 50, True)
    
    d.move_home()
    
    d.flush()
    
    assert open(filename).read() == (
        '<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n'
        '<svg\n'
        '  xmlns="http://www.w3.org/2000/svg"\n'
        '  xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"\n'
        '  width="100mm"\n'
        '  height="200mm"\n'
        '  viewBox="0 0 100 200"\n'
        '>\n'
        '  <!-- tool_diameter = 10 mm -->\n'
        '  <!-- speed = 123 mm/s -->\n'
        '  <!-- force = 321 g -->\n'
        '  <!-- regmarks_used = True -->\n'
        '  <path\n'
        '    d="M10,20L30,40"\n'
        '    stroke="hsl(0, 100%, 50%)"\n'
        '    stroke-width="0.2"\n'
        '  />\n'
        '  <path\n'
        '    d="M30,40L50,60"\n'
        '    stroke="hsl(120, 100%, 50%)"\n'
        '    stroke-width="0.2"\n'
        '  />\n'
        '  <path\n'
        '    d="M20,30L40,50"\n'
        '    stroke="hsl(240, 100%, 50%)"\n'
        '    stroke-width="0.2"\n'
        '  />\n'
        '</svg>\n'
    )
