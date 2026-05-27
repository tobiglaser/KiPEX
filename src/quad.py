from __future__ import annotations
from dataclasses import dataclass, field
from shapely.geometry import Polygon, box, Point
from enum import Enum, IntFlag
from point3d import Point3D

class Quadrant(Enum):
    NE = 1
    NW = 2
    SW = 3
    SE = 4

class Direction(Enum):
    N = 0
    S = 1
    E = 2
    W = 3

class Relation(IntFlag):
    outside = 1
    inside = 2
    intersecting = 4

@dataclass
class Side():
    start: Point3D
    end: Point3D
    width: int
    def middle(self) -> Point3D:
        x = self.start.x + (self.end.x - self.start.x) // 2
        y = self.start.y + (self.end.y - self.start.y) // 2
        z = self.start.z + (self.end.z - self.start.z) // 2
        return Point3D(x, y, z)


@dataclass
class Quad():
    x_min: int
    y_min: int
    x_max: int
    y_max: int
    polygon: Polygon
    parent: Quad | None
    depth: int
    children: dict[Quadrant, Quad] = field(default_factory=dict, init=False)
    neighbours: dict[Direction, Quad] = field(default_factory=dict, init=False)

    def length_x(self) -> int:
        return self.x_max - self.x_min
    
    def length_y(self) -> int:
        return self.y_max - self.y_min

    def relation(self, polygon: Polygon | None = None) -> Relation:
        if not polygon:
            polygon = self.polygon
        b = box(self.x_min, self.y_min, self.x_max, self.y_max)
        if b.within(polygon):
            return Relation.inside
        elif b.intersects(polygon):
            return Relation.intersecting
        else:
            return Relation.outside


    def split(self) -> None:
        x_mid = self.x_min + self.length_x() // 2
        y_mid = self.y_min + self.length_y() // 2
        sw = Quad(self.x_min, self.y_min, x_mid, y_mid, self.polygon, self, self.depth + 1)
        nw = Quad(self.x_min, y_mid, x_mid, self.y_max, self.polygon, self, self.depth + 1)
        se = Quad(x_mid, self.y_min, self.x_max, y_mid, self.polygon, self, self.depth + 1)
        ne = Quad(x_mid, y_mid, self.x_max, self.y_max, self.polygon, self, self.depth + 1)
        self.children[Quadrant.SW] = sw
        self.children[Quadrant.NW] = nw
        self.children[Quadrant.SE] = se
        self.children[Quadrant.NE] = ne

    def set_neighbours(self) -> None:
        if self.parent is None:
            for child in self.children.values():
                child.set_neighbours()
            return
        siblings = self.parent.children
        if self is siblings[Quadrant.SW]:
            self.neighbours[Direction.N] = siblings[Quadrant.NW]
            self.neighbours[Direction.E] = siblings[Quadrant.SE]
            s_parent = self.parent.neighbours.get(Direction.S)
            if s_parent:
                self.neighbours[Direction.S] = s_parent.children.get(Quadrant.NW, s_parent)
            w_parent = self.parent.neighbours.get(Direction.W)
            if w_parent:
                self.neighbours[Direction.W] = w_parent.children.get(Quadrant.SE, w_parent)
                
        if self is siblings[Quadrant.NW]:
            self.neighbours[Direction.S] = siblings[Quadrant.SW]
            self.neighbours[Direction.E] = siblings[Quadrant.NE]
            n_parent = self.parent.neighbours.get(Direction.N)
            if n_parent:
                self.neighbours[Direction.N] = n_parent.children.get(Quadrant.SW, n_parent)
            w_parent = self.parent.neighbours.get(Direction.W)
            if w_parent:
                self.neighbours[Direction.W] = w_parent.children.get(Quadrant.NE, w_parent)
        
        if self is siblings[Quadrant.SE]:
            self.neighbours[Direction.N] = siblings[Quadrant.NE]
            self.neighbours[Direction.W] = siblings[Quadrant.SW]
            s_parent = self.parent.neighbours.get(Direction.S)
            if s_parent:
                self.neighbours[Direction.S] = s_parent.children.get(Quadrant.NE, s_parent)
            e_parent = self.parent.neighbours.get(Direction.E)
            if e_parent:
                self.neighbours[Direction.E] = e_parent.children.get(Quadrant.SW, e_parent)
                
        if self is siblings[Quadrant.NE]:
            self.neighbours[Direction.S] = siblings[Quadrant.SE]
            self.neighbours[Direction.W] = siblings[Quadrant.NW]
            n_parent = self.parent.neighbours.get(Direction.N)
            if n_parent:
                self.neighbours[Direction.N] = n_parent.children.get(Quadrant.SE, n_parent)
            e_parent = self.parent.neighbours.get(Direction.E)
            if e_parent:
                self.neighbours[Direction.E] = e_parent.children.get(Quadrant.NW, e_parent)
        
        for dir, quad in self.neighbours.items():
            if quad.relation(self.polygon) == Relation.outside:
                self.neighbours.pop(dir)
        
        for child in self.children.values():
            child.set_neighbours()

    def get_leaves(self, relation: Relation) -> list[Quad]:
        if not self.children: # is leaf
            if self.relation() & relation:
                return [self]
            else:
                return []
        else:
            leaves: list[Quad] = []
            for child in self.children.values():
                leaves = leaves + child.get_leaves(relation)
            return leaves

    def to_points(self, z: int) -> list[Point3D]:
        corners = [
            Point3D(self.x_min, self.y_min, z),
            Point3D(self.x_min, self.y_max, z),
            Point3D(self.x_max, self.y_max, z),
            Point3D(self.x_max, self.x_min, z)]
        return corners
    
    def to_inside_points(self, z: int) -> list[Point3D]:
        corners = self.to_points(z)
        if self.relation() == Relation.inside:
            return corners
        else:
            list = []
            for point in corners:
                if self.polygon.contains(Point(point.x, point.y)):
                    list.append(point)
            return list
    
    # Wahrscheinlich kann die eigene Verarbeitung der Nodes komplett ausgespart werden,
    def to_inside_sides(self, z: int) -> list[Side]:
        sides: list[Side] = []
        # west
        width = self.length_x()
        w_nbr = self.neighbours.get(Direction.W)
        if w_nbr:
            if w_nbr.children: # is not leaf
                width = -1
                pass
            else:
                width += w_nbr.length_y()
                width = width // 2
        start = Point3D(self.x_min, self.y_min, z)
        end   = Point3D(self.x_min, self.y_max, z)
        if start.inside(self.polygon) and end.inside(self.polygon):
            sides.append(Side(start, end, width))
        # north
        width = self.length_y()
        n_nbr = self.neighbours.get(Direction.N)
        if n_nbr:
            if n_nbr.children: # is not leaf
                width = -1
                pass
            else:
                width += n_nbr.length_y()
                width = width // 2
        start = Point3D(self.x_min, self.y_max, z)
        end   = Point3D(self.x_max, self.y_max, z)
        if start.inside(self.polygon) and end.inside(self.polygon):
            sides.append(Side(start, end, width))
        # east
        width = self.length_x()
        e_nbr = self.neighbours.get(Direction.E)
        if e_nbr:
            if e_nbr.children: # is not leaf
                width = -1
                pass
            else:
                width += e_nbr.length_y()
                width = width // 2
        start = Point3D(self.x_max, self.y_max, z)
        end   = Point3D(self.x_max, self.y_min, z)
        if start.inside(self.polygon) and end.inside(self.polygon):
            sides.append(Side(start, end, width))
        # south
        width = self.length_y()
        s_nbr = self.neighbours.get(Direction.S)
        if s_nbr:
            if s_nbr.children: # is not leaf
                width = -1
                pass
            else:
                width += s_nbr.length_y()
                width = width // 2
        start = Point3D(self.x_max, self.y_min, z)
        end   = Point3D(self.x_min, self.y_min, z)
        if start.inside(self.polygon) and end.inside(self.polygon):
            sides.append(Side(start, end, width))
        
        return sides


    def down_to_size(self, lower: int, upper: int = -1) -> None:
        """
        Split length/width > upper or intersecting and length/width > lower.
        Lower limits the size downwards where geometry is detailed.
        Upper enforces splitting where no further detail would be needed.
        """
        if upper < lower:
            upper = int(1e9) # 1 meter
        side = max(self.length_x(), self.length_y())
        if side <= lower: # both inside range -> ok
            return
        # one not inside range -> split if not already split
        if self.relation() == Relation.intersecting or side > upper:
            if not self.children:
                self.split()
        # recursively for children
        for child in self.children.values():
            child.down_to_size(lower, upper)
