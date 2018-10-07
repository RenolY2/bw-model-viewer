import traceback
from math import sqrt, atan2, pi, cos, sin, radians, degrees, tan
from timeit import default_timer
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import Qt
from OpenGL.GL import *
from OpenGL.GLU import *


from lib.vectors import Vector3, Plane, Triangle, Line
from custom_widgets import catch_exception
from lib.read_binary import *
from lib.model_rendering import Box, Transform, Node, BWModel
from lib.shader import create_shader


def catch_exception_with_dialog(func):
    def handle(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            traceback.print_exc()
            open_error_dialog(str(e), None)
    return handle


def open_error_dialog(errormsg, self):
    errorbox = QtWidgets.QMessageBox()
    errorbox.critical(self, "Error", errormsg)
    errorbox.setFixedSize(500, 200)


def cross_norm(vec1, vec2):

    return (vec1[1]*vec2[2]-vec1[2]*vec2[1],
            vec1[2] * vec2[0] - vec1[0] * vec2[2],
            vec1[0] * vec2[1] - vec1[1] * vec2[0])


def length_vector(vec):
    return sqrt(vec[0]**2 + vec[1]**2 + vec[2]**2)


def calc_angle(vec1, vec2):
    return (vec1[0]*vec2[0]+vec1[1]*vec2[1]+vec1[2]*vec2[2])/(length_vector(vec1)*length_vector(vec2))


def make_gradient(start, end, step=1, max=None):
    r1, g1, b1 = start
    r2, g2, b2 = end

    diff_r, diff_g, diff_b = r2-r1, g2-g1, b2-b1
    norm = sqrt(diff_r**2 + diff_g**2 + diff_b**2)
    norm_r, norm_g, norm_b = diff_r/norm, diff_g/norm, diff_b/norm

    gradient = []
    gradient.append((int(r1), int(g1), int(b1)))

    if max is not None:
        step = int((r2-r1)/norm_r)//max

    #curr_r, curr_g, curr_b = r1, g1, b1
    for i in range(0, int((r2-r1)/norm_r), step):
        curr_r = r1+i*norm_r
        curr_g = g1+i*norm_g
        curr_b = b1+i*norm_b
        gradient.append((int(curr_r), int(curr_g), int(curr_b)))
    gradient.append((int(r2), int(g2), int(b2)))
    return gradient

COLORS = []
for coltrans in [
    #((106, 199, 242), (190, 226, 241), 1), # Ocean level
    #((190, 226, 241), (120, 147, 78), 1), # Transition Ocean->Ground
    ((20, 20, 20), (230,230,230), 1),
    ((120, 147, 78), (147,182,95), 3), # Ground level
    ((147,182,95), (249, 239, 160), 3), # Higher areas, going into mountains, green to yellow
    ((249, 239, 160), (214, 127, 70), 3), # Even higher, yellow to brown
    ((214, 127, 70), (150, 93, 60), 4), # brown to dark brown #(119, 68, 39)
    ((150, 93, 60), (130,130, 130), 4), # dark brown to grey, very high
    (((130,130, 130), (250, 250, 250), 4))]: # grey to white, very very high

    start, end, repeat = coltrans
    for i, color in enumerate(make_gradient(start, end, step=8)):
        #if i % 2 == 0: continue
        for j in range(repeat):
            COLORS.append(color)

DO_GRAYSCALE = False


class RenderWindow(QtWidgets.QOpenGLWidget):
    camera_moved = QtCore.pyqtSignal(float, float, float)
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.verts = []
        self.faces = []
        self.texarchive = None

        self.main_model = None

        self.timer = QtCore.QTimer()
        self.timer.setInterval(2)
        self.timer.timeout.connect(self.render_loop)
        self.timer.start()
        self._lastrendertime = 0
        self._lasttime = 0

        self.shift_is_pressed = False

        self.MOVE_FORWARD = 0
        self.MOVE_BACKWARD = 0
        self.MOVE_LEFT = 0
        self.MOVE_RIGHT = 0
        self.MOVE_UP = 0
        self.MOVE_DOWN = 0

        self.offset_x = -25
        self.offset_y = -25
        self.camera_height = 25

        self.camera_horiz = pi/4.0
        self.camera_vertical = -pi/8.0

        self._frame_invalid = False

        self._wasdscrolling_speed = 12.5
        self._wasdscrolling_speedupfactor = 5

        self.last_move = None
        self.camera_direction = None

        self.lines = []

        self.plane = Plane(Vector3(0, 0, 0),
                           Vector3(1, 0, 0),
                           Vector3(0, 1, 0))

        self.selector = None

        self.setMouseTracking(True)

        self.collision = []

        self.models = []

        self.current_render_index = 0

    @catch_exception
    def initializeGL(self):
        self.shader = create_shader()

        print(self.shader)
        #self.shadershader.setUniform("firstSampler", 0);

    def reset(self):
        self.verts = []
        self.faces = []
        self.collision = []
        self.models = []

    @catch_exception
    def render_loop(self):
        now = default_timer()

        diff = now-self._lastrendertime
        timedelta = now-self._lasttime
        self.handle_arrowkey_scroll(timedelta)
        if diff > 1 / 60.0:
            if self._frame_invalid:
                self.update()
                self._lastrendertime = now
                self._frame_invalid = False
                #self.camera_moved.emit(self.offset_x, self.offset_y, self.camera_height)
        self._lasttime = now

    def do_redraw(self):
        self._frame_invalid = True

    def handle_arrowkey_scroll(self, timedelta):
        diff_x = diff_y = diff_height = 0
        #print(self.MOVE_UP, self.MOVE_DOWN, self.MOVE_LEFT, self.MOVE_RIGHT)
        speedup = 1

        forward_vec = Vector3(cos(self.camera_horiz), sin(self.camera_horiz), 0)
        sideways_vec = Vector3(sin(self.camera_horiz), -cos(self.camera_horiz), 0)

        if self.shift_is_pressed:
            speedup = self._wasdscrolling_speedupfactor

        if self.MOVE_FORWARD == 1 and self.MOVE_BACKWARD == 1:
            forward_move = forward_vec*0
        elif self.MOVE_FORWARD == 1:
            forward_move = forward_vec*(1*speedup*self._wasdscrolling_speed*timedelta)
        elif self.MOVE_BACKWARD == 1:
            forward_move = forward_vec*(-1*speedup*self._wasdscrolling_speed*timedelta)
        else:
            forward_move = forward_vec*0

        if self.MOVE_LEFT == 1 and self.MOVE_RIGHT == 1:
            sideways_move = sideways_vec*0
        elif self.MOVE_LEFT == 1:
            sideways_move = sideways_vec*(-1*speedup*self._wasdscrolling_speed*timedelta)
        elif self.MOVE_RIGHT == 1:
            sideways_move = sideways_vec*(1*speedup*self._wasdscrolling_speed*timedelta)
        else:
            sideways_move = sideways_vec*0

        if self.MOVE_UP == 1 and self.MOVE_DOWN == 1:
            diff_height = 0
        elif self.MOVE_UP == 1:
            diff_height = 1*speedup*self._wasdscrolling_speed*timedelta
        elif self.MOVE_DOWN == 1:
            diff_height = -1 * speedup * self._wasdscrolling_speed * timedelta

        if not forward_move.is_zero() or not sideways_move.is_zero() or diff_height != 0:
            #if self.zoom_factor > 1.0:
            #    self.offset_x += diff_x * (1.0 + (self.zoom_factor - 1.0) / 2.0)
            #    self.offset_z += diff_y * (1.0 + (self.zoom_factor - 1.0) / 2.0)
            #else:
            self.offset_x += (forward_move.x + sideways_move.x)
            self.offset_y += (forward_move.y + sideways_move.y)
            self.camera_height += diff_height
            # self.update()


            self.do_redraw()

    def add_waterbox(self, waterbox):
        self.models.append(waterbox)


    def set_model(self, verts, faces, normals=None):
        print("did this once")
        self.verts = verts
        self.faces = faces
        self.normals = normals
        self.collision = []

        biggest, smallest = None, None
        for x,y,z in verts:
            if biggest is None:
                biggest = smallest = y
            if y > biggest:
                biggest = y
            if y < smallest:
                smallest = y
        scaleheight = biggest-smallest
        if scaleheight == 0:
            scaleheight = 1

        print(len(COLORS))

        self.main_model = glGenLists(1)

        glNewList(self.main_model, GL_COMPILE)
        glBegin(GL_TRIANGLES)

        i = -1
        light_vec = (0, 1, -1)
        for v1, v2, v3 in faces:
            i += 1
            v1x, v1y, v1z = verts[v1[0]-1]
            v2x, v2y, v2z = verts[v2[0]-1]
            v3x, v3y, v3z = verts[v3[0]-1]

            tri = Triangle(
                Vector3(v1x, -v1z, v1y),
                Vector3(v2x, -v2z, v2y),
                Vector3(v3x, -v3z, v3y))

            self.collision.append(tri)

            #grayscale = ((v1y+v2y+v3y)/3.0)/scaleheight
            """average_y = max(v1y, v2y,v3y) - smallest#(v1y+v2y+v3y)/3.0 - smallest
            index = int((average_y/scaleheight)*len(COLORS))
            if index < 0:
                index = 0
            if index >= len(COLORS):
                index = len(COLORS)-1
            r, g, b = COLORS[index]
            glColor3f(r/256.0,g/256.0,b/256.0)"""

            if DO_GRAYSCALE:
                average_y = (v1y+v2y+v3y)/3.0 - smallest
                grayscale = average_y/scaleheight

                glColor3f(grayscale, grayscale, grayscale)
                glVertex3f(v1x, -v1z, v1y)
                glVertex3f(v2x, -v2z, v2y)
                glVertex3f(v3x, -v3z, v3y)

            else:
                norm = cross_norm((v1x-v2x, -v1z+v2z, v1y-v2y),
                                  (v1x-v3x, -v1z+v3z, v1y-v3y))
                #angle = atan2(norm[0], norm[1])
                #verticalangle = norm[2]
                angle = calc_angle(light_vec, norm)
                print(angle)
                light = max(abs(angle), 0.3)
                #print(light)
                average_y = v1y - smallest
                index = int((average_y/scaleheight)*len(COLORS))
                if index < 0:
                    index = 0
                if index >= len(COLORS):
                    index = len(COLORS)-1
                r, g, b = (i * light for i in COLORS[index])
                #glColor3f(r/256.0,g/256.0,b/256.0)
                glColor4f(r / 256.0, g / 256.0, b / 256.0, 1.0)
                glVertex3f(v1x, -v1z, v1y)

                average_y = v3y - smallest
                index = int((average_y/scaleheight)*len(COLORS))
                if index < 0:
                    index = 0
                if index >= len(COLORS):
                    index = len(COLORS)-1
                r, g, b = (i * light for i in COLORS[index])
                #glColor3f(r/256.0,g/256.0,b/256.0)
                glColor4f(r / 256.0, g / 256.0, b / 256.0, 1.0)

                glVertex3f(v3x, -v3z, v3y)

                average_y = v3y - smallest
                index = int((average_y/scaleheight)*len(COLORS))
                if index < 0:
                    index = 0
                if index >= len(COLORS):
                    index = len(COLORS)-1
                r, g, b = (i * light for i in COLORS[index])
                #glColor3f(r/256.0,g/256.0,b/256.0)
                glColor4f(r / 256.0, g / 256.0, b / 256.0, 1.0)
                glVertex3f(v2x, -v2z, v2y)

        glEnd()

        glEndList()

    def create_drawlist(self, bwmodel):
        data = bwmodel.entries[0]
        data.fileobj.seek(0)
        f = data.fileobj


        model = BWModel()


        model.from_file(f)
        #for node in model.nodes:
        #    node.initialize_textures(self.texarchive)
        self.main_model = model
        return
        if self.main_model is not None:
            glDeleteLists(self.main_model, 1)
        self.main_model = glGenLists(1)
        glNewList(self.main_model, GL_COMPILE)
        i = 0
        print("===")
        print([hex(i) for i in model.additionaldata])
        try:
            i = 0
            max_renderable_index = 0
            for node in model.nodes:
                if b"NODRAW" in node.name or b"COLLIDE" in node.name or b"COLLISION" in node.name or node.xbs2count == 0:
                    continue
                max_renderable_index += 1

            for node in model.nodes:
                if b"NODRAW" in node.name or b"COLLIDE" in node.name or b"COLLISION" in node.name or node.xbs2count == 0:
                    continue

                i += 1
                if self.current_render_index == 0:
                    pass
                elif self.current_render_index > 0:
                    if self.current_render_index > max_renderable_index:
                        self.current_render_index = 0

                    elif i != self.current_render_index:
                        continue
                else:
                    continue

                parentname = None
                if node.parent is not None:
                    parentname = node.parent.name

                print(hex(i), hex(node.unkshort1), hex(node.unkshort2), hex(node.unkshort3), node.name, [hex(i) for i in node.additionaldata], node.sections)


                #for transform, box in boundingboxes:
                node.transform.backup_transform()
                box = node.bbox
                currnode = node
                j = 0
                while currnode is not None:
                    j += 1
                    currnode.transform.apply_transform()
                    currnode = currnode.parent
                    if j > 200:
                        raise RuntimeError("Possibly endless loop detected!")

                box.render()
                node.render(self.texarchive)

                node.transform.reset_transform()
                i += 1
        except Exception as error:
            self.main_model = None
            print(error)
            raise error

        glEndList()

        self.do_redraw()

    def re_render(self, model):
        if self.main_model is not None:
            glDeleteLists(self.main_model, 1)
        self.main_model = glGenLists(1)
        glNewList(self.main_model, GL_COMPILE)
        try:
            i = 0
            max_renderable_index = 0
            for node in model.nodes:
                if b"NODRAW" in node.name or b"COLLIDE" in node.name or b"COLLISION" in node.name or node.xbs2count == 0:
                    continue
                max_renderable_index += 1

            for node in model.nodes:


                if b"NODRAW" in node.name or b"COLLIDE" in node.name or b"COLLISION" in node.name or node.xbs2count == 0:
                    continue

                i += 1
                if self.current_render_index == 0:
                    pass
                elif self.current_render_index > 0:
                    if self.current_render_index > max_renderable_index:
                        self.current_render_index = 0

                    elif i != self.current_render_index:
                        continue
                else:
                    continue

                parentname = None
                if node.parent is not None:
                    parentname = node.parent.name

                print(hex(i), hex(node.unkshort1), hex(node.unkshort2), hex(node.unkshort3), node.name, [hex(i) for i in node.additionaldata], node.sections)

                #for transform, box in boundingboxes:
                node.transform.backup_transform()
                box = node.bbox
                currnode = node
                j = 0
                while currnode is not None:
                    j += 1
                    currnode.transform.apply_transform()
                    currnode = currnode.parent
                    if j > 200:
                        raise RuntimeError("Possibly endless loop detected!")

                box.render()
                node.render(self.texarchive)

                node.transform.reset_transform()
                i += 1
        except Exception as error:
            self.main_model = None
            print(error)
            raise error

        glEndList()

        self.do_redraw()

    @catch_exception
    def paintGL(self):
        start = default_timer()
        #Paint the scene.
        # clear the buffer
        #gl.glClear(gl.GL_COLOR_BUFFER_BIT)
        glClearColor(1.0, 1.0, 1.0, 0.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT) # clear the screen
        glDisable(GL_CULL_FACE)
        #glEnable(GL_BLEND)
        #glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
        # set yellow color for subsequent drawing rendering calls


        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(75, self.width/self.height, 1.0, 12800.0)

        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        look_direction = Vector3(cos(self.camera_horiz), sin(self.camera_horiz), sin(self.camera_vertical))
        #look_direction.unify()
        fac = 1.01-abs(look_direction.z)
        #print(fac, look_direction.z, look_direction)

        gluLookAt(self.offset_x, self.offset_y, self.camera_height,
                  self.offset_x+look_direction.x*fac, self.offset_y+look_direction.y*fac, self.camera_height+look_direction.z,
                  0, 0, 1)

        self.camera_direction = Vector3(look_direction.x*fac, look_direction.y*fac, look_direction.z)

        glBegin(GL_LINES)
        glColor3f(0.0, 1.0, 0.0)
        glVertex3f(0, 0, -5000)
        glVertex3f(0, 0, 5000)


        glColor3f(0.0, 0.0, 1.0)
        glVertex3f(0, -5000, 0)
        glVertex3f(0, 5000, 0)


        glColor3f(1.0, 0.0, 0.0)
        glVertex3f(-5000, 0, 0)
        glVertex3f(5000, 0, 0 )

        glColor3f(0.0, 1.0, 1.0)
        i = 0
        for line in self.lines:
            if i % 2 == 0:
                glColor3f(0.0, 1.0, 1.0)
            else:
                glColor3f(1.0, 1.0, 0.0)
            i += 1
            glVertex3f(*line)
        if self.selector is not None:
            glColor3f(1.0, 0.0, 1.0)
            glVertex3f(*self.selector[0])
            glVertex3f(*self.selector[1])
        glEnd()

        glRotatef(90, 1, 0, 0)
        for model in self.models:
            model.render()

        if self.main_model is None:
            return

        """for node in self.model.nodes:
            for material in node.materials:
                if material.tex1 is not None:
                    self.texarchive.load_texture(material.tex1)"""
        #print("drawing", self.main_model, type(self.main_model))
        #glCallList(self.main_model)
        #self.main_model.sort_render_order(self.camera_direction.x, self.camera_direction.y, self.camera_direction.z)
        #self.main_model.sort_render_order(self.offset_x, self.camera_height, -self.offset_y)
        glUseProgram(self.shader)
        texvar = glGetUniformLocation(self.shader, "tex")
        #print(texvar, self.shader, type(self.shader))
        glUniform1i(texvar, 0)
        self.main_model.render(self.texarchive)
        glUseProgram(0)
        glFinish()

        #print("drawn in", default_timer() - start, "s")

    def resizeGL(self, width, height):
        # Called upon window resizing: reinitialize the viewport.
        # update the window size
        self.width, self.height = width, height
        # paint within the whole window
        glEnable(GL_DEPTH_TEST)
        glViewport(0, 0, self.width, self.width)
        #glMatrixMode(GL_PROJECTION)
        #glLoadIdentity()
        #glOrtho(-6000.0, 6000.0, -6000.0, 6000.0, -3000.0, 2000.0)

        #glMatrixMode(GL_MODELVIEW)
        #glLoadIdentity()

    @catch_exception
    def mouseMoveEvent(self, event):
        if self.last_move is not None:
            curr_x, curr_y = event.x(), event.y()
            last_x, last_y = self.last_move

            diff_x = curr_x - last_x
            diff_y = curr_y - last_y

            self.last_move = (curr_x, curr_y)

            self.camera_horiz = (self.camera_horiz - diff_x * (pi/500)) % (2*pi)
            self.camera_vertical = (self.camera_vertical - diff_y * (pi / 600))
            if self.camera_vertical > pi/2.0: self.camera_vertical = pi/2.0
            elif self.camera_vertical < -pi/2.0: self.camera_vertical = -pi/2.0

            #print(self.camera_vertical, "hello")
            self.do_redraw()

        if self.camera_direction is not None:
            self.camera_direction.normalize()

            view = self.camera_direction.copy()

            h = view.cross(Vector3(0, 0, 1))
            v = h.cross(view)

            h.normalize()
            v.normalize()

            rad = 75 * pi / 180.0
            vLength = tan(rad / 2) * 1.0
            hLength = vLength * (self.width / self.height)

            v *= vLength
            h *= hLength

            mirror_y = self.height - event.y()

            x = event.x() - self.width / 2
            y = mirror_y - self.height / 2

            x /= (self.width / 2)
            y /= (self.height / 2)
            camerapos = Vector3(self.offset_x, self.offset_y, self.camera_height)
            #print(h * x)
            #print(v * y)
            #print(view)
            pos = camerapos + view * 1.0 + h * x + v * y
            dir = pos - camerapos

            # self.lines.append((pos.x+0.5, pos.y, pos.z))
            # self.lines.append((pos.x + dir.x*400, pos.y + dir.y*400, pos.z + dir.z*400))

            # Plane Intersection

            if not self.plane.is_parallel(dir):
                d = ((self.plane.origin - pos).dot(self.plane.normal)) / self.plane.normal.dot(dir)
                if d >= 0:
                    point = pos + (dir * d)
                    self.selector = ((point.x, point.y, point.z - 2000), (point.x, point.y, point.z + 2000))
                    self.camera_moved.emit(point.x, point.y, point.z)
                else:
                    self.selector = None
            else:
                self.selector = None

            self.do_redraw()

    @catch_exception
    def mousePressEvent(self, event):
        if event.buttons() & Qt.RightButton:
            self.last_move = (event.x(), event.y())

        elif event.buttons() & Qt.MiddleButton:
            print("hi", self.current_render_index)
            self.current_render_index += 1
            self.re_render(self.model)

        elif event.buttons() & Qt.LeftButton:
            if self.camera_direction is not None:
                self.camera_direction.normalize()

                view = self.camera_direction.copy()

                h = view.cross(Vector3(0,0,1))
                v = h.cross(view)

                h.normalize()
                v.normalize()

                rad = 75 * pi/180.0
                vLength = tan(rad / 2) * 1.0
                hLength = vLength * (self.width / self.height)

                v *= vLength
                h *= hLength

                mirror_y = self.height - event.y()

                x = event.x() - self.width / 2
                y = mirror_y - self.height / 2

                x /= (self.width/2)
                y /= (self.height/2)
                camerapos = Vector3(self.offset_x, self.offset_y, self.camera_height)

                pos = camerapos + view * 1.0 + h * x + v * y
                dir = pos - camerapos


                #self.lines.append((pos.x+0.5, pos.y, pos.z))
                #self.lines.append((pos.x + dir.x*400, pos.y + dir.y*400, pos.z + dir.z*400))

                # Plane Intersection
                line = Line(camerapos, dir)

                nearest_coll = None
                nearest_dist = None

                for tri in self.collision:
                    collision = line.collide(tri)

                    if collision is not False:
                        point, distance = collision
                        if nearest_coll is None or distance < nearest_dist:
                            nearest_coll = point
                            nearest_dist = distance


                if nearest_coll is not None:
                    collision = nearest_coll
                    self.lines.append((collision.x+dir.x*-100, collision.y+dir.y*-100, collision.z+dir.z*-100))
                    self.lines.append((collision.x+dir.x*+100, collision.y+dir.y*+100, collision.z+dir.z*+100))
                """if not self.plane.is_parallel(dir):
                    d = ((self.plane.origin - pos).dot(self.plane.normal)) / self.plane.normal.dot(dir)
                    if d >= 0:
                        point = pos + (dir*d)
                
                        self.lines.append((point.x, point.y, point.z-2000))
                        self.lines.append((point.x, point.y, point.z+2000))"""


                self.do_redraw()



    @catch_exception
    def mouseReleaseEvent(self, event):
        if not event.buttons() & Qt.RightButton:
            self.last_move = None