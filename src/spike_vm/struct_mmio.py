import ctypes
from src.structure_utils import MakeByteAlignedStructure, structures_to_header

EightByteAlignedStructure = MakeByteAlignedStructure(8)

class microarena_io_rw_t(EightByteAlignedStructure):
    _fields_ = [
        ('a',ctypes.c_int32),
        ("stdout_buffer",ctypes.c_int8 * 100),
        ("stdout_go", ctypes.c_int8)
    ]
  
class microarena_io_r_t(EightByteAlignedStructure):
    _fields_ = [
        ('b',ctypes.c_int8),
        ('d', ctypes.c_int32)
    ]

if __name__ == "__main__":
    print(structures_to_header([microarena_io_r_t, microarena_io_rw_t], 8))