from OpenGL.GL import *
from io import BytesIO
from array import array
from struct import Struct
from PyQt5.QtGui import QImage, QPainter

from .read_binary import *

def decode_rgb565(color_val):
    b = (color_val & 0b11111) * (256//32)
    g = ((color_val >> 5) & 0b111111) * (256//64)
    r = ((color_val >> 11) & 0b11111) * (256//32)
    return r, g, b, 255


def addrgba(col1, col2):
    return col1[0]+col2[0], col1[1]+col2[1], col1[2]+col2[2], col1[3]+col2[3]


def multrgba(col, c):
    return col[0] * c, col[1] * c, col[2] * c, col[3] * c


def divrgba(col, c):
    return col[0] // c, col[1] // c, col[2] // c, col[3] // c

colors_format = Struct(">HH")
pixelmask_format = Struct(">I")
colors_unpack = colors_format.unpack
pixelmask_unpack = pixelmask_format.unpack

class Texture(object):
    def __init__(self, name):
        self.name = name
        self._loaded = False

    def dump_to_file(self, filepath):
        img = QImage(self.size_x, self.size_y, QImage.Format_ARGB32)
        rgbadata = self.rgba
        for ix in range(self.size_x):
            for iy in range(self.size_y):
                baseindex = ix * 4 + iy * self.size_x * 4
                r = rgbadata[baseindex + 0]
                g = rgbadata[baseindex + 1]
                b = rgbadata[baseindex + 2]
                a = rgbadata[baseindex + 3]
                img.setPixel(ix, iy, (a <<24) | (r << 16) | (g << 8) | b)

        img.save(filepath, "PNG")

    def is_loaded(self):
        return self._loaded

    def from_file(self, f):

        f.seek(0)
        print(f.read(0x20))
        self.size_x2 = read_uint32(f)
        self.size_y2 = read_uint32(f)
        self.unkint1 = read_uint32(f)
        self.unkint2 = read_uint32(f)
        self.format = f.read(0x10)
        self.unkint3 = read_uint32(f)
        self.unkint4 = read_uint32(f)
        self.unkint5 = read_uint32(f)
        self.unkint6 = read_uint32(f)
        self.unkints = f.read(0x10)
        self.mipcount = read_uint32(f)
        self.size_x = read_uint32(f)
        self.size_y = read_uint32(f)
        self.mipcount2 = read_uint32(f)
        print(self.size_x, self.size_x2)
        print(self.size_y, self.size_y2)
        assert self.size_x == self.size_x2
        assert self.size_y == self.size_y2
        assert self.mipcount == self.mipcount2
        self.success = True

        print(self.format[:8])
        if self.format[:8] != b"\x00\x00\x00\x001TXD" or self.mipcount == 0:
            self.success = False
            return
        assert self.format[:8] == b"\x00\x00\x00\x001TXD"
        assert self.mipcount > 0
        self.rgba = bytearray(self.size_x*self.size_y*4)

        assert f.read(4) == b" PIM"
        pimsize = read_uint32_le(f)
        pic_data = f.read(pimsize)
        x, y = 0, 0

        size_x = self.size_x
        size_y = self.size_y
        rgbadata = self.rgba

        for ii in range(0, len(pic_data) // 8, 4):
            for ii2 in range(0, 4):
                block = pic_data[(ii + ii2) * 8:(ii + ii2 + 1) * 8]

                # col0, col1, pixmask = unpack(">HHI", block)
                col0, col1 = colors_unpack(block[:4])  # unpack(">HH", block[:4])
                pixmask = pixelmask_unpack(block[4:])[0]  # unpack(">I", block[4:])[0]

                color0 = decode_rgb565(col0)
                color1 = decode_rgb565(col1)
                iix = (ii2 % 2) * 4
                iiy = (ii2 // 2) * 4

                if col0 > col1:
                    # col2 = (2*col0 + col1) // 3
                    # col3 = (2*col1 + col0) // 3

                    color2_r = (2 * color0[0] + color1[0]) // 3
                    color2_g = (2 * color0[1] + color1[1]) // 3
                    color2_b = (2 * color0[2] + color1[2]) // 3
                    color2_a = 255  # (2*color0[0] + color1[0]) // 3

                    color3_r = (2 * color1[0] + color0[0]) // 3
                    color3_g = (2 * color1[1] + color0[1]) // 3
                    color3_b = (2 * color1[2] + color0[2]) // 3
                    color3_a = 255  # (2*color0[0] + color1[0]) // 3

                    # color2 = divrgba(addrgba(multrgba(color0, 2), color1), 3)
                    # color3 = divrgba(addrgba(multrgba(color1, 2), color0), 3)

                    # colortable = (decode_rgb565(col0), decode_rgb565(col1),
                    #              decode_rgb565(col2), decode_rgb565(col3))

                else:
                    # col2 = (col0 + col1) // 2
                    # col3 = 0

                    # color2 = divrgba(addrgba(color0, color1), 2)
                    color2_r = (color0[0] + color1[0]) // 2
                    color2_g = (color0[1] + color1[1]) // 2
                    color2_b = (color0[2] + color1[2]) // 2
                    color2_a = 255  # (2*color0[0] + color1[0]) // 3
                    color3_r, color3_g, color3_b, color3_a = 0, 0, 0, 0  # = (0, 0, 0, 0)

                    # colortable = (decode_rgb565(col0), decode_rgb565(col1),
                    #              decode_rgb565(col2), (0, 0, 0, 0))

                colortable = (color0, color1,
                              (color2_r, color2_g, color2_b, color2_a),
                              (color3_r, color3_g, color3_b, color3_a))
                # colortable = (color0, color0, color1, color1)
                # for ix in range(4):
                #    for iy in range(4):
                for iii in range(16):
                    iy = iii // 4
                    ix = iii % 4
                    index = (pixmask >> ((15 - iii) * 2)) & 0b11
                    # col = index * (256//4)
                    # a = 255
                    # r, g, b, a = color0

                    r, g, b, a = colortable[index]
                    # try:
                    if x + ix + iix < size_x and y + iy + iiy < size_y:
                        #pix[x + ix + iix, y + iy + iiy] = r, g, b, a
                        array_x = x + ix + iix
                        array_y = (y + iy + iiy)
                        rgbadata[array_x*4 + array_y*size_x*4 + 0] = r
                        rgbadata[array_x*4 + array_y * size_x*4 + 1] = g
                        rgbadata[array_x*4 + array_y * size_x*4 + 2] = b
                        rgbadata[array_x*4 + array_y * size_x*4 + 3] = a
                    else:
                        print("tried to write outside of bounds:", size_x, size_y, x + ix + iix, y + iy + iiy)

            x += 8
            if x >= size_x:
                x = 0
                y += 8
        self.rgba = bytes(self.rgba)
        self._loaded = True

class TextureArchive(object):
    def __init__(self, archive):
        self.textures = {}
        for texture in archive.textures:
            name = bytes(texture.res_name)
            #print(name)
            self.textures[name] = texture

        self._cached = {}
        self.tex = glGenTextures(1)

    def reset(self):
        self._cached = {}

    def initialize_texture(self, texname):
        if texname in self._cached:
            return self._cached[texname]

        if texname not in self.textures:
            print("Texture not found:", texname)
            return None


        # f = self.textures[texname].fileobj
        tex = Texture(texname)
        #tex.from_file(f)
        ID = glGenTextures(1)
        self._cached[texname] = (tex, ID)
        self.load_texture(texname)
        return self._cached[texname]

    def load_texture(self, texname):
        if texname not in self._cached:
            return None


        tex, ID = self._cached[texname]

        if tex.is_loaded():
            return self._cached[texname]

        f = self.textures[texname].fileobj
        tex.from_file(f)

        if tex.success:
            glBindTexture(GL_TEXTURE_2D, ID)
            glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_BASE_LEVEL, 0);
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAX_LEVEL, 0);
            # glPixelStorei(GL_UNPACK_ROW_LENGTH, tex.size_x)
            print("call info", tex.size_x, tex.size_y, tex.size_x * tex.size_y * 4, len(tex.rgba))
            print(ID)
            glTexImage2D(GL_TEXTURE_2D, 0, 4, tex.size_x, tex.size_y, 0, GL_RGBA, GL_UNSIGNED_BYTE, tex.rgba)# b"\x00"*tex.size_x*tex.size_y*4)#tex.rgba)
            #glTexImage2D(GL_TEXTURE_2D, 0, 4, tex.size_x, tex.size_y, 0, GL_RGBA, GL_UNSIGNED_BYTE, b"\x7F"*tex.size_x*tex.size_y*4)
            #testsize = 32
            #glTexImage2D(GL_TEXTURE_2D, 0, 4, testsize, testsize, 0, GL_RGBA, GL_UNSIGNED_BYTE,
            #             b"\x7F" * testsize * testsize * 4)
            print("error after call", glGetError())
            #self._cached[texname] = (tex, ID)

            return self._cached[texname]
        else:
            print("loading tex wasn't successful")
            return None

    def get_texture(self, texname):
        if texname in self._cached:
            return self._cached[texname]
        else:
            self.initialize_texture(texname)
            return self.load_texture(texname)

