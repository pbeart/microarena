import ctypes
from src.structure_utils import PackedStructure, structures_to_header


class mmiotcp_message_header(PackedStructure, ctypes.BigEndianStructure):
    _fields_ = [
        ('operation',ctypes.c_int8),
        ('target_type', ctypes.c_int8),
        ("addr",ctypes.c_int32),
        ("len", ctypes.c_int32)
    ]
    # todo: why does using bigendianstructure change c_int32 to c_int

if __name__ == "__main__":
    print(structures_to_header([mmiotcp_message_header], 8))