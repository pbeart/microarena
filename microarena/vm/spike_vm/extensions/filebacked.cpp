#include <riscv/abstract_device.h>
#include <stdio.h>
#include <fstream>
#include <iostream>

enum filebacked_type {
    FILEBACKED_TYPE_R,
    FILEBACKED_TYPE_RW
};

class filebacked_t : public abstract_device_t
{
    //std::string path;
    filebacked_type typ;
    int base;
    int _size;
    std::string file_path;
    
    public:
    filebacked_t(filebacked_type typ, int base, int size, std::string file_path) : typ(typ), base(base), _size(size), file_path(file_path) {}
    bool load(reg_t addr, size_t len, uint8_t* bytes)
    {   
        std::ifstream infile;
        infile.open(file_path);
        if (infile.fail()) throw std::runtime_error("filebacked: couldn't read from input file");

        infile.seekg(addr); // because addresses are relative to start of MMIO
        if (infile.fail()) throw std::runtime_error("filebacked: couldn't seek far enough in input file " + std::to_string(addr));

        infile.read((char*)bytes, len);
        if (infile.eof()) throw std::runtime_error("filebacked: couldn't read enough of input file: reading " + std::to_string(len) + " bytes at " + std::to_string(addr));
        if (infile.fail()) throw std::runtime_error("filebacked: couldn't read input file");

        infile.close();
        printf("LOAD -- SELF=%p ADDR=0x%lx LEN=%lu ADDR=%p\n BYTES=0x", this, addr, len, (void*)bytes);
        for (reg_t i=0; i<len; i++) {
            printf("%x", bytes[i]);
        }
        printf("\n");
        return true;
    }


    bool store(reg_t addr, size_t len, const uint8_t* bytes)
    {
        printf("STORE -- SELF=%p ADDR=0x%lx LEN=%lu ADDR=%p BYTES=0x", this, addr, len, (const void*)bytes);
        for (reg_t i=0; i<len; i++) {
            printf("%x", bytes[i]);
        }
        printf("\n");

        if (typ == FILEBACKED_TYPE_R) {
            printf("NOP - mode R\n");
            // spike really likes initialising readonly memories so have to let it write, but print a warning.
            return true;
        }
        
        std::fstream outstream(file_path, std::ios::in | std::ios::out);
        if (outstream.fail()) throw std::runtime_error("filebacked: couldn't open output file `" + file_path + "` for writing");

        outstream.seekp(addr); // because addresses are relative to start of MMIO
        if (outstream.fail()) throw std::runtime_error("filebacked: couldn't seek far enough in output file " + std::to_string(addr));

        outstream.write((char*)bytes, len);
        if (outstream.fail()) throw std::runtime_error("filebacked: couldn't write to output file");

        outstream.close();

        printf("WROTE %ld BYTES TO %s\n", len, file_path.c_str());
        
        return true;
    }

    reg_t size() {
        return _size;
    }
};

std::string filebacked_generate_dts(const sim_t* sim, const std::vector<std::string>& sargs UNUSED) {
    return "";
}

filebacked_t* filebacked_parse_from_fdt(const void* fdt, const sim_t* sim, reg_t* base, const std::vector<std::string>& sargs) {
    if (sargs.size() < 4) throw std::runtime_error("filebacked: requires arguments (mode=r|rw, base, size, file)");
    char* tester;
    *base = strtoull(sargs[1].c_str(), &tester, 0);
    if (tester == sargs[1].c_str()) throw std::runtime_error("filebacked: invalid base address");

    int size = strtoull(sargs[2].c_str(), &tester, 0); 
    if (tester == sargs[2].c_str()) throw std::runtime_error("filebacked: invalid size");

    filebacked_type typ;

    if (sargs[0] == "r") {
        typ = FILEBACKED_TYPE_R;
    } else if (sargs[0] == "rw") {
        typ = FILEBACKED_TYPE_RW;
    } else {
        throw std::runtime_error("filebacked: mode must be `r` or `rw`");
    }

    return new filebacked_t(typ, *base, size, sargs[3]);//sargs[0]);
}

REGISTER_DEVICE(filebacked, filebacked_parse_from_fdt, filebacked_generate_dts)
