from py_silhouette import SUPPORTED_DEVICE_PARAMETERS

class DummyDevice(object):
    """
    A dummy :py:class:`py_silhouette.Device` which, rather than driving an
    actual device, just ignores commands sent to it.
    """
    
    def __init__(self, params=SUPPORTED_DEVICE_PARAMETERS[0]):
        self.params = params
        
        self.width = params.area_width_max
        self.height = params.area_height_max
    
    def zero_on_registration_mark(self, width, height, *args, **kwargs):
        self.width = width
        self.height = height
    
    def move_to(self, x, y, use_tool=False):
        pass
    
    def move_home(self):
        pass
    
    def flush(self):
        pass
    
    def set_speed(self, speed):
        pass
    
    def set_force(self, force):
        pass
    
    def set_tool_diameter(self, tool_diameters):
        pass
