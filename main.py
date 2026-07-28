from occwl.graph import face_adjacency
from occwl.compound import Compound
from occwl.edge_data_extractor import EdgeDataExtractor
import networkx as nx
import math
import numpy as np


#this is taking a super simple step file and turning it into a labeled adjacency 
#graph - nodes are "faces," edges are what connects them

#load the example step file. assert one solid and the file is "closed" (basically the file is a real shape)


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


def raw_graph():
    # i know this file is hardcoded
    solid = load_solid("cad-files/box.step")
    #turns the shape into an attributed adjacency graph. nodes are faces connected by edges -- both carry attributes
    #this is a directed graph, though, so it double counts edges. meaning edge faces(1,2) and edge faces(2,1) are counted twice
    raw_graph = face_adjacency(solid)
    if raw_graph is None:
        raise ValueError("face_adjacency returned None — non-manifold or open shell")

    return raw_graph

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


rg = raw_graph()
ng = new_graph(rg)

print(dict(ng.nodes(data=True)))
print(dict(ng.adj))
