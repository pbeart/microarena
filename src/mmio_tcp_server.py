import ctypes
import os
import sys
import threading
import socket
import time
import faulthandler

from src.spike_vm.struct_tcp_mmio_proto import mmiotcp_message_header

mmiotcp_message_header_sz = ctypes.sizeof(mmiotcp_message_header)

class _OtherThreadRaisedException(Exception):
    pass

OtherThreadRaisedException = _OtherThreadRaisedException("Exiting this thread because another thread raised")

class MMIOTcpServer[MMIO_STRUCT_RW_T: ctypes.Structure, MMIO_STRUCT_R_T: ctypes.Structure]:
    def __init__(self, struct_rw: MMIO_STRUCT_RW_T, struct_r: MMIO_STRUCT_R_T, host: str = "localhost"):
        self.host = host

        self._struct_rw: MMIO_STRUCT_RW_T = struct_rw
        self._struct_rw_t = type(struct_rw)
        self._struct_r: MMIO_STRUCT_R_T = struct_r
        self._struct_r_t = type(struct_r)

        self._lock_struct_r = threading.Lock()
        self._lock_struct_rw = threading.Lock()

        self._errors: list[Exception] = []

        self._handler_thread: threading.Thread|None = None

        self._exit = False

    @property
    def struct_rw(self):
        with self._lock_from_target_type(ord("W")):
            return self._struct_rw

    @struct_rw.setter
    def struct_rw(self, value):
        with self._lock_from_target_type(ord("W")):
            self._struct_rw = value

    @property
    def struct_r(self):
        with self._lock_from_target_type(ord("R")):
            return self._struct_r

    @struct_r.setter
    def struct_r(self, value):
        with self._lock_from_target_type(ord("R")):
            self._struct_r = value

    def start(self):

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setblocking(False)


        s.bind((self.host, 0))
        s.listen()

        port = s.getsockname()[1]
        self._handler_thread = threading.Thread(target=self._make_run_func_handle_errors(self._run), args=[s])
        self._handler_thread.start()
        return port
        

    def _lock_from_target_type(self, target_type: int):
        if target_type == ord("R"): # r
            return self._lock_struct_r
        elif target_type == ord("W"): # rw
            return self._lock_struct_rw
        else:
            raise ValueError(f"Unknown target type {target_type} ({chr(target_type)})")
        
    def _struct_from_target_type(self, target_type: int):
        if target_type == ord("R"): # r
            return self._struct_r
        elif target_type == ord("W"): # rw
            return self._struct_rw
        else:
            raise ValueError(f"Unknown target type {target_type} ({chr(target_type)})")
        
    def _set_struct_from_target_type(self, target_type: int, buffer):
        if target_type == ord("R"): # r
            self._struct_r = self._struct_r_t.from_buffer_copy(buffer)
        elif target_type == ord("W"): # rw
            self._struct_rw =self._struct_rw_t.from_buffer_copy(buffer)
        else:
            raise ValueError(f"Unknown target type {target_type} ({chr(target_type)})")
        
    def _make_run_func_handle_errors(self, func):
        def f(*args, **kwargs):
            try:
                func(*args, **kwargs)
            except Exception as e:
                self._errors.append(e)
                raise(e)
        return f
    
    def check_and_raise(self):
        "Check if any children raised, if so then raise."
        if len(self._errors) != 0:
            raise OtherThreadRaisedException
        
    def cleanup(self):
        self._exit = True
        time.sleep(1)

        if self._handler_thread is not None:
            self._handler_thread.join(5.0)

            if self._handler_thread.is_alive(): # setting _exit failed, exit forcefully and debug
                print("Threads did not exit in time")
                faulthandler.dump_traceback(all_threads=True)
                os._exit(1)

    def _recv_while_exit_checking(self, conn: socket.socket, b: int):
        while True:
            try:
                return conn.recv(b)
            except BlockingIOError:
                pass
            if self._exit: sys.exit()
            
    def _accept_while_exit_checking(self, s: socket.socket):
        while True:
            if self._exit: sys.exit()
            try:
                return s.accept()
            except BlockingIOError:
                pass
    
    def _handle_client(self, c: socket.socket, caddr):

        print("Starting handler!")
        try:
            while True:
                if self._exit:
                    sys.exit()
                d = b""

                while len(d) < mmiotcp_message_header_sz:
                    r = self._recv_while_exit_checking(c, mmiotcp_message_header_sz - len(d))
                    if len(r) == 0:
                        raise ConnectionError("Socket closed")
                    d += r
                    print("Received", r, "now got", d, "expecting length", mmiotcp_message_header_sz)
                    
                header = mmiotcp_message_header.from_buffer_copy(d)

                target_struct = self._struct_from_target_type(header.target_type)

                is_targeting_struct_r = header.target_type == ord("R")


                if header.operation == ord("w"): # write operation, more data follows
                    target_size = ctypes.sizeof(target_struct)

                    print("Received write")
                    if is_targeting_struct_r:
                        # can't prohibit this because Spike loves to initialise read only MMIO
                        print(f"WARN: Attempted write to read-only MMIO: 0x{header.len:X}bytes @{header.addr:08X} for struct {target_struct.__class__.__name__} of length {target_size:X}")

                    payload = b""
                    print(f"Write operation, 0x{header.len:X} bytes @0x{header.addr:X}:")
                    while len(payload) < header.len:
                        print("Got payload", payload, "expecting", header.len, "will recv", (header.len - len(payload)))
                        r = self._recv_while_exit_checking(c, header.len - len(payload))
                        if len(r) == 0:
                            raise ConnectionError("Socket closed")
                        payload += r
                        
                    print(f"{payload}")

                    

                    if header.addr < 0 or (header.addr + header.len) > target_size:
                        print(f"WARN: OOB write address/length: 0x{header.len:X}bytes @{header.addr:08X} for struct {target_struct.__class__.__name__} of length {target_size:X}")
                    else:
                        print("Getting lock for", target_struct)
                        with self._lock_from_target_type(header.target_type):
                            struct_bytes = bytearray(target_struct)
                            struct_bytes[header.addr:header.addr+header.len] = payload

                            self._set_struct_from_target_type(header.target_type, struct_bytes)


                elif header.operation == ord("r"):
                    print("Received read")
                    print(f"Read operation, 0x{header.len:X} bytes @0x{header.addr:X}")

                    target_size = ctypes.sizeof(target_struct)
                    if header.addr < 0 or (header.addr + header.len) > target_size:
                        print(f"WARN: OOB read address/length: 0x{header.len:X}bytes @{header.addr:08X} for struct {target_struct.__class__.__name__} of length {target_size:X}")
                    else:
                        print("Getting lock for", target_struct)
                        with self._lock_from_target_type(header.target_type):
                            todeliver = bytearray(target_struct)[header.addr:header.addr+header.len]
                        while len(todeliver) > 0:
                            sent = c.send(todeliver)
                            todeliver = todeliver[sent:]
                else:
                    raise ValueError(f"Got unexpected operation character {chr(header.operation)} ({header.operation})")
                
                if len(self._errors) != 1:
                    raise OtherThreadRaisedException
        finally:
            c.close()    

    def _run(self, s: socket.socket):

        threads = []
        try:
            while True:
                if self._exit: sys.exit()
                c, addr = self._accept_while_exit_checking(s)
                c.setblocking(False)
                t = threading.Thread(target=self._make_run_func_handle_errors(self._handle_client), args=(c, addr))
                t.start()

                threads.append(t)

                if len(self._errors) != 1:
                    pass
        finally:
            if s:
                s.close()
            for t in threads:
                t.join()
        print("done")

    

if __name__ == "__main__":
    from src.spike_vm import struct_mmio
    s = MMIOTcpServer(struct_mmio.microarena_io_rw_t(), struct_mmio.microarena_io_r_t())
    s.start()