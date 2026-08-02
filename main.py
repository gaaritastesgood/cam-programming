from contextlib import redirect_stdout, redirect_stderr
import argparse
import math
import os
import signal
import sys

import networkx as nx
import numpy as np
from occwl.compound import Compound
from occwl.edge_data_extractor import EdgeDataExtractor
from occwl.graph import face_adjacency
from occwl.viewer import Viewer
from PyQt5 import QtCore, QtWidgets


#this is taking a super simple step file and turning it into an attributed adjacency 
#graph - nodes are "faces," edges are what connects them. metadata about the two help us reason about the shape
#in the future when we want to identify "features" and such

STEP_PATH = "cad-files/block.step"

# distinct-ish colors so face ids in the viewer match the printed graph
FACE_COLORS = [
    (0.90, 0.30, 0.30),
    (0.30, 0.70, 0.30),
    (0.30, 0.45, 0.90),
    (0.95, 0.70, 0.20),
    (0.60, 0.30, 0.80),
    (0.20, 0.75, 0.75),
    (0.90, 0.45, 0.70),
    (0.50, 0.50, 0.50),
    (0.40, 0.70, 0.95),
]


def load_solid(step_path):
    #comp is a Compound object, basically like a set of shapes. 
    comp = Compound.load_from_step(step_path)
    #i turn the comp object a python list of shapes ( by convention, but really i expect one shape)
    #because why does one file have more than one shape?
    solids = list(comp.solids())

    if not solids:
        raise ValueError(f"{step_path}: no closed solids, needs sewing")
    if len(solids) > 1:
        raise ValueError(f"{step_path}: {len(solids)} bodies, assembly or geometry failed to unite")

    solid = solids[0]

    if not solid.is_closed():
        raise ValueError(f"{step_path}: open shell")
    if not solid.valid():
        raise ValueError(f"{step_path}: failed BRepCheck")

    return solid


def raw_graph(solid):
    #turns the shape into an attributed adjacency graph. nodes are faces connected by edges -- both carry attributes
    #this is a directed graph, though, so it double counts edges. meaning edge faces(1,2) and edge faces(2,1) are counted twice
    graph = face_adjacency(solid)
    if graph is None:
        raise ValueError("face_adjacency returned None — non-manifold or open shell")
    return graph


def show_viewer(rg, ng):
    """Rotatable window: each face colored + labeled with the same id as the printout."""
    _move = QtWidgets.QWidget.move
    QtWidgets.QWidget.move = lambda self, *a: (
        _move(self, int(a[0]), int(a[1])) if len(a) == 2 else _move(self, *a)
    )
    try:
        with open(os.devnull, "w") as quiet, redirect_stdout(quiet), redirect_stderr(quiet):
            v = Viewer(backend="qt-pyqt5")
            for n, d in rg.nodes(data=True):
                v.display(d["face"], color=FACE_COLORS[n % len(FACE_COLORS)])
                v.display_text(ng.nodes[n]["sample"], str(n), height=25, color=(0.0, 0.0, 0.0))
            v.fit()

        app = QtWidgets.QApplication.instance()
        if app:
            #quit window on suspension or termination
            for s in (signal.SIGINT, signal.SIGTERM, signal.SIGTSTP, getattr(signal, "SIGHUP", None)):
                if s is not None:
                    signal.signal(s, lambda *_: app.quit())
            app._tick = QtCore.QTimer(app)
            app._tick.start(200)
            app._tick.timeout.connect(lambda: None)

        v.show()
    finally:
        QtWidgets.QWidget.move = _move

#The angle threshold below which two faces are called tangent instead of sharp is 5°
TANGENT_TOL = math.radians(5)

#this is just finding values that are needed to calculate the face normal and get a sample point on a shape. 
#we need those two for other calculations. surprised they dont come out of the box in this library
def interior_uv(face, face_id, grid=7):
    box = face.uv_bounds()
    lo, hi = box.min_point(), box.max_point()

    mid = (lo + hi) / 2
    if face.inside((mid[0], mid[1])):
        return (mid[0], mid[1])

    u_min, u_max = lo[0], hi[0]
    v_min, v_max = lo[1], hi[1]
    for i in range(grid):
        u = u_min + (u_max - u_min) * i / (grid - 1)
        for j in range(grid):
            v = v_min + (v_max - v_min) * j / (grid - 1)
            if face.inside((u, v)):
                return (u, v)

    raise ValueError(f"face {face_id}: no interior uv found on {grid}x{grid} grid")

def face_sample(face, face_id, grid=7):
    uv = interior_uv(face, face_id, grid)
    normal = tuple(float(x) for x in face.normal(uv))
    point  = tuple(float(x) for x in face.point(uv))
    return normal, point

#making a new graph with a schema of our choosing, also making it undirected
def new_graph(rg):
    ng = nx.Graph()
    #n is node index d is the node dict {face:face object}
    for n, d in rg.nodes(data=True):
        face = d["face"]
        ng.add_node(n, stype=face.surface_type(), tad=[], role=None, smr=None,
                    normal=face_sample(face, n)[0], area = face.area(), sample = face_sample(face, n)[1])
    #a,b are node indices (so like graph[0][1] is the edge connecting the two faces)
    #c is edge dict {edge:edge object, edge:index: number}
    for a, b, c in rg.edges(data=True):
        if a > b:
            continue
        e = c["edge"]
        edge_faces = [rg.nodes[a]["face"], rg.nodes[b]["face"]]

        #if the extractor identified faces to the left and right, get the convexity of -- 
        # -- the edge (convex, concave, or smooth). 
        #else dont
        ex = EdgeDataExtractor(e, edge_faces, num_samples=10)
        if ex.good:
            cvx = ex.edge_convexity(TANGENT_TOL).name
        else:
            cvx = None
        ng.add_edge(a, b, convexity=cvx, length=e.length())
    return ng


def print_graph(ng):
    print(f"{ng.number_of_nodes()} faces, {ng.number_of_edges()} edges\n")

    print("faces")
    for n, d in sorted(ng.nodes(data=True)):
        print(
            f"  {n}: {d['stype']}  "
            f"normal={d['normal']}  "
            f"area={d['area']:.1f}  "
            f"sample={d['sample']}  "
            f"role={d['role']}  tad={d['tad']}  smr={d['smr']}"
        )

    print("\nedges")
    for a, b, d in sorted(ng.edges(data=True)):
        print(f"  {a}–{b}: convexity={d['convexity']}  length={d['length']:.1f}")


def _reexec_macos_framework_python():
    """Always run under conda’s framework Python when it exists (required for GUI on macOS)."""
    framework = os.path.join(sys.prefix, "python.app", "Contents", "MacOS", "python")
    if not os.path.isfile(framework):
        return
    # Don’t use realpath — it resolves python.app back to bin/python and skips the switch.
    if "python.app" in sys.executable:
        return
    # pythonw sets PYTHONEXECUTABLE so the child would keep lying; drop it.
    env = os.environ.copy()
    env.pop("PYTHONEXECUTABLE", None)
    os.execve(framework, [framework, *sys.argv], env)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build attributed face graph from a STEP file")
    parser.add_argument("--view", action="store_true", help="open rotatable 3D viewer after printing")
    args = parser.parse_args()

    if args.view:
        _reexec_macos_framework_python()

    solid = load_solid(STEP_PATH)
    rg = raw_graph(solid)
    ng = new_graph(rg)
    print_graph(ng)

    if args.view:
        show_viewer(rg, ng)
