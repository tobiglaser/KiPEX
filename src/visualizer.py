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
    edges: dict[str, tuple[str, str, float, float, tuple[float, float, float]]] = field(init=False, default_factory=dict)
    equivs: list[list[str]] = field(init=False, default_factory=list)
    adj: dict[str, set] = field(init=False, default_factory=dict)
    ports: list[tuple[str, str, str]] = field(init=False, default_factory=list)

    def find_adjacency(self) -> None:
        self.adj = {node: set() for node in self.nodes.keys()}
        for start, end, width, height, w_dir in self.edges.values():
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
        points = np.array(list(self.nodes.values()))
        p_labels = [str(n) for n in self.nodes.keys()]

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
        box = pv.Box(bounds=np.array([
            -length/2, length/2,
            -width/2, width/2,
            -height/2, height/2]))

        # Compute rotation
        x_axis = np.array([1, 0, 0])
        axis = np.cross(x_axis, direction)
        angle = np.degrees(np.arccos(np.dot(x_axis, direction)))

        if np.linalg.norm(axis) > 1e-6:
            box = box.rotate_vector(axis, angle, point=(0, 0, 0))

        # Move to correct location
        box = box.translate(center)
        return box
    def vis_edges(self) -> None:
        # Group edge data by component.
        grouped = {cid: [] for cid in self.unique_components}

        for name, edge in self.edges.items():
            p1, p2 = edge[0], edge[1]
            cid = self.components[p1]

            grouped[cid].append(
                (name, self.nodes[p1], self.nodes[p2], edge[2], edge[3], edge[4])
            )

        # Signs defining the eight corners of a box.
        # Columns: longitudinal direction, width axis, height axis.
        signs = np.array([
            [-1, -1, -1],
            [-1,  1, -1],
            [-1,  1,  1],
            [-1, -1,  1],
            [ 1, -1, -1],
            [ 1,  1, -1],
            [ 1,  1,  1],
            [ 1, -1,  1],
        ], dtype=float)

        # Four vertices per face.
        face_vertices = np.array([
            [0, 3, 2, 1],
            [4, 5, 6, 7],
            [0, 1, 5, 4],
            [1, 2, 6, 5],
            [2, 3, 7, 6],
            [3, 0, 4, 7],
        ], dtype=np.int64)


        for cid, edges in grouped.items():
            if not edges:
                continue

            names, start_points, end_points, widths, heights, w_directions = zip(*edges)

            p1 = np.asarray(start_points, dtype=float)
            p2 = np.asarray(end_points, dtype=float)
            widths = np.asarray(widths, dtype=float)
            heights = np.asarray(heights, dtype=float)
            w_directions = np.asarray(w_directions, dtype=float)

            delta = p2 - p1
            lengths = np.linalg.norm(delta, axis=1)

            # Skip zero-length edges.
            valid = lengths > 1e-12
            if not np.any(valid):
                continue

            #names = np.asarray(names, dtype=object)[valid]
            p1 = p1[valid]
            p2 = p2[valid]
            delta = delta[valid]
            lengths = lengths[valid]
            widths = widths[valid]
            heights = heights[valid]
            w_directions = w_directions[valid]

            directions = delta / lengths[:, None]
            centers = (p1 + p2) * 0.5

            n_edges = len(lengths)

            width_axis = w_directions
            height_axis = np.cross(directions, width_axis)

            # Half-dimension vectors.
            d = directions * (lengths * 0.5)[:, None]
            u = width_axis * (widths * 0.5)[:, None]
            v = height_axis * (heights * 0.5)[:, None]

            # Vectorized construction of all 8 vertices per edge.
            points = (
                centers[:, None, :]
                + signs[None, :, 0, None] * d[:, None, :]
                + signs[None, :, 1, None] * u[:, None, :]
                + signs[None, :, 2, None] * v[:, None, :]
            )

            points = points.reshape(-1, 3)

            # Generate all face indices in one batch.
            offsets = 8 * np.arange(n_edges, dtype=np.int64)

            indices = offsets[:, None, None] + face_vertices[None, :, :]
            counts = np.full((n_edges, 6, 1), 4, dtype=np.int64)

            # PyVista face format: [4, i0, i1, i2, i3, ...].
            faces = np.concatenate(
                [counts, indices], axis=2
            ).reshape(-1)

            mesh = pv.PolyData(points, faces)

            self.plotter.add_mesh(
                mesh,
                color=self.comp_color[cid],
                opacity=0.5,
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
            self.nodes[str(node)] = np.array([to_mm(point.x), -to_mm(point.y), to_mm(point.z)])
        for element in self.translator.elements.values():
            if element.w_direction:
                w_dir = element.w_direction
            else:
                delta = self.nodes[str(element.start)] - self.nodes[str(element.end)]
                if np.isclose(delta[0], 0) and np.isclose(delta[1], 0):
                    # "If the length direction is parallel to the z-axis, then the width is assumed along the x-axis"
                    w_dir = (1.0, 0.0, 0.0)
                else:
                    # "width vector is assumed to lie in x-y plane perpendicular to the length"
                    dir = np.cross(delta, [0, 0, 1])
                    w_dir = dir / np.linalg.norm(dir)
                    w_dir = (w_dir[0], w_dir[1], w_dir[2])
            self.edges[str(element)] = (str(element.start), str(element.end), to_mm(element.width), to_mm(element.height), w_dir)
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

        #self.plotter.show_axes_all()
        self.plotter.show()



