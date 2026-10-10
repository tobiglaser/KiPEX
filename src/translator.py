from __future__ import annotations
from typing import TextIO
from math import ceil
from kipy import KiCad
from kipy.errors import ApiError
from kipy.board import Board
from kipy.board_types import Net, Track, ArcTrack, Zone, Pad, FootprintInstance, BoardPolygon
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
    full = 0

class MockUpOptions(Enum):
    mock_up = 0
    direct = 1

@dataclass
class CopperZone():
    polygon: shapely.Polygon
    net: str
    layer: BoardLayer.ValueType
    nodes: set[Point3D] = field(default_factory=set, init=False)

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
    def __str__(self) -> str:
        return f"E{self.index}"
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
    via_mode: ViaMode = ViaMode.full
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
    quad_upper_mm: float = 3
    quad_lower_mm: float = 0.25
    bridge_default_height_mm: float = 0.5
    bridge_default_thickness_mm: float = 0.2
    bridge_default_width_mm: float = 1
    bridging_fp_layer: BoardLayer.ValueType = BoardLayer.BL_User_1
    bridging_footprints: list[tuple[FootprintInstance, MockUpOptions]] = field(init=False, default_factory=list)

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
        self.bridging_footprints = []

    def set_frequency_range(self, fmin: float, fmax: float, ndec: int = 1) -> None:
        self.frequency = Frequencies(fmin, fmax, ndec)

    def set_max_element_length(self, nm: int) -> None:
        self.max_element_length = nm

    def set_via_mode(self, mode: ViaMode) -> None:
        self.via_mode = mode

    def set_filament_mode(self, mode: FilamentMode) -> None:
        self.filament_mode = mode

    def set_quad_limits(self, upper_mm: float, lower_mm: float) -> None:
        self.quad_upper_mm = upper_mm
        self.quad_lower_mm = lower_mm

    def set_bridging_footprint_layer(self, layer: BoardLayer.ValueType) -> None:
        self.bridging_fp_layer = layer

    def set_footprint_quad_limits(self, upper_mm: float, lower_mm: float) -> None:
        self.fp_quad_upper_mm = upper_mm
        self.fp_quad_lower_mm = lower_mm

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
    
    def translate_loop(self, pad_mode: str = "inside") -> str | None:
        """ "closest" (to pad center) or "inside" (pad)"""
        try:
            self.stackup()
            self.zones()
            self.traces()
            self.vias()
            self.footprints_mockup(pad_mode)
            self.footprints_direct(pad_mode)
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
        if not start_pad.net.name in self.nets:
            self.add_net(start_pad.net.name)
        if not end_pad.net.name in self.nets:
            self.add_net(end_pad.net.name)
        self.preliminary_ports.append(PreliminaryPort(start_pad, start_layer, end_pad, end_layer, name))
    
    def add_net(self, net: str) -> None:
        if net not in self.nets:
            self.nets.append(net)

    def add_loop_footprint(self, reference: str, mode: MockUpOptions) -> None:
        fpis = self.board.get_footprints()
        for fpi in fpis:
            if reference == fpi.reference_field.text.value:
                if mode == MockUpOptions.direct:
                    self.bridging_footprints.append((fpi, mode))
                    return
                elif mode == MockUpOptions.mock_up:
                    shapes = fpi.definition.shapes
                    polycount = 0
                    for shape in shapes:
                        if shape.layer == self.bridging_fp_layer:
                            if type(shape) == BoardPolygon:
                                polycount += len(shape.polygons)
                    if polycount == 1:
                        self.bridging_footprints.append((fpi, mode))
                        return

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
            trace_inside = False
            a_in_zone = False
            b_in_zone = False
            for zone in self.copper_zones:
                if zone.layer != track.layer:
                    continue
                a_inside = position_A.inside(zone.polygon)
                b_inside = position_B.inside(zone.polygon)
                if a_inside and b_inside:
                    trace_inside = True
                    break
                elif a_inside:
                    a_in_zone = True
                elif b_inside:
                    b_in_zone = True
            if trace_inside:
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

            inside_nodes: list[Node] = []
            inside_nodes += [node_A] if a_in_zone else []
            inside_nodes += [node_B] if b_in_zone else []
            for trace_node in inside_nodes:
                if not trace_node: continue
                closest_node = None
                closest_dist = 1e9
                for node in self.nodes.values():
                    if not node.net == track.net.name or not node.position.z == trace_node.position.z:
                        continue
                    distance = trace_node.position.distance2D(node.position)
                    if distance < closest_dist and not node == trace_node:
                        closest_dist = distance
                        closest_node = node
                if not closest_node: raise # we are already in a zone
                equiv = Equivalence([trace_node, closest_node])
                self.eqivs.append(Equivalence([trace_node, closest_node]))

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
        shapely.prepare(poly)
        return poly


    def find_closest_node_in_zone(self, position: Point3D, zone: CopperZone) -> tuple[Node | None, float]:
        closest_node = None
        closest_dist = 1e9 # 1 meter
        for pos in zone.nodes:
            node = self.nodes[pos]
            dist = node.position.distance2D(position)
            if dist < closest_dist:
                closest_node = node
                closest_dist = dist
        return closest_node, closest_dist

    def find_connecting_zone(self, pad: Pad, side: BoardLayer.ValueType) -> CopperZone | None:
        pad_polygon = self.board.get_pad_shapes_as_polygons(pad, side)
        if not pad_polygon: raise
        pad_poly = self.polygon_kicad_to_shapely(pad_polygon, create_holes=False)
        for zone in self.copper_zones:
            if zone.polygon.intersects(pad_poly) or zone.polygon.contains(pad_poly):
                return zone
        return None

    def pad_center(self, pad: Pad, side: BoardLayer.ValueType) -> Point3D:
        pad_polygon = self.board.get_pad_shapes_as_polygons(pad)
        if not pad_polygon: raise
        pad_center = pad_polygon.bounding_box().center()
        return Point3D(pad_center.x, pad_center.y, self.zs[side])

    def find_center_most_node_in_pad(self, pad: Pad, side: BoardLayer.ValueType) -> tuple[Node | None, float]:
        pad_polygon = self.board.get_pad_shapes_as_polygons(pad, side)
        if not pad_polygon: raise
        poly = self.polygon_kicad_to_shapely(pad_polygon, create_holes=False)
        inside_nodes = []
        for pos in self.nodes.keys():
            if shapely.contains_xy(poly, pos.x, pos.y):
                inside_nodes.append(self.nodes[pos])
        return self.find_closest_node(self.pad_center(pad, side), pad.net, inside_nodes)


    def find_closest_node(self, position: Point3D, net: Net, nodes: list[Node] = []) -> tuple[Node | None, float]:
        
        if not nodes:
            if node := self.nodes.get(position):
                return node, 0
            nodes = list(self.nodes.values())
        
        closest_dist = 1e9 # 1meter
        closest_node = None
        for node in nodes:
            if node.net != net.name: continue
            if node.position.z != position.z: continue
            dist = position.distance2D(node.position)
            if dist < closest_dist:
                closest_dist = dist
                closest_node = node
        return closest_node, closest_dist


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
            lower = from_mm(self.quad_lower_mm)
            upper = from_mm(self.quad_upper_mm)
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
                    zone.nodes.add(side.start)
                    zone.nodes.add(side.end)
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

    def get_mockup_parameters(self, footprint: FootprintInstance) -> tuple[int, int, int]:
        """returns tuple(width, height, thickness)"""
        height = None
        thickness = None
        width = None
        for field in footprint.texts_and_fields:
            name = getattr(field, "name", "")
            if name == "KiPEX_Height_mm": # we know that .text is populated here
                height = float(field.text.value.replace(',', '.')) # type: ignore
            if name == "KiPEX_Width_mm":
                width = float(field.text.value.replace(',', '.')) # type: ignore
            if name == "KiPEX_Thickness_mm":
                thickness = float(field.text.value.replace(',', '.')) # type: ignore
        if not height:
            height = self.bridge_default_height_mm
        if not thickness:
            thickness = self.bridge_default_thickness_mm
        if not width:
            width = self.bridge_default_width_mm
        return from_mm(width), from_mm(height), from_mm(thickness)

    def find_node_for_bridging(self, pad: Pad, side: BoardLayer.ValueType, pad_mode: str) -> Node:
        pos = Point3D(pad.position.x, pad.position.y, self.zs[side])
        node = None
        if zone := self.find_connecting_zone(pad, side):
            closest_node, distance = self.find_closest_node_in_zone(pos, zone)
            if not closest_node: raise
            if pad_mode == "inside":
                poly = self.board.get_pad_shapes_as_polygons(pad)
                if not poly: raise
                poly = self.polygon_kicad_to_shapely(poly)
                inside = shapely.contains_xy(poly, float(closest_node.position.x), float(closest_node.position.y))
                if not inside: raise Exception("No available node inside Pad", pad)
            node = closest_node
        else:
            most_center_node, distance = self.find_center_most_node_in_pad(pad, side)
            if not most_center_node: raise Exception("No available node inside Pad", pad)
            node = most_center_node
        return node


    def footprints_direct(self, pad_mode: str) -> None:
        for fp, mode in self.bridging_footprints:
            if mode != MockUpOptions.direct: continue 
            if len(fp.definition.pads) != 2: raise
            
            width, height, thickness = self.get_mockup_parameters(fp)

            if fp.layer == BoardLayer.BL_F_Cu:
                height = -height
            
            start_pad = fp.definition.pads[0]
            start_pos = Point3D(start_pad.position.x, start_pad.position.y, self.zs[fp.layer])
            start_node = self.find_node_for_bridging(start_pad, fp.layer, pad_mode)
            end_pad = fp.definition.pads[1]
            end_pos = Point3D(end_pad.position.x, end_pad.position.y, self.zs[fp.layer])
            end_node = self.find_node_for_bridging(end_pad, fp.layer, pad_mode)
            # go up
            up_pos = Point3D(start_pos.x, start_pos.y, start_pos.z + height)
            self.node_index += 1
            up_node = Node(self.node_index, "Bridge", up_pos)
            self.nodes[up_pos] = up_node
            self.element_index += 1
            up_element = Element(self.element_index, start_node, up_node, width, thickness)
            self.elements[start_node.position, up_pos] = up_element
            # go over
            over_pos = Point3D(end_pos.x, end_pos.y, end_pos.z + height)
            self.node_index += 1
            over_node = Node(self.node_index, "Bridge", over_pos)
            self.nodes[over_pos] = over_node
            self.element_index += 1
            over_element = Element(self.element_index, up_node, over_node, width, thickness)
            self.elements[up_pos, over_pos] = over_element
            #go down
            self.element_index += 1
            down_element = Element(self.element_index, over_node, end_node, width, thickness)
            self.elements[over_pos, end_pos] = down_element



    def footprints_mockup(self, pad_mode: str) -> None:
        for fp, mode in self.bridging_footprints:
            if mode != MockUpOptions.mock_up: continue
            bridge_poly = None
            for shape in fp.definition.shapes:
                if shape.layer == self.bridging_fp_layer and type(shape) == BoardPolygon:
                    bridge_poly = self.polygon_kicad_to_shapely(shape.polygons[0])
                    break
            if not bridge_poly: raise
            side = fp.layer
            pads: list[Pad] = []
            height = None
            thickness = None
            for pad in fp.definition.pads:
                pad_poly = self.board.get_pad_shapes_as_polygons(pad, side)
                if not pad_poly: raise
                pad_poly = self.polygon_kicad_to_shapely(pad_poly)
                if bridge_poly.intersects(pad_poly) and (not self.nets or pad.net.name in self.nets):
                    pads.append(pad)
            
            width, height, thickness = self.get_mockup_parameters(fp)
            
            xmin, ymin, xmax, ymax = map(int, bridge_poly.bounds)
            quadtree = Quad(xmin, ymin, xmax, ymax, bridge_poly, None, 0)
            lower = from_mm(self.fp_quad_lower_mm)
            upper = from_mm(self.fp_quad_upper_mm)
            quadtree.down_to_size(lower, upper)
            quadtree.set_neighbours()
            leaves = quadtree.get_leaves(Relation.inside | Relation.intersecting)
            leaves = sorted(leaves, key=lambda quad: quad.depth, reverse=True)

            z_bridge = self.zs[side]
            if side == BoardLayer.BL_F_Cu:
                z_bridge -= height
            else:
                z_bridge += height
            thickness = thickness
            for leaf in leaves:
                sides = leaf.to_inside_sides(z_bridge)
                for side in sides:
                    if not self.nodes.get(side.start):
                        self.node_index += 1
                        self.nodes[side.start] = Node(self.node_index, "Bridge", side.start)
                    if not self.nodes.get(side.end):
                        self.node_index += 1
                        self.nodes[side.end] = Node(self.node_index, "Bridge", side.end)
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

            for pad in pads:
                side = fp.layer
                z_pad = self.zs[side]
                pad_polygon = self.board.get_pad_shapes_as_polygons(pad, side)
                if not pad_polygon: raise
                bounding_box = pad_polygon.bounding_box()
                center = bounding_box.center()
                center = Point3D(center.x, center.y, z_pad)
                if self.nodes.get(Point3D(center.x, center.y, z_pad)):
                    pad_node = self.nodes[Point3D(center.x, center.y, z_pad)]
                else:
                    polygon = self.polygon_kicad_to_shapely(pad_polygon, create_holes=False)
                    if pad_mode == "inside":
                        points = [position for position, node in self.nodes.items() if node.net == pad.net.name and position.inside(polygon) and position.z == z_pad]
                    elif pad_mode == "closest":
                        points = [position for position, node in self.nodes.items() if node.net == pad.net.name and position.z == z_pad]
                    else:
                        points = []
                    if not points:
                        raise Exception("No available point inside Pad", pad)
                    closest_point = points[0]
                    closest_distance = 1e9
                    for point in points:
                        distance = center.distance2D(point)
                        if distance < closest_distance:
                            closest_point = point
                            closest_distance = distance
                    pad_node = self.nodes[closest_point]

                if self.nodes.get(Point3D(center.x, center.y, z_bridge)):
                    bridge_node = self.nodes[Point3D(center.x, center.y, z_bridge)]
                else:
                    closest_distance = 1e9
                    closest_node = None
                    for point, node in self.nodes.items():
                        if not point.z == z_bridge:
                            continue
                        distance = point.distance2D(pad_node.position)
                        if distance < closest_distance:
                            closest_distance = distance
                            closest_node = node
                    if not closest_node: raise
                    bridge_node = closest_node
                
                width = min(bounding_box.size.x, bounding_box.size.y)

                self.element_index += 1
                element = Element(
                    self.element_index,
                    pad_node,
                    bridge_node,
                    width,
                    width,
                    )
                self.elements[pad_node.position, bridge_node.position] = element

    def vias(self) -> None:
        PHs: list[PlatedHole] = []

        for via in self.board.get_vias():
            if not via.net.name in self.nets:
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
            positions: list[Point3D] = []
            if ph.mode == ViaMode.full:
                if ph.start_layer > ph.end_layer:
                    tmp = ph.start_layer
                    ph.start_layer = ph.end_layer
                    ph.end_layer = tmp
                for layer, z in self.zs.items():
                    if layer > ph.end_layer: break
                    if layer < ph.start_layer: continue
                    positions.append(Point3D(ph.x, ph.y, z))

            net_nodes = None
            via_nodes: list[Node] = []
            for pos in positions:
                node = self.nodes.get(pos)
                if node:
                    via_nodes.append(node)
                else:
                    inside = False
                    for zone in self.copper_zones:
                        if zone.net != ph.net: continue
                        if self.zs[zone.layer] != pos.z: continue
                        if shapely.contains_xy(zone.polygon, pos.x, pos.y):
                            inside = True
                            break
                    if not inside and pos != positions[-1] and pos != positions[0]:
                        continue
                    elif not inside and (pos == positions[-1] or pos == positions[0]):
                        self.node_index += 1
                        node = Node(self.node_index, ph.net, pos)
                        via_nodes.append(node)
                        self.nodes[pos] = node
                    else:
                        if net_nodes == None: net_nodes = [n for n in self.nodes.values() if n.net == ph.net]
                        closest_node = None
                        closest_distance = 1e9
                        for node in net_nodes:
                            if node.position.z != pos.z: continue
                            if not closest_node: closest_node = node
                            distance = pos.distance2D(node.position)
                            if distance < closest_distance:
                                closest_node = node
                                closest_distance = distance
                        if not closest_node:
                            raise Exception(f"No node found for {ph} despite inside Polygon: {pos}")
                        self.node_index += 1
                        node = Node(self.node_index, ph.net, pos)
                        via_nodes.append(node)
                        self.nodes[pos] = node
                        self.eqivs.append(Equivalence([node, closest_node]))

            via_conductance = ph.conductance
            #! Vastly underestimating Via resistance with solid copper conductor the size of via diameter.
            for i, node in enumerate(via_nodes[:-1]):
                self.element_index += 1
                element = Element(
                    self.element_index,
                    via_nodes[i],
                    via_nodes[i+1],
                    ph.diameter,
                    ph.diameter,
                    sigma=via_conductance)
                self.elements[element.start.position, element.end.position] = element

    def ports(self) -> None:
        for pre_port in self.preliminary_ports:
            # start
            net = pre_port.start_pad.net.name
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
                inside_points = [position for position, node in self.nodes.items() if node.net == net and position.inside(polygon) and position.z == z]
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
            net = pre_port.end_pad.net.name
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
                inside_points = [position for position, node in self.nodes.items() if node.net == net and position.inside(polygon) and position.z == z]
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
    kicad = KiCad()
    board = kicad.get_board()
    translator = Translator(board, {})

    start_pad = None
    end_pad = None
    layer = None
    for fpi in board.get_footprints():
        try:
            if fpi.reference_field.text.value == "C9":
                start_pad = fpi.definition.pads[0]
                end_pad = fpi.definition.pads[1]
                layer = fpi.layer
        except: pass
    if not start_pad or not end_pad or not layer: raise

    translator.set_frequency_range(100e3, 100e3, 1)
    translator.add_net("Net-(U1-DRAIN_1)")
    translator.add_net("Net-(SW1-Pin_1)")
    translator.add_net("GND")
    translator.add_loop_footprint("U1", MockUpOptions.mock_up)
    translator.add_loop_footprint("U2", MockUpOptions.mock_up)
    translator.add_port_from_pads(start_pad, layer, end_pad, layer, "C9")
    translator.set_quad_limits(3, 1)
    translator.set_footprint_quad_limits(3, 1)

    translator.translate_loop("closest") # "closest" (to pad center) or "inside" (pad)
    
    from visualizer import Visualizer
    Visualizer(translator).visualize()
    import os
    working_dir = kicad.get_project(kicad.get_board().document).path
    working_dir = os.path.join(working_dir, "KiPEX")
    if not os.path.exists(working_dir):
        os.mkdir(working_dir)
    os.chdir(working_dir)
    with open("export_test.inp", 'w') as file:
        translator.export(file, "My unique title.")

