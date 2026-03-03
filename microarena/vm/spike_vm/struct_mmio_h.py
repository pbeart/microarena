from ..structure_utils import declarations_to_header
from .struct_mmio import structures, constants

if __name__ == "__main__":
    print(declarations_to_header(structures, constants, 8))