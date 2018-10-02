from math import sqrt


class Vector3(object):
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

    def copy(self):
        return Vector3(self.x, self.y, self.z)

    def norm(self):
        return sqrt(self.x**2 + self.y**2 + self.z**2)

    def normalize(self):
        norm = self.norm()
        self.x /= norm
        self.y /= norm
        self.z /= norm

    def unit(self):
        return self/self.norm()

    def cross(self, other_vec):
        return Vector3(self.y*other_vec.z - self.z*other_vec.y,
                       self.z*other_vec.x - self.x*other_vec.z,
                       self.x*other_vec.y - self.y*other_vec.x)

    def dot(self, other_vec):
        return self.x*other_vec.x + self.y*other_vec.y + self.z*other_vec.z

    def __truediv__(self, other):
        return Vector3(self.x/other, self.y/other, self.z/other)

    def __add__(self, other_vec):
        return Vector3(self.x+other_vec.x, self.y+other_vec.y, self.z+other_vec.z)

    def __mul__(self, other):
        return Vector3(self.x*other, self.y*other, self.z*other)

    def __sub__(self, other_vec):
        return Vector3(self.x-other_vec.x, self.y-other_vec.y, self.z-other_vec.z)

    def cos_angle(self, other_vec):
        return self.dot(other_vec)/(self.norm()*other_vec.norm())

    def __iadd__(self, other_vec):
        self.x += other_vec.x
        self.y += other_vec.y
        self.z += other_vec.z
        return self

    def __isub__(self, other_vec):
        self.x -= other_vec.x
        self.y -= other_vec.y
        self.z -= other_vec.z
        return self

    def __imul__(self, other):
        self.x *= other
        self.y *= other
        self.z *= other
        return self

    def __itruediv__(self, other):
        self.x /= other
        self.y /= other
        self.z /= other
        return self

    def is_zero(self):
        return self.x == self.y == self.z == 0

    def __eq__(self, other_vec):
        return self.x == other_vec.x and self.y == other_vec.y and self.z == other_vec.z

    def __str__(self):
        return str((self.x, self.y, self.z))


class Plane(object):
    def __init__(self, origin, vec1, vec2): # a point and two vectors defining the plane
        self.origin = origin
        self.vec1 = vec1
        self.vec2 = vec2
        self.normal = vec1.cross(vec2)

    def point_is_on_plane(self, vec):
        return (vec-self.origin).dot(self.normal) == 0

    def is_parallel(self, vec):
        return self.normal.dot(vec) == 0


class Triangle(object):
    def __init__(self, p1, p2, p3):
        self.origin = p1
        self.p2 = p2
        self.p3 = p3
        self.p1_to_p2 = p2 - p1
        self.p1_to_p3 = p3 - p1

        self.normal = self.p1_to_p2.cross(self.p1_to_p3)


        if not self.normal.is_zero():
            self.normal.normalize()

    def is_parallel(self, vec):
        return self.normal.dot(vec) == 0


class Line(object):
    def __init__(self, origin, direction):
        self.origin = origin
        self.direction = direction
        self.direction.normalize()

    def collide(self, tri: Triangle):
        hit = False

        edge1 = tri.p1_to_p2
        edge2 = tri.p1_to_p3

        normal = tri.normal 
        if normal.is_zero():
            return False

        #d = -normal.dot(self.origin)

        if tri.normal.dot(self.direction) == 0:
            return False

        d = ((tri.origin - self.origin).dot(tri.normal)) / tri.normal.dot(self.direction)

        #if d == 0:
        #    return False

        #t = (normal.dot(self.origin) + d) / normal.dot(self.direction)

        if d < 0:
            return False

        intersection_point = self.origin + self.direction * d

        #return intersection_point
        C0 = intersection_point - tri.origin

        if tri.normal.dot(tri.p1_to_p2.cross(C0)) > 0:
            p2_to_p3 = tri.p3 - tri.p2
            C1 = intersection_point - tri.p2

            if tri.normal.dot(p2_to_p3.cross(C1)) > 0:
                p3_to_p1 = tri.origin - tri.p3
                C2 = intersection_point - tri.p3
                if tri.normal.dot(p3_to_p1.cross(C2)) > 0:
                    return intersection_point, d
                else:
                    return False
            else:
                return False
        else:
            return False

