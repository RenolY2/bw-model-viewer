from struct import unpack

def read_id(f):
    c1 = f.read(1)
    c2 = f.read(1)
    c3 = f.read(1)
    c4 = f.read(1)
    return c4+c3+c2+c1

def read_uint32(f):
    return unpack(">I", f.read(4))[0]


def read_uint32_le(f):
    return unpack("I", f.read(4))[0]


def read_uint16(f):
    return unpack(">H", f.read(2))[0]

def read_int16(f):
    return unpack(">h", f.read(2))[0]

def read_uint16_le(f):
    return unpack("H", f.read(2))[0]

def read_int16_le(f):
    return unpack("h", f.read(2))[0]

def read_float(f):
    return unpack(">f", f.read(4))[0]

def read_uint8(f):
    return unpack("B", f.read(1))[0]

def read_int8(f):
    return unpack("b", f.read(1))[0]

def read_float_le(f):
    return unpack("f", f.read(4))[0]