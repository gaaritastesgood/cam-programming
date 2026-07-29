# occwl API — what we use

## Load a CAD File

```python
from occwl.compound import Compound

comp = Compound.load_from_step("block.step")
solid = list(comp.solids())[0]
solid.is_closed()   # True or adjacency will lie
solid.valid()       # True or geometry is broken
```

## Represent the shape as an adjacency graph

```python
from occwl.graph import face_adjacency

dg = face_adjacency(solid)   # -> nx.DiGraph, or None if non-manifold/open
```

| | key | value |
|---|---|---|
| node attr | `"face"` | `Face` object |
| edge attr | `"edge"` | oriented `Edge` |
| edge attr | `"edge_index"` | int |

**DiGraph with reciprocal arcs** — each B-rep edge creates both `(a,b)` and `(b,a)`. Skip duplicates with `if a > b: continue`.

## Convexity

```python
from occwl.edge_data_extractor import EdgeDataExtractor, EdgeConvexity

TANGENT_TOL = math.radians(5)

ex = EdgeDataExtractor(edge, [face_a, face_b], num_samples=10)
if ex.good:
    cvx = ex.edge_convexity(TANGENT_TOL)   # EdgeConvexity.CONVEX | CONCAVE | SMOOTH
```

**SMOOTH is ambiguous.** It collapses concave-tangent (fillet into pocket — keep) and convex-tangent (blend on outer corner — remove). You disambiguate by perturbing `ex.left_uvs`/`ex.right_uvs` into each face's interior, re-evaluating normals there, and rerunning the cross-product-dot-tangent sign test.

## Face geometry — for the enrichment pass

```python
f = dg.nodes[n]["face"]

# type
f.surface_type()       # "plane" "cylinder" "cone" "sphere" "torus" "bspline" ...

# normal at a point
uv = f.uv_bounds()     # -> Box2D — use mid-point for a representative sample
f.normal(uv)           # -> np.array(3), orientation-corrected

# area, centroid
f.area()
f.center_of_mass()     # -> np.array(3)

# axis (cylinder/cone/sphere axis direction)
surf = f.specific_surface()   # -> gp_Pln / gp_Cylinder / gp_Cone / ...
surf.Axis()                   # -> gp_Ax1, call .Direction() for the gp_Dir

# radius (cylinders, cones, tori)
surf.Radius()                 # cylinder/cone/sphere
surf.MinorRadius()            # torus fillet radius

# bounding box — for z_min, z_max
box = f.exact_box()           # -> Bnd_Box
z_min = box.CornerMin().Z()
z_max = box.CornerMax().Z()
```

## Edge geometry — what we read

```python
e.length()
e.has_curve()          # False → degenerate, skip
```

## Not in occwl — we write these

- Concave-tangent vs convex-tangent disambiguation
- TAD assignment
- Role assignment (B/F/C/S)
- D_min / wall & bottom thickness (`BRepExtrema_DistShapeShape` — raw OCCT, access via `f.topods_shape()`)
