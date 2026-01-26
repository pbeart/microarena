import ctypes

class SelfExpositingStructure(ctypes.Structure):
    def __repr__(self):
        indent = " "
        
        s = f"<{type(self).__name__}\n"

        for f in self._fields_:
            name = f[0]
            value = repr(getattr(self, name))
            value_lines = value.splitlines()
            if len(value_lines) == 1: # print on one line
                s += f"{indent}{name}={value}\n"
            else:
                s += f"{indent}{name}=\n"
                for line in value_lines:
                    s += f"{indent*2}{line}\n"

        
        s += ">"

        return s

class microarena_io_rw_t(SelfExpositingStructure):
    _fields_ = [
        ('a',ctypes.c_int32)
    ]
  
class microarena_io_r_t(SelfExpositingStructure):
    _fields_ = [
        ('b',ctypes.c_int32)
    ]
  
class microarena_io_t(SelfExpositingStructure):
    _fields_ = [
        ('in_',microarena_io_r_t),
        ('out',microarena_io_rw_t)
    ]