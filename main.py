from curses import raw
from occwl.face import Face
from occwl.graph import face_adjacency
from occwl.compound import Compound
from occwl.edge_data_extractor import EdgeDataExtractor
import networkx as nx
import math


#this is taking a super simple step file and turning it into a labeled adjacency 
#graph - nodes are "faces," edges are what connects them

#load the example step file. assert one solid and the file is "closed" (basically the file is a real shape)


def load_solid(step_path):
    #comp is a Compound object, basically like a set of shapes. 
    comp = Compound.load_from_step(step_path)
    #i turn the comp object a python list of shape objects by convention, but really i expect one shape 
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
    # i know this is hardcoded
    solid = load_solid("cad-files/block.step")
    #turns the shape into an attributed adjacency graph. nodes are faces connected by edges -- both carry attributes
    #this is a directed graph, though, so it double counts edges. meaning edge faces(1,2) and edge faces(2,1) are counted twice
    raw_graph = face_adjacency(solid)
    if raw_graph is None:
        raise ValueError("face_adjacency returned None — non-manifold or open shell")

    return raw_graph

#The angle threshold below which two faces are called tangent instead of sharp is 5°
TANGENT_TOL = math.radians(5)

# just making a new graph with our desired schema, also making it undirected
#this tbh is our most important part -- figuring out the graph representation and then defining Sub-Machining Regions
def new_graph(rg):
    solid = load_solid("cad-files/block.step")
    ng = nx.Graph()
    #n is node index d is the node dict {face:face object}
    for n,d in rg.nodes(data = True):
        ng.add_node(n, stype=d["face"].surface_type(),
               tad=[], role=None, smr=None)
    #a,b are node indices (so like graph[0][1] is the edge connecting the two faces)
    #c is edge dict {edge:edge object, edge:index: number}
    for a,b,c in rg.edges(data=True):
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


#2 dicts, one adjacency dict: face and adjacent faces, and then one dict for face: attributes
#add_node adds to the node dict and presumably creates a node key in the adj list, and add_edge adds a value to adj list/dict
#undirected graph writes, when you add edge, node[1][2]= {}, and node [2][1] = {}, DiGraph only writes the one