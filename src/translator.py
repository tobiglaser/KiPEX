from __future__ import annotations
from typing import TextIO
from math import ceil
from kipy import KiCad
from kipy.errors import ApiError
from kipy.board import Board
from kipy.board_types import Net, Track, ArcTrack, Zone, Pad
from kipy.geometry import PolygonWithHoles
from kipy.proto.board.board_types_pb2 import BoardLayer, PadType, ViaType
from kipy.util.units import to_mm, from_mm
from dataclasses import dataclass, field
from enum import Enum
from functools import cache
from filaments import get_filament_number
import shapely
from quad import Quad, Relation
from point3d import Point3D
from api_warning import api_warning


class FilamentMode(Enum):
    default = 0 # whatever default means

class ViaMode(Enum):
    ignore_inner_layers = 0

@dataclass
class CopperZone():
    polygon: shapely.Polygon
    net: str
    layer: BoardLayer.ValueType

@dataclass
class Node():
    index: int
    net:   str
    position: Point3D = field(default_factory=Point3D)
    def __str__(self) -> str:
        return f"N{self.index}"
    def to_line(self) -> str:
        return f"N{self.index} x={to_mm(self.position.x)} y={to_mm(self.position.y)} z={to_mm(self.position.z)}\n"

@dataclass
class Element():
    index:  int
    start:  Node
    end:    Node
    width:  int
    height: int
    nwinc: int = 1
    nhinc: int = 1
    w_ratio: int = 2
    h_ratio: int = 2
    sigma: float | None = None # 1/(mm*Ohm)
    def to_line(self) -> str:
        extra = ""
        if self.nwinc != 1: extra += f" nwinc={self.nwinc}"
        if self.nhinc != 1: extra += f" nhinc={self.nhinc}"
        if self.w_ratio != 2: extra += f" rw={self.w_ratio}"
        if self.h_ratio != 2: extra += f" rh={self.h_ratio}"
        if self.sigma: extra += f" sigma={self.sigma}"
        return f"E{self.index} {self.start} {self.end} w={to_mm(self.width)} h={to_mm(self.height)}{extra}\n"

@dataclass
class PreliminaryPort():
    start_pad: Pad
    start_layer: BoardLayer.ValueType
    end_pad: Pad
    end_layer: BoardLayer.ValueType
    name: str

@dataclass
class Port():
    start: Node
    end: Node
    name: str
    def to_line(self) -> str:
        name = self.name.replace("/", "")
        return f".external {self.start} {self.end} {name}\n"

@dataclass
class Frequencies():
    min: float = 0
    max: float = 0
    ndec: int = 1
    def to_line(self) -> str:
        return f".freq fmin={self.min} fmax={self.max} ndec={self.ndec}\n"

@dataclass
class Equivalence():
    nodes: list[Node] = field(default_factory=list, init=True)
    def append(self, nodes: Node | list[Node]):
        if isinstance(nodes, list):
            self.nodes += nodes
        else:
            self.nodes.append(nodes)
    def to_line(self) -> str:
        node_strings = [str(node) for node in self.nodes]
        return f".equiv {' '.join(node_strings)}\n"

@dataclass
class PlatedHole():
    diameter: int
    x: int
    y: int
    start_layer: BoardLayer.ValueType
    end_layer: BoardLayer.ValueType
    conductance: float
    net: str
    mode: ViaMode


@dataclass
class Translator():
    """
    Coordinates in nanometers until export or visualization step
    """
    board: Board
    pad_by_name: dict = field(init=True)
    nets: list[str] = field(default_factory=list, init=False)
    frequency: Frequencies = field(default_factory=Frequencies, init=False)
    conductivity: float = 5.8e4 # 1/(mm*Ohm)
    via_mode: ViaMode = ViaMode.ignore_inner_layers
    filament_mode: FilamentMode = FilamentMode.default
    nodes: dict[Point3D, Node] = field(default_factory=dict, init=False)
    elements: dict[tuple[Point3D, Point3D], Element] = field(default_factory=dict, init=False)
    preliminary_ports: list[PreliminaryPort] = field(default_factory=list, init=False)
    processed_ports: list[Port] = field(default_factory=list, init=False)
    zs: dict[BoardLayer.ValueType, int] = field(default_factory=dict, init=False)
    copper_thicknesses: dict[BoardLayer.ValueType, int] = field(default_factory=dict, init=False)
    node_index: int = field(default=0, init = False)
    element_index: int = field(default=0, init = False)
    element_max_length: int = field(default=int(1e9), init = False) # 1m
    copper_zones: list[CopperZone] = field(default_factory=list, init=False)
    eqivs: list[Equivalence] = field(default_factory=list, init=False)

    def reset(self) -> None:
        self.nets: list[str] = []
        self.nodes: dict[Point3D, Node] = {}
        self.elements: dict[tuple[Point3D, Point3D], Element] = {}
        self.preliminary_ports: list[PreliminaryPort] = []
        self.processed_ports: list[Port] = []
        self.zs: dict[BoardLayer.ValueType, int] = {}
        self.copper_thicknesses: dict[BoardLayer.ValueType, int] = {}
        self.node_index: int = 0
        self.element_index: int = 0
        self.copper_zones: list[CopperZone] = []
        self.eqivs: list[Equivalence] = []

    def set_frequency_range(self, fmin: float, fmax: float, ndec: int = 1) -> None:
        self.frequency = Frequencies(fmin, fmax, ndec)

    def set_max_element_length(self, nm: int) -> None:
        self.max_element_length = nm

    def set_via_mode(self, mode: ViaMode) -> None:
        self.via_mode = mode

    def set_filament_mode(self, mode: FilamentMode) -> None:
        self.filament_mode = mode

    def translate(self) -> str | None:
        """Actually do the thing."""
        try:
            self.stackup()
            self.zones()
            self.traces()
            self.vias()
            self.ports()
        except ApiError as error:
            if error.code == 7:
                api_warning()
                return "API busy"
            else:
                raise error

    def export(self, file: TextIO, title: str = "Auto generated via KiPEX") -> None:
        file.write(f"*{title}\n")
        file.write(".Units MM\n")
        file.write(f".Default sigma={self.conductivity}\n")
        file.write(self.frequency.to_line())
        for node in self.nodes.values():
            file.write(node.to_line())
        for element in self.elements.values():
            file.write(element.to_line())
        for equiv in self.eqivs:
            file.write(equiv.to_line())
        for port in self.processed_ports:
            file.write(port.to_line())
        file.write(".end")

    def add_port_from_netpanel(self, start: str, end: str, name: str = "") -> None:
        #start
        start_pad = self.pad_by_name[start]
        if start.endswith("(Back)"):
            start_layer = BoardLayer.BL_B_Cu
        elif start.endswith("(Front)"):
            start_layer = BoardLayer.BL_F_Cu
        else:
            layers = start_pad.padstack.layers
            if BoardLayer.BL_F_Cu in layers: 
                start_layer = BoardLayer.BL_F_Cu
            else:
                start_layer = BoardLayer.BL_B_Cu
        #end
        end_pad = self.pad_by_name[end]
        if end.endswith("(Back)"):
            end_layer = BoardLayer.BL_B_Cu
        elif end.endswith("(Front)"):
            end_layer = BoardLayer.BL_F_Cu
        else:
            layers = end_pad.padstack.layers
            if BoardLayer.BL_F_Cu in layers: 
                end_layer = BoardLayer.BL_F_Cu
            else:
                end_layer = BoardLayer.BL_B_Cu
        #add
        self.add_port_from_pads(start_pad, start_layer, end_pad, end_layer, name)
    
    def add_port_from_pads(self, start_pad: Pad, start_layer: BoardLayer.ValueType, end_pad: Pad, end_layer: BoardLayer.ValueType, name: str):
        if not start_pad.net.name == end_pad.net.name:
            raise Exception("Port nets did not match.")
        self.add_net(start_pad.net.name)
        self.preliminary_ports.append(PreliminaryPort(start_pad, start_layer, end_pad, end_layer, name))
    
    def add_net(self, net: str) -> None:
        if net not in self.nets:
            self.nets.append(net)

    def stackup(self) -> None:
        stackup = self.board.get_stackup()
        z = 0
        for layer in stackup.layers:
            thickness = layer.thickness
            if layer.material_name == "copper":
                self.copper_thicknesses[layer.layer] = thickness
                self.zs[layer.layer] = z + (thickness // 2)
                z += thickness
            if layer.layer == BoardLayer.BL_UNDEFINED:
                z += thickness

    def is_two_layer(self) -> bool:
        return len(self.copper_thicknesses) == 2

    def traces(self) -> None:
        """Ignores Traces beginning and ending in the same copper polygon."""
        for track in self.board.get_tracks():
            if not track.net.name in self.nets:
                continue
            if type(track) == ArcTrack:
                raise Exception("Arc Tracks not supported", track)
            z = self.zs[track.layer]

            position_A = Point3D(track.start.x, track.start.y, z)
            position_B = Point3D(track.end.x,   track.end.y,   z)
            for zone in self.copper_zones:
                if position_A.inside(zone.polygon) and position_B.inside(zone.polygon):
                    continue

            if not self.nodes.get(position_A):
                self.node_index += 1
                node_A = Node(self.node_index, track.net.name, position_A)
                self.nodes[position_A] = node_A
            else:
                node_A =  self.nodes[position_A]

            if not self.nodes.get(position_B):
                self.node_index += 1
                node_B = Node(self.node_index, track.net.name, position_B)
                self.nodes[position_B] = node_B
            else:
                node_B =  self.nodes[position_B]

            thickness = self.copper_thicknesses[track.layer]
            width = track.width
            nwinc, nhinc, w_ratio, h_ratio = self.calc_filaments(width, thickness, self.frequency.max, FilamentMode.default)

            if track.length() <= self.element_max_length:
                self.element_index += 1
                self.elements[position_A, position_B] = Element(
                    self.element_index,
                    node_A,
                    node_B,
                    width,
                    thickness,
                    nwinc,
                    nhinc,
                    w_ratio,
                    h_ratio
                )
            else:
                num_segs = ceil(track.length() / self.element_max_length)
                last_node = node_A
                last_pos = position_A
                x_step = (position_B.x - position_A.x) // num_segs
                y_step = (position_B.y - position_A.y) // num_segs
                for i in range(num_segs - 1):
                    next_pos = Point3D(last_pos.x + x_step, last_pos.y + y_step, z)
                    if not self.nodes.get(next_pos):
                        self.node_index += 1
                        next_node = Node(self.node_index, track.net.name, next_pos)
                        self.nodes[next_pos] = next_node
                    else:
                        next_node = self.nodes[next_pos]
                    
                    self.element_index += 1
                    self.elements[last_pos, next_pos] = Element(
                        self.element_index,
                        last_node,
                        next_node,
                        width,
                        thickness,
                        nwinc,
                        nhinc,
                        w_ratio,
                        h_ratio
                    )
                    last_pos = next_pos
                    last_node = next_node
                
                self.element_index += 1
                self.elements[last_pos, position_B] = Element(
                        self.element_index,
                        last_node,
                        node_B,
                        width,
                        thickness,
                        nwinc,
                        nhinc,
                        w_ratio,
                        h_ratio
                    )

    @staticmethod
    @cache
    def calc_filaments(width: int, height: int, fmax: float, mode: FilamentMode) -> tuple[int, int, int, int]:
        if mode == FilamentMode.default:
            rw = 2
            rh = 2
            nwinc = get_filament_number(to_mm(width), fmax, rw)
            nhinc = get_filament_number(to_mm(height), fmax, rh)
            return nwinc, nhinc, rw, rh
        else:
            raise Exception("Unknown FilamentMode")

    @staticmethod
    def polygon_kicad_to_shapely(polygon: PolygonWithHoles, create_holes: bool = True) -> shapely.Polygon:
        points = [shapely.Point(node.point.x, node.point.y) for node in polygon.outline.nodes] # extract points
        points.append(points[0]) # close loop
        lines = [shapely.LineString([points[i], points[i+1]]) for i in range(len(points)-1)]
        polygons = shapely.polygonize(lines).geoms
        # largest polygon *must* be the hull, rest are holes
        polygons = sorted(polygons, key=lambda poly: poly.area, reverse=True)
        poly = polygons[0]
        if create_holes:
            for p in polygons[1:]:
                poly = poly.difference(p)
        if type(poly) is not shapely.Polygon:
            raise TypeError("this should still be a polygon", type(poly), poly)
        return poly

    def zones(self) -> None:
        for zone in self.board.get_zones():
            net = zone.net.name if zone.net else ""
            if self.nets and not net in self.nets:
                continue
            for layer, polygons_kicad in zone.filled_polygons.items():
                for polygon_kicad in polygons_kicad:
                    polygon = self.polygon_kicad_to_shapely(polygon_kicad)
                    net = zone.net.name if zone.net else ""
                    self.copper_zones.append(CopperZone(polygon, net, layer))
        
        for zone in self.copper_zones:
            xmin, ymin, xmax, ymax = map(int, zone.polygon.bounds)
            quadtree = Quad(xmin, ymin, xmax, ymax, zone.polygon, None, 0)
            lower = upper = from_mm(3)
            print("Create Translation Options with proper settings entries.")
            quadtree.down_to_size(lower, upper)
            quadtree.set_neighbours()
            leaves = quadtree.get_leaves(Relation.inside | Relation.intersecting)
            leaves = sorted(leaves, key=lambda quad: quad.depth, reverse=True)
            
            z = self.zs[zone.layer]
            thickness = self.copper_thicknesses[zone.layer]
            for leaf in leaves:
                sides = leaf.to_inside_sides(z)
                for side in sides:
                    if not self.nodes.get(side.start):
                        self.node_index += 1
                        self.nodes[side.start] = Node(self.node_index, zone.net, side.start)
                    if not self.nodes.get(side.end):
                        self.node_index += 1
                        self.nodes[side.end] = Node(self.node_index, zone.net, side.end)
                    if not self.nodes.get(side.middle()):
                        if not self.elements.get((side.start, side.end)) and not self.elements.get((side.end, side.start)):
                                self.element_index += 1
                                self.elements[side.start, side.end] = Element(
                                    index=self.element_index,
                                    start=self.nodes[side.start],
                                    end=self.nodes[side.end],
                                    width=side.width,
                                    height=thickness
                                )

    def vias(self) -> None:
        """Only very basic vias for now."""
        if not self.is_two_layer() or not self.via_mode == ViaMode.ignore_inner_layers:
            raise Exception("Only two layers with most basic vias implemented.")
        
        PHs: list[PlatedHole] = []

        for via in self.board.get_vias():
            if not via.net.name in self.nets:
                continue
            if via.type != ViaType.VT_THROUGH:
                continue
            ph = PlatedHole(
                diameter=via.diameter,
                x=via.position.x,
                y=via.position.y,
                start_layer=via.padstack.drill.start_layer,
                end_layer=via.padstack.drill.end_layer,
                conductance=self.conductivity,
                net=via.net.name,
                mode=self.via_mode
            )
            PHs.append(ph)

        for pad in self.board.get_pads():
            if not pad.net.name in self.nets:
                continue
            if pad.pad_type == PadType.PT_PTH:
                ph = PlatedHole(
                    diameter=pad.padstack.drill.diameter.x,
                    x=pad.position.x,
                    y=pad.position.y,
                    start_layer=pad.padstack.drill.start_layer,
                    end_layer=pad.padstack.drill.end_layer,
                    conductance=self.conductivity,
                    net=pad.net.name,
                    mode=self.via_mode
                )
                PHs.append(ph)

        for ph in PHs:
            start_pos = Point3D(ph.x, ph.y, self.zs[ph.start_layer])
            end_pos   = Point3D(ph.x, ph.y, self.zs[ph.end_layer])
            start_node = self.nodes.get(start_pos)
            end_node   = self.nodes.get(end_pos)

            net_nodes = [n for n in self.nodes.values() if n.net == ph.net]
            if not start_node:
                closest_node = net_nodes[0]
                closest_distance = 1e9
                for node in net_nodes:
                    distance = start_pos.distance2D(node.position)
                    if distance < closest_distance:
                        closest_node = node
                        closest_distance = distance
                self.node_index += 1
                start_node = Node(self.node_index, ph.net, start_pos)
                self.nodes[start_pos] = start_node
                self.eqivs.append(Equivalence([start_node, closest_node]))
            if not end_node:
                closest_node = net_nodes[0]
                closest_distance = 1e9
                for node in net_nodes:
                    distance = end_pos.distance2D(node.position)
                    if distance < closest_distance:
                        closest_node = node
                        closest_distance = distance
                self.node_index += 1
                end_node = Node(self.node_index, ph.net, end_pos)
                self.nodes[end_pos] = end_node
                self.eqivs.append(Equivalence([end_node, closest_node]))
            
            via_conductance = ph.conductance
            #! Vastly underestimating Via resistance with solid copper conductor the size of via diameter.
            self.element_index += 1
            element = Element(
                self.element_index,
                start_node,
                end_node,
                ph.diameter,
                ph.diameter,
                sigma=via_conductance)
            self.elements[start_node.position, end_node.position] = element

    def ports(self) -> None:
        for pre_port in self.preliminary_ports:
            net = pre_port.start_pad.net.name
            # start
            z = self.zs[pre_port.start_layer]
            pad_polygon = self.board.get_pad_shapes_as_polygons(pre_port.start_pad, pre_port.start_layer)
            if not pad_polygon:
                raise Exception("No pad polygon found.", pre_port.start_pad)
            center = pad_polygon.bounding_box().center()
            center = Point3D(center.x, center.y, z)
            if self.nodes.get(Point3D(center.x, center.y, z)):
                start_node = self.nodes[Point3D(center.x, center.y, z)]
            else:
                polygon = self.polygon_kicad_to_shapely(pad_polygon, create_holes=False)
                inside_points = [position for position, node in self.nodes.items() if node.net == net and position.inside(polygon)]
                if not inside_points:
                    raise Exception("No available point inside Pad", pre_port.start_pad)
                closest_point = inside_points[0]
                closest_distance = 1e9
                for point in inside_points:
                    distance = center.distance2D(point)
                    if distance < closest_distance:
                        closest_point = point
                        closest_distance = distance
                start_node = self.nodes[closest_point]
            # end
            z = self.zs[pre_port.end_layer]
            pad_polygon = self.board.get_pad_shapes_as_polygons(pre_port.end_pad, pre_port.end_layer)
            if not pad_polygon:
                raise Exception("No pad polygon found.", pre_port.end_pad)
            center = pad_polygon.bounding_box().center()
            center = Point3D(center.x, center.y, z)
            if self.nodes.get(Point3D(center.x, center.y, z)):
                end_node = self.nodes[Point3D(center.x, center.y, z)]
            else:
                polygon = self.polygon_kicad_to_shapely(pad_polygon, create_holes=False)
                inside_points = [position for position, node in self.nodes.items() if node.net == net and position.inside(polygon)]
                if not inside_points:
                    raise Exception("No available point inside Pad", pre_port.end_pad)
                closest_point = inside_points[0]
                closest_distance = 1e9
                for point in inside_points:
                    distance = center.distance2D(point)
                    if distance < closest_distance:
                        closest_point = point
                        closest_distance = distance
                end_node = self.nodes[closest_point]
            
            port = Port(start_node, end_node, pre_port.name)
            self.processed_ports.append(port)

        pass


if __name__ == "__main__":
    translator = Translator(KiCad().get_board(), {})
    translator.translate()
    with open("export_test.txt", 'w') as file:
        translator.export(file, "My unique title.")

