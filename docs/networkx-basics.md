# NetworkX basics

## The one idea

An adjacency list `{1: [2, 3]}` but with a dict instead of a list so edges carry data:

```python
# adjacency dict — who connects to whom, with attributes
adj  = {1: {2: {"convexity": "CONCAVE"}}, 2: {1: {"convexity": "CONCAVE"}}}

# node dict — attributes per node
node = {1: {"stype": "plane"}, 2: {"stype": "cylinder"}}
```

That's the entire data structure. Two dicts. Everything else is convenience methods.

## Build

```python
import networkx as nx
g = nx.Graph()
g.add_node(1, stype="plane")
g.add_edge(1, 2, convexity="CONCAVE")   # auto-creates node 2 with empty attrs
```

`add_edge` on a nonexistent node creates it silently — a typo gives you a bare node instead of an error.

Undirected `add_edge(1,2)` writes both `adj[1][2]` and `adj[2][1]` — same dict object, so `g[1][2]["x"] = 1` is visible from `g[2][1]`.

## Read

```python
g.nodes[1]       # {'stype': 'plane'}         node attrs
g[1][2]          # {'convexity': 'CONCAVE'}   edge attrs — plain dict indexing
g.adj[1]         # {2: {'convexity': ...}}    adjacency row
```

## Loop with `data=True`

```python
for n, d in g.nodes(data=True):      # node id + attr dict
for u, v, d in g.edges(data=True):   # two endpoints + attr dict
```

Without `data=True` you just get ids/pairs.

## Write attributes later

```python
g.nodes[1]["role"] = "B"
g[1][2]["convexity"] = "SMOOTH"
```

Plain dict assignment. That's why we seed `role=None` when building — the slot exists, we fill it later.

## Graph vs DiGraph

`nx.Graph`: `(1,2)` and `(2,1)` are the same edge. `nx.DiGraph`: they're separate. occwl's `face_adjacency` returns a DiGraph with reciprocal arcs — we rebuild it as an undirected Graph, skipping duplicates with `if a > b: continue`.
