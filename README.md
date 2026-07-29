# cam-programming

Builds a labeled face adjacency graph from a STEP (CAD) file. Nodes are B-rep faces, edges are where they meet. Each carries attributes (surface type, convexity, geometry) that downstream steps use for tool access direction assignment and sub-machining region detection.

## Setup

```bash
conda env create -f environment.yml
conda activate occwl
```

## Run

```bash
python main.py
```

Expects `cad-files/block.step [OR] box.step` (included).

## What main.py does

1. **Load** — reads a STEP file, asserts one closed solid
2. **Raw graph** — `face_adjacency` from occwl → directed graph (faces as nodes, B-rep edges as arcs)
3. **Rebuild** — converts to undirected, adds convexity labels (CONVEX / CONCAVE / SMOOTH) and face surface types

## Reference docs

- [`docs/occwl-api.md`](docs/occwl-api.md) — occwl API surface we actually use
- [`docs/networkx-basics.md`](docs/networkx-basics.md) — networkx from first principles

## Dependencies

- [occwl](https://github.com/AutodeskAILab/occwl) — OpenCASCADE wrapper for B-rep traversal and adjacency graphs
- networkx — graph data structure
- numpy
