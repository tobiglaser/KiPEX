from translator import Translator
from dataclasses import dataclass, field
import pyvista as pv
import numpy as np
from itertools import count
from kipy.util.units import to_mm
#from numpy import ND

_palette = [
    "#1f77b4",  # blue
    "#ff7f0e",  # orange
    "#2ca02c",  # green
    "#d62728",  # red
    "#9467bd",  # purple
    "#8c564b",  # brown
    "#e377c2",  # pink
    "#7f7f7f",  # gray
    "#bcbd22",  # yellow-green
    "#17bdcf",  # cyan
]

@dataclass
class Visualizer():
    translator: Translator

    plotter: pv.Plotter = field(init=False, default_factory=pv.Plotter)

    nodes: dict[str, np.ndarray] = field(init=False, default_factory=dict)
    edges: dict[str, tuple[str, str, float, float]] = field(init=False, default_factory=dict)
    equivs: list[list[str]] = field(init=False, default_factory=list)
    adj: dict[str, set] = field(init=False, default_factory=dict)
    ports: list[tuple[str, str, str]] = field(init=False, default_factory=list)

    def find_adjacency(self) -> None:
        self.adj = {node: set() for node in self.nodes.keys()}
        for start, end, width, height in self.edges.values():
            self.adj[start].add(end)
            self.adj[end].add(start)

        for equiv in self.equivs:
            for node in equiv:
                self.adj[node].update(n for n in equiv if n != node)
                pass

        component: dict[str, int] = {}
        comp_id = count()
        for node in self.nodes.keys():
            if node in component:
                continue
            cid = next(comp_id)
            stack = [node]
            while stack:
                x = stack.pop()
                if x in component:
                    continue
                component[x] = cid
                stack.extend(self.adj[x] - set(component))

        self.unique_components = sorted(set(component.values()))
        self.components = component

        self.comp_color = {cid: _palette[cid % len(_palette)] for cid in self.unique_components}


    def vis_points(self, labels: bool = False) -> None:
        nodes = self.translator.nodes.values()
        points = np.array([[to_mm(p.position.x), to_mm(p.position.y), to_mm(p.position.z)] for p in nodes])
        p_labels = [str(n) for n in nodes]

        self.plotter.add_points(
            points,
            #color=node_colors,
            point_size=10,
            render_points_as_spheres=True,
        )

        if labels:
            self.plotter.add_point_labels(
                points,
                p_labels,
                font_size=14,
                text_color="white",
                always_visible=True,
            )
    @staticmethod
    def _rectangular_edge(p1, p2, width=0.05, height=0.05):
        """Return a rectangular bar (thin box) between p1 and p2."""
        center = (p1 + p2) / 2
        length = np.linalg.norm(p2 - p1)
        direction = (p2 - p1) / length

        # Create a box aligned with +X, then rotate into place
        box = pv.Box(bounds=(
            -length/2, length/2,
            -width/2, width/2,
            -height/2, height/2))

        # Compute rotation
        x_axis = np.array([1, 0, 0])
        axis = np.cross(x_axis, direction)
        angle = np.degrees(np.arccos(np.dot(x_axis, direction)))

        if np.linalg.norm(axis) > 1e-6:
            box = box.rotate_vector(axis, angle, point=(0, 0, 0))

        # Move to correct location
        box = box.translate(center)
        return box
    def vis_edges(self, labels: bool = False) -> None:
        edge_midpoints = []
        edge_names = []
        component_meshes: dict[int, list] = {cid: [] for cid in self.unique_components}
        
        for name, edge in self.edges.items():
            p1, p2 = edge[0], edge[1]
            cid = self.components[p1]
            bar = self._rectangular_edge(self.nodes[p1], self.nodes[p2], width=edge[2], height=edge[3])
            #self.plotter.add_mesh(bar, color=self.comp_color[cid])
            component_meshes[cid].append(bar)

            edge_midpoints.append((self.nodes[p1] + self.nodes[p2]) / 2)
            edge_names.append(name)

        for cid, meshes in component_meshes.items():
            if not meshes: continue
            merged = meshes[0].merge(meshes[1:] if len(meshes) > 1 else meshes[0])
            self.plotter.add_mesh(merged, color=self.comp_color[cid], opacity=0.5)
        
        if labels:
            self.plotter.add_point_labels(
                np.array(edge_midpoints),
                edge_names,
                font_size=12,
                text_color="yellow",
                always_visible=True,
            )

    def vis_equivs(self) -> None:
        for equiv in self.equivs:
            for i, node in enumerate(equiv[:-1]):
                bar = self._rectangular_edge(self.nodes[node], self.nodes[equiv[i+1]], 0.1, 0.1)
                self.plotter.add_mesh(bar, color="red")

    def vis_ports(self) -> None:
        for start, end, name in self.ports:
            points = np.array([self.nodes[start], self.nodes[end]])
            color = self.comp_color[self.components[start]]
            self.plotter.add_points(
                points,
                color=color,
                point_size=15,
                render_points_as_spheres=True,
            )
            labels = [f"{name}-start", f"{name}-end"]
            self.plotter.add_point_labels(
                points,
                labels,
                font_size=14,
                text_color=color,
                always_visible=True,
            )


    def visualize(self) -> None:
        for point, node in self.translator.nodes.items():
            self.nodes[str(node)] = np.array([to_mm(point.x), to_mm(point.y), to_mm(point.z)])
        for element in self.translator.elements.values():
            self.edges[str(element)] = (str(element.start), str(element.end), to_mm(element.width), to_mm(element.height))
        for equiv in self.translator.eqivs:
            self.equivs.append([str(n) for n in equiv.nodes])
        for port in self.translator.processed_ports:
            start = str(port.start)
            end = str(port.end)
            name = port.name
            self.ports.append((start, end, name))



        self.find_adjacency()

        self.vis_points()
        self.vis_edges()
        self.vis_equivs()
        self.vis_ports()

        self.plotter.show()



