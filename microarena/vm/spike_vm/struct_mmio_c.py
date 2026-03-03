from ..structure_utils import definitions_to_source
from .struct_mmio import structures, constants

if __name__ == "__main__":
    print(definitions_to_source(constants))