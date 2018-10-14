from OpenGL.GL import *
from binascii import hexlify
from struct import unpack
from .vectors import Vector3, Matrix4x4
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

class Material(object):
    def __init__(self):
        self.tex1 = None
        self.tex2 = None
        self.tex3 = None
        self.tex4 = None
        self.data = None

    def from_file(self, f):
        self.tex1 = f.read(0x20) #.strip(b"\x00")
        self.tex2 = f.read(0x20) #.strip(b"\x00")
        self.tex3 = f.read(0x20) #.strip(b"\x00")
        self.tex4 = f.read(0x20) #.strip(b"\x00")
        self.data = f.read(0x24) # rest

        if self.tex1.count(b"\x00") == 32:
            self.tex1 = None
        if self.tex2.count(b"\x00") == 32:
            self.tex2 = None
        if self.tex3.count(b"\x00") == 32:
            self.tex3 = None
        if self.tex4.count(b"\x00") == 32:
            self.tex4 = None

    def textures(self):
        if self.tex1 is not None:
            yield self.tex1
        if self.tex2 is not None:
            yield self.tex2
        if self.tex3 is not None:
            yield self.tex3
        if self.tex4 is not None:
            yield self.tex4

        raise StopIteration()

    def __str__(self):
        return str([x.strip(b"\x00") for x in self.textures()])


class Model(object):
    def __init__(self):
        pass

    def render(self, *args, **kwargs):
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
        self.render_order = []
        for node in self.nodes:
            node.create_displaylists()

            self.render_order.append(node )

    def _skip_section(self, f, secname):
        name = f.read(4)
        assert name == secname
        size = read_uint32_le(f)
        f.read(size)

    def sort_render_order(self, camerax, cameray, cameraz):
        origin = Vector3(camerax, cameray, cameraz)

        def distance(node):
            dist_vec = origin - node.world_center
            distance = dist_vec.norm()
            return distance

        self.render_order.sort(key = lambda x: distance(x), reverse=True)

    def render(self, texturearchive, shader, j=0):
        #for node in self.nodes:
        i = 0
        for node in self.render_order:
            #box.render()
            if node.do_skip():
                continue
            i += 1

            if (j > 0 and j != i):
                continue
            node.render(texturearchive, shader)
            #print("Rendering first:", node.name, node.world_center.x, node.world_center.y, node.world_center.z)
            #break
            #node.transform.reset_transform()


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
        self.materials = []

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
        self.binormals = []
        self.tangents = []
        self.triprimitives = []
        self.meshes = []
        self.uvmaps = [[],[],[],[]]

        self.additionaldata = []
        self.lods = []

        self._displaylists = []

        self.world_center = Vector3(0, 0, 0)

        self._mvmat = None

    def do_skip(self):
        return b"NODRAW" in self.name or b"COLLIDE" in self.name or b"COLLISION" in self.name or self.xbs2count == 0 or b"DUMMY" in self.name

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
        self.unkshort1, self.unkshort2, self.unkshort3, self.padd, self.xbs2count = unpack("HHHHI", f.read(12))
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

        self.world_center.x = (x1 + x2) / 2.0
        self.world_center.y = (y1 + y2) / 2.0
        self.world_center.z = (z1 + z2) / 2.0

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
        assert size % 0xA4 == 0
        assert self.xbs2count*0xA4 == size

        self.materials = []
        for i in range(self.xbs2count):
            material = Material()
            material.from_file(f)
            self.materials.append(material)

        vertexdesc = 0

        self.uvmaps = [[], [], [], []]

        while f.tell() < nodeend:
            secname = read_id(f)
            size = read_uint32_le(f)
            end = f.tell()+size

            if secname == b"SCNT":
                val = read_uint32(f)
                assert size == 4
                self.lods.append(val)

            elif secname in (b"VUV1", b"VUV2", b"VUV3", b"VUV4"):
                uvindex = secname[3] - b"1"[0]

                for i in range(size // 4):
                    scale = 2.0**11
                    u, v = read_int16(f)/(scale), read_int16(f)/(scale)
                    self.uvmaps[uvindex].append((u, v))

            elif secname == b"XBS2":
                #eprint(hex(f.tell()))
                materialindex = read_uint32(f)
                unknown = (read_uint32(f), read_uint32(f))
                gx_data_size = read_uint32(f)
                gx_data_end = f.tell() + gx_data_size
                #print(hex(gx_data_end), hex(gx_data_size))

                mesh = []
                self.meshes.append((materialindex, mesh))

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

                    elif opcode & 0xFA == 0x98:  # Triangle strip
                        attribs = VertexDescriptor()
                        attribs.from_value(vertexdesc)

                        vertex_count = read_uint16(f)
                        prim = Primitive(0x98)
                        #print(bin(vertexdesc))
                        #print([x for x in attribs.active_attributes()])

                        for i in range(vertex_count):
                            primattrib = [None, None,
                                          None,None,None,None,None,None,None,None]

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
                                elif attrib is not None and VTX.Tex0Coord <= attrib <= VTX.Tex7Coord:
                                    coordindex = attrib - VTX.Tex0Coord
                                    val = read_uint8(f)
                                    primattrib[2+coordindex] = val
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

                        #self.triprimitives.append(prim)
                        mesh.append(prim)
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
                #print(self.name, size)
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
                    self.binormals.append((read_float(f), read_float(f), read_float(f)))

                    self.tangents.append((read_float(f), read_float(f), read_float(f)))

            else:
                f.read(size)
            self.sections.append(secname)

        while f.tell() < nodeend:
            secname = read_id(f)
            size = read_uint32_le(f)
            f.read(size)
            self.sections.append(secname)

        assert f.tell() == nodeend

    def initialize_textures(self, texarchive):
        for material in self.materials:
            if material.tex1 is not None:
                texarchive.initialize_texture(material.tex1)

    def render(self, texarchive, shader):#, program):
        #glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S,GL_REPEAT)
        #glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
        #print(len(self.materials), len(self._displaylists))
        #print(self.xbs2count, self.sections)
        #assert len(self.materials) == len(self._displaylists)
        #for material, displist in zip(self.materials, self._displaylists):
        if self._mvmat is None:
            self.transform.backup_transform()
            currnode = self
            j = 0
            while currnode is not None:
                j += 1
                currnode.transform.apply_transform()
                currnode = currnode.parent
                if j > 200:
                    raise RuntimeError("Possibly endless loop detected!")
            self._mvmat = glGetFloatv(GL_MODELVIEW_MATRIX)
            self.transform.reset_transform()

        matloc = glGetUniformLocation(shader, "modelview")
        glUniformMatrix4fv(matloc, 1, False, self._mvmat)

        for i, displist in self._displaylists:
            material = self.materials[i]

            glEnable(GL_TEXTURE_2D)
            if material.tex1 is not None:
                texture = texarchive.get_texture(material.tex1)
                if texture is not None:
                    tex, texid = texture
                    #texname = str(tex.name.strip(b"\x00"), encoding="ascii")
                    #tex.dump_to_file(texname+".png")
                    #print("texture bound!", texid)
                    #print(glGetError())
                    glActiveTexture(GL_TEXTURE0)
                    glBindTexture(GL_TEXTURE_2D, texid)
                    #glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S,GL_REPEAT)
                    #glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
                else:
                    print("oops case 2 disable")
                    glDisable(GL_TEXTURE_2D)
            else:
                print("oops case 1 disable")
                glDisable(GL_TEXTURE_2D)

            if material.tex2 is not None:
                texture = texarchive.get_texture(material.tex2)
                if texture is not None:
                    tex, texid = texture
                    glActiveTexture(GL_TEXTURE1)
                    glBindTexture(GL_TEXTURE_2D, texid)

            glCallList(displist)

    #def setup_world_center(self):
    def create_displaylists(self):
        if len(self._displaylists) > 0:
            for matindex, i in self._displaylists:
                glDeleteLists(i, 1)
            self._displaylists = []

        #for material, mesh in zip(self.materials, self.meshes):
        for i, mesh in self.meshes:
            material = self.materials[i]

            displist = glGenLists(1)
            glNewList(displist, GL_COMPILE)
            self.transform.backup_transform()
            box = self.bbox
            currnode = self
            j = 0
            while currnode is not None:
                j += 1
                currnode.transform.apply_transform()
                currnode = currnode.parent
                if j > 200:
                    raise RuntimeError("Possibly endless loop detected!")


            #glEnable(GL_TEXTURE_2D)
            #print("node", self.name, "textures:", str(material))
            #for tex in material.textures():

            glColor3f(1.0, 1.0, 1.0)
            """
            glBegin(GL_TRIANGLE_FAN)
            #glColor3f(1.0, 0.0, 1.0)
            glVertexAttrib2f(2, 0, 0)
            glVertex3f(0, 0, 0+i*10)
            glVertexAttrib2f(2, 0, 1)
            glVertex3f(0, 10, 0+i*10)
            #glColor3f(1.0, 0.0, 0.0)
            glVertexAttrib2f(2, 1, 1)
            glVertex3f(10, 10, 0+i*10)
            glVertexAttrib2f(2, 1, 0)
            glVertex3f(10, 0, 0+i*10)
            glEnd()"""

            for prim in mesh:
                if prim.type == 0x98:
                    glBegin(GL_TRIANGLE_STRIP)
                elif prim.type == 0x90:
                    glBegin(GL_TRIANGLES)
                else:
                    assert False

                for vertex in prim.vertices:
                    if len(vertex) == 0:
                        continue
                    posindex, normindex = vertex[0], vertex[1]
                    tex0 = vertex[2]
                    tex1 = vertex[3]
                    x,y,z = self.vertices[posindex]

                    if not tex1 is None:
                        #print(tex1, self.uvmaps[0])
                        if not tex0 is None:
                            texcoordindex = tex0 << 8 | tex1
                        else:
                            texcoordindex = tex1
                        u,v = self.uvmaps[0][texcoordindex]

                        glVertexAttrib2f(2, u, v)
                        glVertexAttrib2f(4, u, v)

                    if normindex is not None:
                        glVertexAttrib3f(3, *self.normals[normindex])
                        if len(self.binormals) > 0:
                            glVertexAttrib3f(5, *self.binormals[normindex])
                            glVertexAttrib3f(6, *self.tangents[normindex])
                    glVertex3f(x * self.vscl, y * self.vscl, z * self.vscl)

                glEnd()
            self.transform.reset_transform()
            glEndList()
            self._displaylists.append((i, displist))


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
