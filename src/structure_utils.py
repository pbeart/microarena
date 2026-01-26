import ctypes
from dataclasses import dataclass
from typing import Type

class SelfExpositingStructure(ctypes.Structure):
    def __repr__(self):
        indent = " "
        
        s = f"<{type(self).__name__}\n"

        for f in self._fields_:
            name = f[0]
            v = getattr(self, name)
            if isinstance(v, ctypes.Array):
                value = "[" + ", ".join(repr(x) for x in v) + "]"
            else:
                value = repr(v)
            value_lines = value.splitlines()
            if len(value_lines) == 1: # print on one line
                s += f"{indent}{name}={value}\n"
            else:
                s += f"{indent}{name}=\n"
                for line in value_lines:
                    s += f"{indent*2}{line}\n"

        
        s += ">"

        return s
    
def MakeByteAlignedStructure(n):

    class ByteAlignedStructure(SelfExpositingStructure):
        _align_ = n
        _pack_ = n
    return ByteAlignedStructure

def builtin_ctype_to_c_type(ctype, structure):
    MAP_CTYPES = {
        ctypes.c_int32: "int32_t",
        ctypes.c_int16: "int16_t",
        ctypes.c_int8: "int8_t"
    }
    if not ctype in MAP_CTYPES:
        raise TypeError(f"Can't handle field of type {ctype} in {structure}.")

    return MAP_CTYPES[ctype]

def h_source_and_dependencies(structure: Type[ctypes.Structure], align_bytes):
    name = structure.__name__

    depends_on: set[Type[ctypes.Structure]] = set()

    indent = "    "
    s = "typedef struct {\n"
    for (field_name, field_type, *_) in structure._fields_:
        
        if issubclass(field_type, ctypes.Structure):
            depends_on.add(field_type)
            c_type = field_type.__name__
            length_specifier = ""

        elif issubclass(field_type, ctypes.Array):
            if issubclass(field_type._type_, ctypes.Structure): # type: ignore
                depends_on.add(field_type._type_)

            c_type = builtin_ctype_to_c_type(field_type._type_, structure)
            length_specifier = f"[{field_type._length_}]"
        else:
            c_type = builtin_ctype_to_c_type(field_type, structure)
            length_specifier = ""

        s += f"{indent}{c_type} {field_name}{length_specifier};\n"

    s += f"}}__attribute__((packed, aligned({align_bytes}))) {name};\n"

    return s, depends_on


def structures_to_header(structures: list[Type[ctypes.Structure]], align_bytes):

    nodes: dict[str, list["str"]] = {}
    structure_sources: dict[str, str] = {}
    
    to_check = structures

    while to_check:
        checking = to_check[:]
        to_check = []
        for structure_dependency in checking:
            if structure_dependency.__name__ in nodes: continue

            source, depends_on_structures = h_source_and_dependencies(structure_dependency, align_bytes)
            to_check += depends_on_structures
            structure_sources[structure_dependency.__name__] = source

            depends_on_names = [x.__name__ for x in depends_on_structures]
            nodes[structure_dependency.__name__] = depends_on_names

    out = "#pragma once\n#include <stdint.h>\n"

    while nodes:
        eliminated = []
        for name, node in nodes.items():
            if len(node) == 0:
                out += structure_sources[name] + "\n"
                eliminated.append(name)
        
        for to_eliminate in eliminated:
            del nodes[to_eliminate]
            for node in nodes.values():
                if to_eliminate in node: node.remove(to_eliminate)
    
    return out
