import ctypes
from ..structure_utils import MakeByteAlignedStructure, ConstantDefinition

EightByteAlignedStructure = MakeByteAlignedStructure(8)

TURN_LEFT = ConstantDefinition("TURN_LEFT", ctypes.c_int8, 0)
TURN_RIGHT = ConstantDefinition("TURN_RIGHT", ctypes.c_int8, 1)
TURN_NO = ConstantDefinition("TURN_NO", ctypes.c_int8, 2)

RADAR_FREQ_NONE = ConstantDefinition("RADAR_FREQ_NONE", ctypes.c_int8, 0)
RADAR_FREQ_WALL = ConstantDefinition("RADAR_FREQ_WALL", ctypes.c_int8, 1)
RADAR_FREQ_SHIP = ConstantDefinition("RADAR_FREQ_SHIP", ctypes.c_int8, 2)
RADAR_FREQ_PROJECTILE = ConstantDefinition("RADAR_FREQ_PROJECTILE", ctypes.c_int8, 3)

class microarena_io_rw_t(EightByteAlignedStructure):
    _fields_ = [
        ('shoot',ctypes.c_bool),
        ('thrust', ctypes.c_bool),
        ('turn', ctypes.c_int8),
        ("putchar_buffer",ctypes.c_int8 * 100),
        ("putchar_go", ctypes.c_bool)
    ]
  
class microarena_io_r_t(EightByteAlignedStructure):
    _fields_ = [
        ('angle',ctypes.c_double),
        ('angle_rate', ctypes.c_double),
        ('speed', ctypes.c_double),
        ('radar_d', ctypes.c_double),
        ('radar_f', ctypes.c_int8)
    ]

structures = [microarena_io_rw_t, microarena_io_r_t]
constants = [TURN_LEFT, TURN_RIGHT, TURN_NO]