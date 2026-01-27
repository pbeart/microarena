import ctypes
import sys
import threading
import socket
import time

from src.spike_vm.struct_tcp_mmio_proto import mmiotcp_message_header

mmiotcp_message_header_sz = ctypes.sizeof(mmiotcp_message_header)

class _OtherThreadRaisedException(Exception):
    pass

OtherThreadRaisedException = _OtherThreadRaisedException("Exiting this thread because another thread raised")

class MMIOTcpServer:
    def __init__(self, struct_rw: ctypes.Structure, struct_r: ctypes.Structure, port: int, host: str = "localhost"):
        self.port = port
        self.host = host

        self.struct_rw = struct_rw
        self.struct_rw_t = type(struct_rw)
        self.struct_r = struct_r
        self.struct_r_t = type(struct_r)

        self.lock_struct_r = threading.Lock()
        self.lock_struct_rw = threading.Lock()

        self._errors: list[Exception] = []

        self.handler_thread: threading.Thread|None = None

    def start(self):
        self.handler_thread = threading.Thread(target=self._make_run_func_handle_errors(self._run))
        self.handler_thread.start()

        while True:
            time.sleep(2)
            with self._lock_from_target_type(ord("W")):
                print(self.struct_rw)

    def _lock_from_target_type(self, target_type: int):
        if target_type == ord("R"): # r
            return self.lock_struct_r
        elif target_type == ord("W"): # rw
            return self.lock_struct_rw
        else:
            raise ValueError(f"Unknown target type {target_type} ({chr(target_type)})")
        
    def _struct_from_target_type(self, target_type: int):
        if target_type == ord("R"): # r
            return self.struct_r
        elif target_type == ord("W"): # rw
            return self.struct_rw
        else:
            raise ValueError(f"Unknown target type {target_type} ({chr(target_type)})")
        
    def _set_struct_from_target_type(self, target_type: int, buffer):
        if target_type == ord("R"): # r
            self.struct_r = self.struct_r_t.from_buffer_copy(buffer)
        elif target_type == ord("W"): # rw
            self.struct_rw =self.struct_rw_t.from_buffer_copy(buffer)
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
    
    def check(self):
        "Check if any children raised, if so then raise."
        if len(self._errors) != 0:
            raise OtherThreadRaisedException
        
    def _run(self):

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        def handle_client(c, caddr):
            print("Starting handler!")
            try:
                while True:
                    d = b""

                    while len(d) < mmiotcp_message_header_sz:
                        r = c.recv(mmiotcp_message_header_sz - len(d))
                        if len(r) == 0:
                            raise ConnectionError("Socket closed")
                        d += r
                        print("Received", r, "now got", d, "expecting length", mmiotcp_message_header_sz)
                        
                    header = mmiotcp_message_header.from_buffer_copy(d)

                    target_struct = self._struct_from_target_type(header.target_type)


                    if header.operation == ord("w"): # write operation, more data follows
                        print("Received write")
                        payload = b""
                        print(f"Write operation, 0x{header.len:X} bytes @0x{header.addr:X}:")
                        while len(payload) < header.len:
                            print("Got payload", payload, "expecting", header.len, "will recv", (header.len - len(payload)))
                            r = c.recv(header.len - len(payload))
                            if len(r) == 0:
                                raise ConnectionError("Socket closed")
                            payload += r
                            
                        print(f"{payload}")

                        target_size = ctypes.sizeof(target_struct)

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


        s.bind((self.host, self.port))
        s.listen()

        threads = []
        try:
            while True:
                print("Acceptin")
                c, addr = s.accept()
                print("Accepted one, starting thread")
                t = threading.Thread(target=self._make_run_func_handle_errors(handle_client), args=(c, addr))
                t.start()

                threads.append(t)

                if len(self._errors) != 1:
                    raise OtherThreadRaisedException
        finally:
            if s:
                s.close()
            for t in threads:
                t.join()
        print("done")

if __name__ == "__main__":
    from src.spike_vm import struct_mmio
    s = MMIOTcpServer(struct_mmio.microarena_io_rw_t(), struct_mmio.microarena_io_r_t(), 9999)
    s.start()