from py_silhouette import SUPPORTED_DEVICE_PARAMETERS, DeviceState

class DummyDevice(object):
    """
    A dummy :py:class:`py_silhouette.Device` which, rather than driving an
    actual device, generates an SVG showing the cuts/lines plotted.
    """
    
    def __init__(self, filename=None, params=SUPPORTED_DEVICE_PARAMETERS[0]):
        """
        Parameters
        ----------
        filename : str or None
            If not None, the file to write an SVG to when :py:meth:`flush` is
            called.
        device_params : :py:class:`DeviceParameters`
            Definition of the device's key parameters.
        """
        
        self.filename = filename
        self.params = params
        
        self.width = params.area_width_max
        self.height = params.area_height_max
        
        self.regmarks_used = False
        self.speed = None
        self.force = None
        self.tool_diameter = None
        self.paths = [[(0, 0)]]  # [[(x, y), ...], ...]
    
    def zero_on_registration_mark(self, width, height, *args, **kwargs):
        self.width = width
        self.height = height
        
        self.regmarks_used = True
    
    def move_to(self, x, y, use_tool=False):
        if use_tool:
            self.paths[-1].append((x, y))
        else:
            self.paths.append([(x, y)])
    
    def move_home(self):
        self.move_to(0, 0, False)
    
    def set_speed(self, speed):
        self.speed = speed
    
    def set_force(self, force):
        self.force = force
    
    def set_tool_diameter(self, tool_diameter):
        self.tool_diameter = tool_diameter
    
    def get_state(self):
        return DeviceState.ready
    
    def flush(self):
        if self.filename is not None:
            with open(self.filename, "w") as f:
                f.write('<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n')
                f.write('<svg\n')
                f.write('  xmlns="http://www.w3.org/2000/svg"\n')
                f.write('  xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"\n')
                f.write('  width="{}mm"\n'.format(self.width))
                f.write('  height="{}mm"\n'.format(self.height))
                f.write('  viewBox="0 0 {} {}"\n'.format(self.width, self.height))
                f.write('>\n')
                
                f.write('  <!-- tool_diameter = {} mm -->\n'.format(
                    self.tool_diameter,
                ))
                f.write('  <!-- speed = {} mm/s -->\n'.format(
                    self.speed,
                ))
                f.write('  <!-- force = {} g -->\n'.format(
                    self.force,
                ))
                f.write('  <!-- regmarks_used = {} -->\n'.format(
                    self.regmarks_used,
                ))
                
                # Filter out non-drawn parts of the path
                paths = [path for path in self.paths if len(path) > 1]
                
                num_points = sum(len(p) - 1 for p in paths)
                i = 0
                for path in paths:
                    for (x1, y1), (x2, y2) in zip(path, path[1:]):
                        f.write('  <path\n')
                        f.write('    d="M{},{}L{},{}"\n'.format(
                            x1, y1,
                            x2, y2,
                        ))
                        f.write('    stroke="hsl({}, 100%, 50%)"\n'.format(
                            (360*i) // num_points
                        ))
                        f.write('    stroke-width="0.2"\n')
                        f.write('  />\n')
                        i += 1
                
                f.write('</svg>\n')
