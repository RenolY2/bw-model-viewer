from OpenGL.GL import *
from struct import unpack
from .vectors import Vector3
from .read_binary import *
from .gx import VertexDescriptor, VTX, VTXFMT

vertexshader = [
"#version 330 core",
"layout (location = 0) in vec3 aPos; // the position variable has attribute position 0",
  
"out vec4 vertexColor; // specify a color output to the fragment shader",

"void main()",
"{",
"    gl_Position = vec4(aPos, 1.0); // see how we directly give a vec3 to vec4's constructor",
"    vertexColor = vec4(aPos.r, aPos.g, aPos.b, 1.0); // set the output variable to a dark-red color",
"}"
]

frag = [
#version 330 core
"out vec4 FragColor;",
  
"in vec4 vertexColor; // the input variable from the vertex shader (same name and same type) " ,

"void main()",
"{",
"    FragColor = vertexColor;",
"}"
]


class Model(object):
    def __init__(self):
        pass

    def render(self):
        pass


class BWModel(Model):
    def __init__(self):
        self.version = None
        self.nodecount = None
        self.additionalcount = None
        self.additionaldata = []
        self.unkint = None
        self.floattuple = None

        self.bgfname = "Model.bgf"

        self.nodes = []

    def from_file(self, f):
        self.version = (read_uint32(f), read_uint32(f))
        self.nodecount = read_uint16(f)
        self.additionaldatacount = read_uint16(f)
        self.unkint = read_uint32(f)
        self.floattuple = (read_float(f), read_float(f), read_float(f), read_float(f))


        bgfnamelength = read_uint32(f)
        self.bgfname = f.read(bgfnamelength)

        self.additionaldata = []
        for i in range(self.additionaldatacount):
            self.additionaldata.append(read_uint32(f))

        self._skip_section(f, b"MEMX")  # Unused

        self.nodes = []
        for i in range(self.nodecount):
            node = Node(self.additionaldatacount)
            node.from_file(f)
            self.nodes.append(node)

        cntname = f.read(4)
        print(cntname)
        assert cntname == b"TCNC"
        cnctsize = read_uint32_le(f)
        start = f.tell()
        assert cnctsize == self.unkint*4

        for i in range(self.unkint):
            parent = read_uint16_le(f)
            child = read_uint16_le(f)
            #print("Concat:", child, parent)
            self.nodes[child].parent = self.nodes[parent]

        assert f.tell() == start+cnctsize

    def _skip_section(self, f, secname):
        name = f.read(4)
        assert name == secname
        size = read_uint32_le(f)
        f.read(size)

class LODLevel(object):
    def __init__(self):
        self.vertices = []
        self.faces = []
        self.sections = []


class Primitive(object):
    def __init__(self, primtype):
        self.type = primtype
        self.vertices = []


class Node(object):
    def __init__(self, additionaldatacount):
        self.children = []
        self.parent = None
        self.transform = None

        self.additionaldatacount = additionaldatacount

        self.bbox = None # Boundary box
        self.rnod = None # Only used by soldier models?
        self.material = None

        self.sections = []

        self.name = "NodeName"

        self.unkshort1 = None
        self.unkshort2 = None
        self.unkshort3 = None
        self.padd = None
        self.xbs2count = None
        self.vscl = None

        self.vertices = []
        self.normals = []
        self.triprimitives = []

        self.additionaldata = []
        self.lods = []

    def setparent(self, parent):
        self.parent = parent

    def from_file(self, f):
        nodename = f.read(4)
        print("reading", nodename)
        assert nodename == b"EDON"
        nodesize = read_uint32_le(f)
        nodestart = f.tell()
        nodeend = f.tell() + nodesize

        nodenamelength = read_uint32(f)
        self.name = f.read(nodenamelength)
        headerstart = f.tell()
        # Do stuff
        self.unkshort1, self.unkshort2, self.unkshort3, self.padd, self.xbs2count = unpack(">HHHHI", f.read(12))
        assert self.padd == 0
        # unkshort1, unkshort2, unkshort3, padd = unpack(">HHHH", f.read(8))
        floats = unpack("f" * 11, f.read(4 * 11))
        self.transform = Transform(floats)

        assert f.tell() - headerstart == 0x38

        self.additionaldata = []
        for i in range(self.additionaldatacount):
            self.additionaldata.append(read_uint32(f))

        assert read_id(f) == b"BBOX"
        f.read(4)

        x1, y1, z1, x2, y2, z2 = unpack("ffffff", f.read(4*6))
        self.bbox = Box((x1, y1, z1), (x2, y2, z2))

        secname = read_id(f)
        size = read_uint32_le(f)

        while secname != b"MATL":
            if secname == b"RNOD":
                self.rnod = f.read(size)

            elif secname == b"VSCL":
                assert size == 4
                self.vscl = read_float_le(f)

            else:
                raise RuntimeError("Unknown secname {0}", secname)

            secname = read_id(f)
            size = read_uint32_le(f)

        assert secname == b"MATL"
        self.material = f.read(size)

        vertexdesc = 0

        while f.tell() < nodeend:
            secname = read_id(f)
            size = read_uint32_le(f)
            end = f.tell()+size

            if secname == b"SCNT":
                val = read_uint32(f)
                assert size == 4
                self.lods.append(val)

            elif secname == b"XBS2":
                print(hex(f.tell()))
                moremeshes = read_uint32(f) # maybe, unsure
                unknown = f.read(8)
                gx_data_size = read_uint32(f)
                gx_data_end = f.tell() + gx_data_size
                print(hex(gx_data_end), hex(gx_data_size))



                while f.tell() < gx_data_end:
                    opcode = read_uint8(f)

                    if opcode == 0x8:  # Load CP Reg
                        command = read_uint8(f)
                        val = read_uint32(f)
                        if command == 0x50:
                            vertexdesc &= ~0x1FFFF
                            vertexdesc |= val
                        elif command == 0x60:
                            vertexdesc &= 0x1FFFF
                            vertexdesc |= (val << 17)
                        else:
                            raise RuntimeError("unknown CP command {0:x}".format(command))

                    elif opcode == 0x10:  # Load XF Reg
                        x = read_uint32(f)
                        y = read_uint32(f)

                        """elif opcode&0xFA == 0x90:  # Triangles
                            vertex_count = read_uint16(f)
                            prim = Primitive(0x90)
    
                            for i in range(vertex_count):
                                matindex = read_uint8(f)
                                #posIndex = read_uint8(f)
                                posIndex = read_uint16(f)
                                tex1index = read_uint16(f)
                                prim.vertices.append(posIndex)
    
                            self.triprimitives.append(prim)"""

                    elif opcode & 0xFA == 0x98:  # Triangle strip
                        attribs = VertexDescriptor()
                        attribs.from_value(vertexdesc)

                        vertex_count = read_uint16(f)
                        prim = Primitive(0x98)
                        print(bin(vertexdesc))
                        print([x for x in attribs.active_attributes()])

                        for i in range(vertex_count):
                            primattrib = [None, None]
                            for attrib, fmt in attribs.active_attributes():
                                # matindex = read_uint8(f)

                                if attrib == VTX.Position:
                                    if fmt == VTXFMT.INDEX8:
                                        posIndex = read_uint8(f)
                                    elif fmt == VTXFMT.INDEX16:
                                        posIndex = read_uint16(f)
                                    else:
                                        raise RuntimeError("unknown position format")
                                    primattrib[0] = posIndex
                                elif attrib == VTX.Normal:
                                    if fmt == VTXFMT.INDEX8:
                                        normIndex = read_uint8(f)
                                    elif fmt == VTXFMT.INDEX16:
                                        normIndex = read_uint16(f)
                                    else:
                                        raise RuntimeError("unknown normal format")
                                    primattrib[1] = normIndex

                                elif fmt is not None:
                                    if fmt == VTXFMT.INDEX8:
                                        read_uint8(f)
                                    elif fmt == VTXFMT.INDEX16:
                                        read_uint16(f)
                                    else:
                                        RuntimeError("unknown fmt format")
                                else:
                                    read_uint8(f)

                            prim.vertices.append(primattrib)

                        self.triprimitives.append(prim)

                    elif opcode == 0x00:
                        pass
                    else:
                        print(self.name, hex(f.tell()-nodestart))
                        raise RuntimeError("Unknown opcode: {0:x}".format(opcode))

                f.seek(gx_data_end)

            elif secname == b"VPOS":
                if len(self.vertices) > 0:
                    f.read(size)
                    self.sections.append(secname)
                    break
                print(self.name, size)
                assert size%6 == 0
                #assert size%4 == 0

                for i in range(size//6):
                    #self.vertices.append((read_float_le(f), read_float_le(f), read_float_le(f)))
                    self.vertices.append((read_int16(f), read_int16(f), read_int16(f)))

            elif secname == b"VNRM":
                assert size%3 == 0
                for i in range(size//3):
                    self.normals.append((read_int8(f), read_int8(f), read_int8(f)))

            elif secname == b"VNBT":
                assert size%3 == 0
                assert size%9 == 0
                assert size % 36 == 0
                for i in range(size//36):
                    #self.normals.append((read_int8(f), read_int8(f), read_int8(f)))
                    #f.read(6)
                    self.normals.append((read_float(f), read_float(f), read_float(f)))
                    f.read(24)
            else:
                f.read(size)
            self.sections.append(secname)

        while f.tell() < nodeend:
            secname = read_id(f)
            size = read_uint32_le(f)
            f.read(size)
            self.sections.append(secname)

        assert f.tell() == nodeend

    def render(self):
        glColor3f(1.0, 0.0, 1.0)
        #glPointSize(2.0)

        #glBegin(GL_POINTS)
        #for x, y, z in self.vertices:
        #    glVertex3f(x * self.vscl, y * self.vscl, z * self.vscl)
        #glEnd()

        for prim in self.triprimitives:
            if prim.type == 0x98:
                glBegin(GL_TRIANGLE_STRIP)
            elif prim.type == 0x90:
                glBegin(GL_TRIANGLES)
            else:
                assert False

            for vertex in prim.vertices:
                if len(vertex) == 0:
                    continue
                if len(vertex) == 2:
                    posindex, normindex = vertex

                x,y,z = self.vertices[posindex]
                if normindex is not None and len(self.normals) > 0:
                    glColor3f(*self.normals[normindex])
                glVertex3f(x * self.vscl, y * self.vscl, z * self.vscl)
            glEnd()

class Transform(object):
    def __init__(self, floats):
        self.floats = floats
        x,y,z,w = floats[3:7]
        self.matrix = [w**2+x**2-y**2-z**2,     2*x*y+2*w*z,            2*x*z-2*w*y,            0.0,
                       2*x*y-2*w*z,             y**2+w**2-x**2-z**2,    2*y*z+2*w*x,            0.0,
                       2*x*z+2*w*y,             2*y*z-2*w*x,            z**2+w**2-x**2-y**2,    0.0,
                       floats[0],               floats[1],              floats[2],              1.0]

    def backup_transform(self):
        glPushMatrix()

    def apply_transform(self):
        #glPushMatrix()
        #glTranslatef(self.floats[0], self.floats[2], -self.floats[1])
        #glTranslatef(self.floats[8], self.floats[10], -self.floats[9])
        cos_alpha = self.floats[3]
        sin_alpha = self.floats[6]
        #glTranslatef(self.floats[0], self.floats[2], self.floats[9])
        #glTranslatef(self.floats[0], self.floats[2], self.floats[10])
        # Column major, i.e. each column comes first
        """glMultMatrixf([1.0, 0.0, 0.0, self.floats[0],
                      0.0, 1.0, 0.0, self.floats[1],
                      0.0, 0.0, 1.0, self.floats[2],
                      0.0, 0.0, 0.0, 1.0])"""

        glMultMatrixf(self.matrix)
        #print(self.floats)
        """for i in (self.floats[3], self.floats[4], self.floats[5], self.floats[6], self.floats[7]):
            print(abs(i))
            assert abs(i) <= 1.0"""



    def reset_transform(self):
        glPopMatrix()


class Box(Model):
    def __init__(self, corner_bottomleft, corner_topright):
        self.corner_bottomleft = corner_bottomleft
        self.corner_topright = corner_topright

    def render(self):
        x1, y1, z1 = self.corner_bottomleft
        x2, y2, z2 = self.corner_topright
        glColor3f(1.0, 0.0, 1.0)
        glBegin(GL_LINE_STRIP)  # Bottom, z1
        glVertex3f(x2, y1, z1)
        glVertex3f(x2, y2, z1)
        glVertex3f(x1, y2, z1)
        glVertex3f(x1, y1, z1)
        glVertex3f(x2, y1, z1)

        glEnd()
        glBegin(GL_LINE_STRIP)  # Front, x1
        glVertex3f(x1, y1, z1)
        glVertex3f(x1, y1, z2)
        glVertex3f(x1, y2, z2)
        glVertex3f(x1, y2, z1)
        glVertex3f(x1, y1, z1)
        glEnd()

        glBegin(GL_LINE_STRIP)  # Side, y1
        glVertex3f(x1, y1, z1)
        glVertex3f(x1, y1, z2)
        glVertex3f(x2, y1, z2)
        glVertex3f(x2, y1, z1)
        glVertex3f(x1, y1, z1)
        glEnd()

        glBegin(GL_LINE_STRIP)  # Back, x2
        glVertex3f(x2, y1, z1)
        glVertex3f(x2, y1, z2)
        glVertex3f(x2, y2, z2)
        glVertex3f(x2, y2, z1)
        glVertex3f(x2, y1, z1)
        glEnd()

        glBegin(GL_LINE_STRIP)  # Side, y2
        glVertex3f(x1, y2, z1)
        glVertex3f(x1, y2, z2)
        glVertex3f(x2, y2, z2)
        glVertex3f(x2, y2, z1)
        glVertex3f(x1, y2, z1)
        glEnd()

        glBegin(GL_LINE_STRIP)  # Top, z2
        glVertex3f(x1, y1, z2)
        glVertex3f(x1, y2, z2)
        glVertex3f(x2, y2, z2)
        glVertex3f(x2, y1, z2)
        glVertex3f(x1, y1, z2)
        glEnd()

    def render_(self):
        x1,y1,z1 = self.corner_bottomleft
        x2,y2,z2 = self.corner_topright
        glColor3f(1.0, 0.0, 1.0)
        glBegin(GL_LINE_STRIP) # Bottom, z1
        glVertex3f(x2, y1, z1)
        glVertex3f(x2, y2, z1)
        glVertex3f(x1, y2, z1)
        glVertex3f(x1, y1, z1)



        glEnd()
        glColor3f(0.1, 0.1875, 0.8125)
        glBegin(GL_LINE_STRIP) # Front, x1
        glVertex3f(x1, y1, z1)
        glVertex3f(x1, y1, z2)
        glVertex3f(x1, y2, z2)
        glVertex3f(x1, y2, z1)
        glEnd()

        glBegin(GL_LINE_STRIP) # Side, y1
        glVertex3f(x1, y1, z1)
        glVertex3f(x1, y1, z2)
        glVertex3f(x2, y1, z2)
        glVertex3f(x2, y1, z1)
        glEnd()
        glColor3f(1.0, 1.0, 0.0)
        glBegin(GL_LINE_STRIP) # Back, x2
        glVertex3f(x2, y1, z1)
        glVertex3f(x2, y1, z2)
        glVertex3f(x2, y2, z2)
        glVertex3f(x2, y2, z1)
        glEnd()
        glColor3f(0.1, 0.1875, 0.8125)
        glBegin(GL_LINE_STRIP) # Side, y2
        glVertex3f(x1, y2, z1)
        glVertex3f(x1, y2, z2)
        glVertex3f(x2, y2, z2)
        glVertex3f(x2, y2, z1)
        glEnd()
        glColor3f(0.1, 0.1875, 0.8125)
        glBegin(GL_LINE_STRIP) # Top, z2
        glVertex3f(x1, y1, z2)
        glVertex3f(x1, y2, z2)
        glVertex3f(x2, y2, z2)
        glVertex3f(x2, y1, z2)
        glEnd()
