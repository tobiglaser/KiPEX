from __future__ import annotations
from dataclasses import dataclass
from math import sqrt
import shapely

@dataclass(slots=True, frozen=True)
class Point3D():
    x: int = 0
    y: int = 0
    z: int = 0
    def inside(self, poly: shapely.Polygon) -> bool:
        """ignores z"""
        return poly.contains(shapely.Point(self.x, self.y))
    def distance2D(self, other: Point3D) -> float:
        return sqrt((self.x - other.x)**2 + (self.y - other.y)**2)
    def distance3D(self, other: Point3D) -> float:
        return sqrt((self.x - other.x)**2 + (self.y - other.y)**2 + (self.z - other.z)**2)