#include <riscv/abstract_device.h>
#include "../build/tcp_mmio_proto.generated.h"
#include <stdio.h>
#include <fstream>
#include <iostream>

#include <unistd.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <arpa/inet.h>
#include <netinet/tcp.h>

enum mmio_tcp_type {
    mmio_tcp_TYPE_R,
    mmio_tcp_TYPE_RW
};


/*
MMIO protocol:

-- Sending to server_address --
Bytes 0           1              5             9
Bits  0           8             40            72
      | char mtyp | int64_t addr | int64_t len | char data[len] (iff mtyp = PROTO_MESSAGE_TYPE_W) ...

-- Receiving (after sent PROTO_MESSAGE_TYPE_R) --
Bytes 0
Bits  0
      | char data[len] ...
*/

typedef char proto_message_type;
char PROTO_MESSAGE_TYPE_R = 'r';
char PROTO_MESSAGE_TYPE_W = 'w';

typedef char proto_target_type;
char PROTO_TARGET_TYPE_R = 'R';
char PROTO_TARGET_TYPE_RW = 'W';

float get_subtime() {
    struct timespec spec;

    clock_gettime(CLOCK_REALTIME, &spec);
    float fs = spec.tv_nsec / 1.0e9;

    long secs = spec.tv_sec % 1000;

    float st = secs + fs;

    return st;
}


class mmio_tcp_t : public abstract_device_t
{
    mmio_tcp_type typ;
    int base;
    int _size;
    std::string host;
    int port;

    proto_target_type target_type;

    struct hostent *hostnm;
    struct sockaddr_in server_address; 

    int sock;  
    
    public:
    mmio_tcp_t(mmio_tcp_type typ, int base, int size, std::string host, int port) : typ(typ), base(base), _size(size), host(host), port(port)
    {
        if (typ == mmio_tcp_TYPE_R) {
            target_type = PROTO_TARGET_TYPE_R;
        } else if (typ == mmio_tcp_TYPE_RW) {
            target_type = PROTO_TARGET_TYPE_RW;
        } else {
            __builtin_unreachable();
        }
        server_address.sin_family      = AF_INET;
        server_address.sin_port        = htons(port);

        if ((sock = socket(AF_INET, SOCK_STREAM, 0)) < 0)
        {
            throw std::runtime_error("mmio_tcp: socket() failed");
        }

        int flag = 1;
        if (setsockopt(sock, IPPROTO_TCP, TCP_NODELAY, (char *) &flag, sizeof(int)) < 0) {
            throw std::runtime_error("mmio_tcp: setsocketopt() failed: " + std::string(strerror(errno)));
        }

        inet_aton(host.c_str(), (struct in_addr *) &server_address.sin_addr.s_addr);

        if (connect(sock, (struct sockaddr *)&server_address, sizeof(server_address)) < 0)
        {
            throw std::runtime_error("mmio_tcp: connect() failed for " + host + ":" + std::to_string(port));
        }

        
    }   

    ~mmio_tcp_t() {
        close(sock);
        
    }

    bool load(reg_t addr, size_t len, uint8_t* bytes)
    {   

        printf("LOAD t%f -- SELF=%p ADDR=0x%lx LEN=%lu ADDR=%p\n", get_subtime(), this, addr, len, (void*)bytes);

        mmiotcp_message_header message;

        message.operation = PROTO_MESSAGE_TYPE_R;
        message.target_type = target_type;
        message.addr = htonl(addr);
        message.len = htonl(len);

        if (send(sock, &message, sizeof(message), 0) < 0)
        {
            throw std::runtime_error("mmio_tcp: send() failed during load");
        }

        
        uint8_t* end = bytes + len;
        uint8_t* ptr = bytes;

        printf("I want to receive %zu bytes\n", len);
        while (ptr < end) {
            int sent = recv(sock, ptr, end - ptr, 0);
            printf("Received %d\n", sent);
            if (sent < 0) {
                throw std::runtime_error("mmio_tcp: recv() failed during load");
            }

            ptr += sent;
        }
        

        printf("BYTES=0x");
        for (reg_t i=0; i<len; i++) {
            printf("%x", bytes[i]);
        }
        printf("\n");
        return true;
    }


    bool store(reg_t addr, size_t len, const uint8_t* bytes)
    {
        printf("STORE t%f -- SELF=%p ADDR=0x%lx LEN=%lu ADDR=%p BYTES=0x", get_subtime(),this, addr, len, (const void*)bytes);
        for (reg_t i=0; i<len; i++) {
            printf("%x", bytes[i]);
        }
        printf("\n");

        mmiotcp_message_header message;

        message.operation = PROTO_MESSAGE_TYPE_W;
        message.target_type = target_type;
        message.addr = htonl(addr);
        message.len = htonl(len);

        //printf("Sending %d, %d, %ld\n", message.addr, message.len, sizeof(message));
        if (send(sock, &message, sizeof(message), 0) < 0)
        {
            throw std::runtime_error("mmio_tcp: send() failed during store: " + std::string(strerror(errno)));
        }

        // send data
        
        if (send(sock, bytes, len, 0) < 0)
        {
            throw std::runtime_error("mmio_tcp: send() failed during store: " + std::string(strerror(errno)));
        }

        // we must receive a single byte response
        char buf[1];
        int received = 0;
        while (received < 1) {
            received = recv(sock, buf, 1, 0);
            if (received < 0) {
                throw std::runtime_error("mmio_tcp: recv() failed during store: " + std::string(strerror(errno)));
            }
        }
        if (buf[0] != 'K') {
            throw std::runtime_error("mmio_tcp: recv() did not receive acknowledgement ('K') during store, received: " + std::to_string(buf[0]));
        };
        
        printf("STORE: Acked\n");
        
        return true;
    }

    reg_t size() {
        return _size;
    }
};

std::string mmio_tcp_generate_dts(const sim_t* sim, const std::vector<std::string>& sargs UNUSED) {
    return "";
}

mmio_tcp_t* mmio_tcp_parse_from_fdt(const void* fdt, const sim_t* sim, reg_t* base, const std::vector<std::string>& sargs) {
    if (sargs.size() < 4) throw std::runtime_error("mmio_tcp: requires arguments (mode=r|rw, base, size, host, port)");
    char* tester;
    *base = strtoull(sargs[1].c_str(), &tester, 0);
    if (tester == sargs[1].c_str()) throw std::runtime_error("mmio_tcp: invalid base address");

    int size = strtoull(sargs[2].c_str(), &tester, 0); 
    if (tester == sargs[2].c_str()) throw std::runtime_error("mmio_tcp: invalid size");

    mmio_tcp_type typ;

    if (sargs[0] == "r") {
        typ = mmio_tcp_TYPE_R;
    } else if (sargs[0] == "rw") {
        typ = mmio_tcp_TYPE_RW;
    } else {
        throw std::runtime_error("mmio_tcp: mode must be `r` or `rw`");
    }

    int port = strtoull(sargs[4].c_str(), &tester, 0); 
    if (tester == sargs[4].c_str()) throw std::runtime_error("mmio_tcp: invalid size");

    return new mmio_tcp_t(typ, *base, size, sargs[3], port);//sargs[0]);
}

REGISTER_DEVICE(mmio_tcp, mmio_tcp_parse_from_fdt, mmio_tcp_generate_dts)
