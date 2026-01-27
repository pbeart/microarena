import ctypes
import re
import time
from typing import Type

import pexpect.replwrap
from src import simdriver

from src.spike_vm import struct_mmio

from src.mmio_tcp_server import MMIOTcpServer

import pexpect

class UnexpectedEOFException(Exception):
    pass

class SpikeTrapException(Exception):
    pass

class SpikeAccessFaultTrapException(SpikeTrapException):
    pass

class SpikeUnknownTrapException(SpikeTrapException):
    pass


class SpikeSimDriver[MMIO_STRUCT_R_T: ctypes.Structure, MMIO_STRUCT_RW_T: ctypes.Structure](simdriver.SimDriver):

    @staticmethod
    def _parse_lds_config(path):
        d = {}
        with open(path, "r") as f:
            for n, line in enumerate(f.readlines()):
                try:
                    line = line.strip()
                    if not line: continue
                    elif line.startswith("/*"): continue
                    elif "=" in line:
                        if line.endswith(";"): 
                            line_trimmed = line[:-1]
                            l = line_trimmed.split("=")
                            key = l[0].strip()
                            value = int(l[1].strip(), base=0)
                            d[key] = value
                            continue
                    raise ValueError("Invalid line. Must be blank, start with /* or be key=value;")
                except ValueError as e:
                    raise ValueError(f"Couldn't parse line {n} of linker script config:\n{line}")
        return d
    
    def __init__(self, mmio_struct_rw: MMIO_STRUCT_RW_T, mmio_struct_r: MMIO_STRUCT_R_T, memories_lds_path: str, spike_binary: str, isa_str: str, mmio_tcp_so: str, target_binary: str):

        self.tcp_mmio_client = MMIOTcpServer(mmio_struct_rw, mmio_struct_r, "localhost")
        
        self._mmio_tcp_so = mmio_tcp_so
        self._target_binary = target_binary
        self._isa_str = isa_str

        memories = self._parse_lds_config(memories_lds_path)
        ram_start = memories["RAM_START"]
        ram_length = memories["RAM_LENGTH"]

        stack_start = memories["STACK_START"]
        stack_length = memories["STACK_LENGTH"]

        mmio_r_start = memories["MMIO_R_START"]
        mmio_r_length = memories["MMIO_R_LENGTH"]

        mmio_rw_start = memories["MMIO_RW_START"]
        mmio_rw_length = memories["MMIO_RW_LENGTH"]


        self._spawn = None
        self._repl = None

        self._spike = spike_binary

        self._memory_regions = [(ram_start, ram_length), (stack_start, stack_length)]
        
        self._mmio_r_region = (mmio_r_start, mmio_r_length)
        self._mmio_rw_region = (mmio_rw_start, mmio_rw_length)


    def start(self):
        port = self.tcp_mmio_client.start()
        args = [
            "-d",
            #"-l",
            #"--log=log.txt.tmp",
            "--isa",
            self._isa_str,
            "-m" + ",".join(f"0x{start:08X}:0x{length:X}" for (start, length) in self._memory_regions),
            f"--extlib={self._mmio_tcp_so}",
            f"--device=mmio_tcp,r,0x{self._mmio_r_region[0]:08X},0x{self._mmio_r_region[1]:X},localhost,{port}",
            f"--device=mmio_tcp,rw,0x{self._mmio_rw_region[0]:08X},0x{self._mmio_rw_region[1]:X},localhost,{port}",
            self._target_binary
        ]


        print("Running", " ".join([self._spike, *args]))
        self._spawn = pexpect.spawn(self._spike, args, encoding="utf-8")
        self._spawn.delaybeforesend = 0.0
        try:
            self._repl = pexpect.replwrap.REPLWrapper(self._spawn, "(spike) ", prompt_change=None)
        except pexpect.exceptions.EOF as e:
            assert self._spawn is not None
            raise UnexpectedEOFException(self._spawn.before)

    def _handle_spike_output(self, output: str):
        for line in output.splitlines():
            m = re.match(r"^core\s*[0-9]+: exception ([a-zA-Z0-9_]+)", line)
            if m is None: continue
            exception = m.group(1)
            if exception == "trap_instruction_access_fault":
                t = SpikeAccessFaultTrapException
            else:
                t = SpikeUnknownTrapException

            raise t(output)
        
    def get_mmio_struct_rw(self) -> MMIO_STRUCT_RW_T:
        return self.tcp_mmio_client.struct_rw
    
    def set_mmio_struct_r(self, structure: MMIO_STRUCT_R_T):
        self.tcp_mmio_client.struct_r = structure

    def _communicate(self, send):
        assert self._repl is not None
        assert self._spawn is not None

        try:
            
            response: str = self._repl.run_command(send)
            self._handle_spike_output(response)
        except pexpect.exceptions.EOF as e:
            assert self._spawn is not None
            raise UnexpectedEOFException(self._spawn.before)
    def step(self):
        self.tcp_mmio_client.check_and_raise()
        # send space because of some funky logic in REPLWrapper, this is needed to get a single newline
        self._communicate(" ")