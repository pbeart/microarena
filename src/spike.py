import ctypes
import re
import time
from typing import Type

import pexpect.replwrap
from src import simdriver

from src.spike_vm import mmio_struct

import pexpect

class UnexpectedEOFException(Exception):
    pass

class SpikeTrapException(Exception):
    pass

class SpikeAccessFaultTrapException(SpikeTrapException):
    pass

class SpikeUnknownTrapException(SpikeTrapException):
    pass


class SpikeSimDriver(simdriver.SimDriver):

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
    
    def __init__(self, mmio_struct_rw: ctypes.Structure, mmio_struct_r: ctypes.Structure, memories_lds_path: str, spike_binary: str, isa_str: str, filebacked_so: str, filebacked_rw_path: str, filebacked_r_path: str, target_binary: str):

        self.mmio_struct_rw = mmio_struct_rw
        self.mmio_struct_r = mmio_struct_r

        memories = self._parse_lds_config(memories_lds_path)
        ram_start = memories["RAM_START"]
        ram_length = memories["RAM_LENGTH"]

        stack_start = memories["STACK_START"]
        stack_length = memories["STACK_LENGTH"]

        mmio_r_start = memories["MMIO_R_START"]
        mmio_r_length = memories["MMIO_R_LENGTH"]

        mmio_rw_start = memories["MMIO_RW_START"]
        mmio_rw_length = memories["MMIO_RW_LENGTH"]
        
        self._filebacked_mmio_r_path = filebacked_r_path
        self._filebacked_mmio_rw_path = filebacked_rw_path

        self._write_mmio_r_filebacked()
        self._create_mmio_rw_filebacked()

        self._spawn = None
        self._repl = None

        self._spike = spike_binary

        memory_regions = [(ram_start, ram_length), (stack_start, stack_length)]
        
        self._args = [
            "-d",
            #"-l",
            #"--log=log.txt.tmp",
            "--isa",
            isa_str,
            "-m" + ",".join(f"0x{start:08X}:0x{length:X}" for (start, length) in memory_regions),
            f"--extlib={filebacked_so}",
            f"--device=filebacked,r,0x{mmio_r_start:08X},0x{mmio_r_length:X},{filebacked_r_path}",
            f"--device=filebacked,rw,0x{mmio_rw_start:08X},0x{mmio_rw_length:X},{filebacked_rw_path}",
            target_binary
        ]

    def _write_mmio_r_filebacked(self):
        f = open(self._filebacked_mmio_r_path, "wb")
        f.write(bytearray(self.mmio_struct_r))
        f.close()

        #print("Wrote", bytearray(self.mmio_struct_r))

    def _create_mmio_rw_filebacked(self):
        f = open(self._filebacked_mmio_rw_path, "wb")
        f.write(bytearray(self.mmio_struct_rw))
        f.close()

    def _read_mmio_rw_filebacked(self):
        f = open(self._filebacked_mmio_rw_path, "rb")
        b = f.read()
        f.close()

        #print("Read",b)

        self.mmio_struct_rw = type(self.mmio_struct_rw).from_buffer_copy(b)

    def start(self):
        print("Running", " ".join([self._spike, *self._args]))
        self._spawn = pexpect.spawn(self._spike, self._args, encoding="utf-8")
        try:
            self._repl = pexpect.replwrap.REPLWrapper(self._spawn, "(spike) ", prompt_change=None)
        except pexpect.exceptions.EOF as e:
            assert self._spawn is not None
            raise UnexpectedEOFException(self._spawn.before)
        
        time.sleep(1)
        #print("Immediate:", self.spawn.read(1))

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

    def _communicate(self, send):
        assert self._repl is not None
        assert self._spawn is not None

        try:
            #print("Bf", self._spawn.before, self._spawn.buffer)
            self._write_mmio_r_filebacked()
            response = self._repl.run_command(send)
            self._handle_spike_output(response)
            self._read_mmio_rw_filebacked()
            print("Received `", response, "`")
        except pexpect.exceptions.EOF as e:
            assert self._spawn is not None
            raise UnexpectedEOFException(self._spawn.before)
        #print("Before", self._spawn.before)
        print(repr(self.mmio_struct_rw))
    def step(self):
        # send space because of some funky logic in REPLWrapper, needed to get a single newline
        self._communicate(" ")

struct_r = mmio_struct.microarena_io_r_t()
struct_rw = mmio_struct.microarena_io_rw_t()

s = SpikeSimDriver(struct_rw, struct_r, "./src/spike_vm/memories.lds", "../riscv-isa-sim/build/spike", "rv32imafdc", "./src/spike_vm/mmu_filebacked/build/filebacked.so", "store_to.tmp", "load_from.tmp", "./src/spike_vm/build/target")

s.start()
for i in range(4000):
    s.step()
    if s.mmio_struct_rw.stdout_go != 0:
        print("".join(chr(x) for x in s.mmio_struct_rw.stdout_buffer))
        break
