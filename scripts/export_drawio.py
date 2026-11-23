"""
Export the mythology knowledge graph to a multi-page draw.io (.drawio) file.

    python scripts/export_drawio.py

Layout principles (so arrows never run through entity blocks):

  * One relation family per page — mixing 142 edges of 10 kinds on one canvas
    can't be made readable, so each page carries a single, legible story.
  * Explicit exit/entry anchors on every edge (bottom→top, or right→left), so
    edges leave and enter at predictable points instead of being routed by
    draw.io through whatever lies between.
  * Proper DAG layering for genealogy (topological generations, with parents
    pulled down next to their children), then a barycentre pass to reduce
    crossings — long edges that would cross intermediate rows become short.
  * Generous pitch: 190px horizontal for 130px-wide nodes, ~110px empty
    corridor between rows, so horizontal runs happen in open space.
  * jumpStyle=arc, so where two edges do cross, the crossing reads clearly.

Pages:
  1. Genealogy            — parent_of / born_from, layered top-down
  2. Deeds & domains      — killed / rules / wields / bears / guards / loved
  3. Greek ↔ Roman        — the 21 equivalent_to pairs + Janus (no counterpart)
  4. Scenario 1 explained — why the set intersection drops Hades
  5. Governance model     — actions ← roles → sensitivity tiers
  6. Full graph           — everything at once; dense by nature, kept for
                            reference (apply Arrange → Layout → Organic)

Open at https://app.diagrams.net (File → Open) or with the VS Code
Draw.io Integration extension. Plain, uncompressed XML.
"""
from __future__ import annotations

import os
import re
import sys
from xml.sax.saxutils import escape

import networkx as nx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mythos.graph import KnowledgeGraph  # noqa: E402
from mythos import governance as gov      # noqa: E402

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "diagrams")
OUT_FILE = os.path.join(OUT_DIR, "mythos_graph.drawio")

NODE_W, NODE_H = 130, 40
PITCH_X, LAYER_DY = 190, 150

# --- styling ------------------------------------------------------------------
NODE_STYLE = {
    "Primordial": "fillColor=#E1D5E7;strokeColor=#9673A6",
    "Titan":      "fillColor=#FFE6CC;strokeColor=#D79B00",
    "Olympian":   "fillColor=#FFF2CC;strokeColor=#D6B656;fontStyle=1",
    "God":        "fillColor=#DAE8FC;strokeColor=#6C8EBF",
    "Hero":       "fillColor=#D5E8D4;strokeColor=#82B366",
    "Mortal":     "fillColor=#F5F5F5;strokeColor=#999999",
    "Nymph":      "fillColor=#F5F5F5;strokeColor=#999999",
    "Monster":    "fillColor=#F8CECC;strokeColor=#B85450",
    "Place":      "fillColor=#EEEEEE;strokeColor=#808080",
    "Artifact":   "fillColor=#FFFFCC;strokeColor=#999900",
    "RomanDeity": "fillColor=#B0E3E6;strokeColor=#0E8088",
    "Group":      "fillColor=#FFFFFF;strokeColor=#666666;dashed=1;fontStyle=1",
    "Unknown":    "fillColor=#FFFFFF;strokeColor=#B3B3B3",
}
BASE_NODE = "rounded=1;whiteSpace=wrap;html=1;fontSize=12;"

EDGE_COLOR = {
    "parent_of":     "strokeColor=#9E9E9E",
    "born_from":     "strokeColor=#9673A6;dashed=1",
    "equivalent_to": "strokeColor=#0E8088;dashed=1;strokeWidth=2",
    "member_of":     "strokeColor=#6C8EBF;dashed=1;dashPattern=1 3",
    "killed":        "strokeColor=#B85450;strokeWidth=2",
    "rules":         "strokeColor=#D79B00",
    "wields":        "strokeColor=#D79B00",
    "bears":         "strokeColor=#D79B00",
    "guards":        "strokeColor=#D79B00",
    "loved":         "strokeColor=#CC66CC",
}
BASE_EDGE = ("edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;endArrow=block;endFill=1;"
             "fontSize=10;labelBackgroundColor=#FFFFFF;jumpStyle=arc;jumpSize=6;")

# explicit anchors — the key to keeping arrows out of the blocks
DOWN  = "exitX=0.5;exitY=1;exitDx=0;exitDy=0;entryX=0.5;entryY=0;entryDx=0;entryDy=0;"
UP    = "exitX=0.5;exitY=0;exitDx=0;exitDy=0;entryX=0.5;entryY=1;entryDx=0;entryDy=0;"
RIGHT = "exitX=1;exitY=0.5;exitDx=0;exitDy=0;entryX=0;entryY=0.5;entryDx=0;entryDy=0;"
LEFT  = "exitX=0;exitY=0.5;exitDx=0;exitDy=0;entryX=1;entryY=0.5;entryDx=0;entryDy=0;"

DEED_RELS = ("killed", "rules", "wields", "bears", "guards", "loved")


def sid(name: str) -> str:
    return "n_" + re.sub(r"[^A-Za-z0-9]", "_", name)


class Page:
    def __init__(self, name: str, width: int = 1600, height: int = 1200) -> None:
        self.name, self.width, self.height = name, width, height
        self.cells: list[str] = []
        self._n = 0

    def node(self, node_id: str, label: str, x: int, y: int, style: str,
             w: int = NODE_W, h: int = NODE_H) -> None:
        self.cells.append(
            f'        <mxCell id="{node_id}" value="{escape(label)}" style="{style}" '
            f'vertex="1" parent="1">\n'
            f'          <mxGeometry x="{int(x)}" y="{int(y)}" width="{w}" height="{h}" as="geometry"/>\n'
            f'        </mxCell>')

    def edge(self, src: str, dst: str, style: str, label: str = "",
             points: list[tuple[float, float]] | None = None) -> None:
        self._n += 1
        if points:
            pts = "\n".join(f'            <mxPoint x="{int(x)}" y="{int(y)}"/>'
                            for x, y in points)
            geo = ('          <mxGeometry relative="1" as="geometry">\n'
                   f'            <Array as="points">\n{pts}\n            </Array>\n'
                   '          </mxGeometry>')
        else:
            geo = '          <mxGeometry relative="1" as="geometry"/>'
        self.cells.append(
            f'        <mxCell id="e{self._n}" value="{escape(label)}" style="{style}" '
            f'edge="1" parent="1" source="{src}" target="{dst}">\n{geo}\n'
            f'        </mxCell>')

    def text(self, label: str, x: int, y: int, w: int = 520, h: int = 26,
             size: int = 13, bold: bool = True, align: str = "left") -> None:
        self._n += 1
        st = (f"text;html=1;strokeColor=none;fillColor=none;align={align};"
              f"verticalAlign=middle;fontSize={size};fontStyle={1 if bold else 0};")
        self.cells.append(
            f'        <mxCell id="t{self._n}" value="{escape(label)}" style="{st}" '
            f'vertex="1" parent="1">\n'
            f'          <mxGeometry x="{int(x)}" y="{int(y)}" width="{w}" height="{h}" as="geometry"/>\n'
            f'        </mxCell>')

    def box(self, label: str, x: int, y: int, w: int, h: int, style: str) -> None:
        self._n += 1
        self.cells.append(
            f'        <mxCell id="b{self._n}" value="{escape(label)}" style="{style}" '
            f'vertex="1" parent="1">\n'
            f'          <mxGeometry x="{int(x)}" y="{int(y)}" width="{w}" height="{h}" as="geometry"/>\n'
            f'        </mxCell>')

    def xml(self, idx: int) -> str:
        return (f'  <diagram id="page{idx}" name="{escape(self.name)}">\n'
                f'    <mxGraphModel dx="1422" dy="800" grid="1" gridSize="10" guides="1" '
                f'tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" '
                f'pageWidth="{self.width}" pageHeight="{self.height}" math="0" shadow="0">\n'
                f'      <root>\n        <mxCell id="0"/>\n        <mxCell id="1" parent="0"/>\n'
                + "\n".join(self.cells)
                + f'\n      </root>\n    </mxGraphModel>\n  </diagram>')


def nstyle(kg: KnowledgeGraph, n: str) -> str:
    return BASE_NODE + NODE_STYLE.get(kg.node_type(n), NODE_STYLE["Unknown"]) + ";"


# --- layering -----------------------------------------------------------------
def genealogy_dag(kg: KnowledgeGraph) -> nx.DiGraph:
    """parent → child DAG (born_from is stored child → parent, so reverse it)."""
    D = nx.DiGraph()
    for u, v, k in kg.g.edges(keys=True):
        if k == "parent_of":
            D.add_edge(u, v)
        elif k == "born_from":
            D.add_edge(v, u)
    return D


def layered(D: nx.DiGraph) -> list[list[str]]:
    """Topological generations, then pull parentless nodes down beside their
    children so edges span one layer instead of several."""
    layer = {}
    for i, gen in enumerate(nx.topological_generations(D)):
        for n in gen:
            layer[n] = i
    for n in list(D.nodes):
        if D.in_degree(n) == 0:
            kids = list(D.successors(n))
            if kids:
                layer[n] = min(layer[k] for k in kids) - 1
    lo = min(layer.values())
    layer = {n: l - lo for n, l in layer.items()}
    out: list[list[str]] = [[] for _ in range(max(layer.values()) + 1)]
    for n, l in sorted(layer.items()):
        out[l].append(n)
    return out


def barycentre(layers: list[list[str]], D: nx.DiGraph, passes: int = 4) -> None:
    """Reorder within layers to cut edge crossings (in place)."""
    for p in range(passes):
        rng = range(1, len(layers)) if p % 2 == 0 else range(len(layers) - 2, -1, -1)
        for i in rng:
            ref = {n: j for j, n in enumerate(layers[i - 1 if p % 2 == 0 else i + 1])}
            nbrs = D.predecessors if p % 2 == 0 else D.successors

            def key(n: str) -> tuple[float, str]:
                xs = [ref[m] for m in nbrs(n) if m in ref]
                return (sum(xs) / len(xs) if xs else 1e6, n)

            layers[i].sort(key=key)


def place_layers(page: Page, kg: KnowledgeGraph, layers: list[list[str]],
                 y0: int = 110, band_labels: bool = False) -> dict[str, tuple[float, float]]:
    widest = max(len(l) for l in layers)
    total_w = widest * PITCH_X
    pos: dict[str, tuple[float, float]] = {}
    for i, row in enumerate(layers):
        y = y0 + i * LAYER_DY
        offset = (total_w - len(row) * PITCH_X) / 2 + 40
        for j, n in enumerate(row):
            x = offset + j * PITCH_X
            page.node(sid(n), n, x, y, nstyle(kg, n))
            pos[n] = (x, y)
        if band_labels:
            page.text(f"gen {i}", 8, y + 8, w=60, h=22, size=10, bold=False)
    return pos


def free_lanes(row_xs: list[float]) -> list[float]:
    """Mid-points of the horizontal gaps in a row, plus the two side margins —
    the x positions where a vertical edge segment can pass without clipping a block."""
    if not row_xs:
        return []
    xs = sorted(row_xs)
    lanes = [xs[0] - 55]
    for a, b in zip(xs, xs[1:]):
        if b - (a + NODE_W) >= 24:
            lanes.append((a + NODE_W + b) / 2)
    lanes.append(xs[-1] + NODE_W + 55)
    return lanes


def pick_lane(candidates: list[float], blocked_rows: list[list[float]],
              prefer_x: float, usage: dict[float, int]) -> float:
    """Choose a lane that clips no block in any intermediate row, close to the
    straight-line path, and least-used so parallel long edges fan out."""
    def clear(c: float) -> bool:
        return all(not any(x - 8 <= c <= x + NODE_W + 8 for x in row) for row in blocked_rows)

    ok = [c for c in candidates if clear(c)] or candidates
    ok.sort(key=lambda c: abs(c - prefer_x))
    best = min(ok[:6], key=lambda c: (usage.get(c, 0), abs(c - prefer_x)))
    usage[best] = usage.get(best, 0) + 1
    return best


# --- Page 1: genealogy --------------------------------------------------------
def page_genealogy(kg: KnowledgeGraph) -> Page:
    D = genealogy_dag(kg)
    layers = layered(D)
    barycentre(layers, D)
    widest = max(len(l) for l in layers)
    p = Page("1 · Genealogy", width=widest * PITCH_X + 160,
             height=len(layers) * LAYER_DY + 220)
    p.text("Divine genealogy — parent_of (grey) · born_from (dashed purple)", 40, 24,
           w=900, size=16)
    p.text("Layered by topological generation; arrows exit the bottom of a parent and "
           "enter the top of a child, travelling only in the empty corridor between rows.",
           40, 50, w=1400, size=11, bold=False)
    pos = place_layers(p, kg, layers, y0=110, band_labels=True)
    lay = {n: i for i, row in enumerate(layers) for n in row}
    row_xs = [[pos[n][0] for n in row] for row in layers]
    usage: dict[float, int] = {}

    # parent → child, using the stored direction of each relation
    rels = [(u, v, k) if k == "parent_of" else (v, u, k)
            for u, v, k in kg.g.edges(keys=True) if k in ("parent_of", "born_from")]

    for parent, child, k in sorted(rels, key=lambda e: (lay[e[0]], e[0], e[1])):
        style = BASE_EDGE + DOWN + EDGE_COLOR[k] + ";"
        span = lay[child] - lay[parent]
        if span <= 1:
            p.edge(sid(parent), sid(child), style)
            continue
        # long edge: hop through a lane that is free in every row it crosses
        px, py = pos[parent]
        cx, cy = pos[child]
        mid_rows = list(range(lay[parent] + 1, lay[child]))
        cands = sorted({c for r in mid_rows for c in free_lanes(row_xs[r])})
        lane = pick_lane(cands, [row_xs[r] for r in mid_rows],
                         (px + cx) / 2 + NODE_W / 2, usage)
        p.edge(sid(parent), sid(child), style,
               points=[(lane, py + NODE_H + 45), (lane, cy - 45)])
    return p


# --- Page 2: deeds & domains --------------------------------------------------
def page_deeds(kg: KnowledgeGraph) -> Page:
    edges = [(u, v, k) for u, v, k in kg.g.edges(keys=True) if k in DEED_RELS]
    actors = sorted({u for u, _, _ in edges})
    objects = [v for _, v, _ in edges]
    # order objects by their actor's row, so edges stay short and parallel
    a_idx = {a: i for i, a in enumerate(actors)}
    seen, ordered_objs = set(), []
    for v in sorted(set(objects), key=lambda v: (min(a_idx[u] for u, vv, _ in edges if vv == v), v)):
        if v not in seen:
            seen.add(v); ordered_objs.append(v)

    row_h = 70
    p = Page("2 · Deeds & domains", width=1000,
             height=max(len(actors), len(ordered_objs)) * row_h + 220)
    p.text("Deeds & domains — killed (red) · rules / wields / bears / guards (amber) · loved (pink)",
           40, 24, w=900, size=16)
    p.text("Two columns, one edge family: every arrow runs right→left across an empty "
           "gutter, so nothing crosses a block.", 40, 50, w=900, size=11, bold=False)
    p.text("ACTOR", 60, 86, w=200, size=11)
    p.text("TARGET", 700, 86, w=200, size=11)

    ypos = {}
    for i, a in enumerate(actors):
        y = 116 + i * row_h
        p.node(sid(a), a, 60, y, nstyle(kg, a)); ypos[a] = y
    for i, v in enumerate(ordered_objs):
        y = 116 + i * row_h
        p.node(sid(v), v, 700, y, nstyle(kg, v))
    for u, v, k in sorted(edges, key=lambda e: (a_idx[e[0]], e[1])):
        p.edge(sid(u), sid(v), BASE_EDGE + RIGHT + EDGE_COLOR[k] + ";", label=k)
    return p


# --- Page 3: Greek ↔ Roman ----------------------------------------------------
def page_parallels(kg: KnowledgeGraph) -> Page:
    pairs = kg.parallels()
    p = Page("3 · Greek ↔ Roman", width=900, height=200 + len(pairs) * 56)
    p.text("Cross-pantheon links (interpretatio romana) — one equivalent_to edge each",
           40, 24, w=860, size=16)
    p.text("Paired rows: each arrow is a short straight hop across the gutter.",
           40, 50, w=860, size=11, bold=False)
    p.text("GREEK", 120, 86, w=200, size=11)
    p.text("ROMAN", 560, 86, w=200, size=11)
    y = 116
    for greek, roman in pairs:
        p.node(sid(greek), greek, 100, y, nstyle(kg, greek))
        p.node(sid(roman), roman, 560, y, nstyle(kg, roman))
        p.edge(sid(greek), sid(roman), BASE_EDGE + RIGHT + EDGE_COLOR["equivalent_to"] + ";")
        y += 56
    p.node(sid("Janus"), "Janus", 560, y + 16, nstyle(kg, "Janus"))
    p.box("no Greek counterpart recorded\n(the graph can represent absence)",
          100, y + 8, 380, 56,
          "rounded=1;whiteSpace=wrap;html=1;fillColor=#FFF2CC;strokeColor=#D6B656;"
          "dashed=1;fontSize=11;align=center;")
    return p


# --- Page 4: scenario 1 explained --------------------------------------------
def page_scenario1(kg: KnowledgeGraph) -> Page:
    p = Page("4 · Scenario 1 explained", width=1300, height=820)
    p.text("Scenario 1 — “Which of the Twelve Olympians are children of Cronus and Rhea?”",
           40, 24, w=1200, size=16)
    p.text("RAG returns all six children. The graph intersects three sets — and Hades drops out.",
           40, 50, w=1200, size=12, bold=False)

    kids = ["Zeus", "Hera", "Poseidon", "Demeter", "Hestia", "Hades"]
    x0, pitch = 90, 190
    # parents centred over the children they point to
    p.node(sid("Cronus"), "Cronus", x0 + 1.1 * pitch, 120, nstyle(kg, "Cronus"))
    p.node(sid("Rhea"), "Rhea", x0 + 3.1 * pitch, 120, nstyle(kg, "Rhea"))

    for i, k in enumerate(kids):
        st = nstyle(kg, k)
        if k == "Hades":
            st = BASE_NODE + "fillColor=#F8CECC;strokeColor=#B85450;strokeWidth=3;fontStyle=1;"
        p.node(sid(k), k, x0 + i * pitch, 330, st)
        p.edge(sid("Cronus"), sid(k), BASE_EDGE + DOWN + EDGE_COLOR["parent_of"] + ";")
        p.edge(sid("Rhea"), sid(k), BASE_EDGE + DOWN + EDGE_COLOR["parent_of"] + ";")

    p.node("grp_olymp", "Twelve Olympians", x0 + 1.6 * pitch, 560,
           BASE_NODE + NODE_STYLE["Group"] + ";", w=220, h=44)
    for k in kids[:-1]:
        p.edge("grp_olymp", sid(k), BASE_EDGE + UP + EDGE_COLOR["member_of"] + ";")

    p.box("Hades has no member_of edge →\nexcluded by the intersection, not by luck",
          x0 + 4.15 * pitch, 552, 340, 60,
          "rounded=1;whiteSpace=wrap;html=1;fillColor=#F8CECC;strokeColor=#B85450;"
          "fontSize=11;align=center;")
    p.box("children_of(Cronus) ∩ children_of(Rhea) ∩ members(Twelve Olympians)\n"
          "=  Zeus, Hera, Poseidon, Demeter, Hestia",
          90, 690, 1120, 70,
          "rounded=1;whiteSpace=wrap;html=1;fillColor=#D5E8D4;strokeColor=#82B366;"
          "fontSize=13;align=center;fontStyle=1;")
    return p


# --- Page 5: governance -------------------------------------------------------
def page_governance() -> Page:
    """Actions ← ROLES → Tiers. Mirroring the two edge families around the role
    column means neither ever crosses the other's territory."""
    roles = ["mortal", "initiate", "hero", "god", "admin"]
    tiers = ["public", "restricted", "secret"]
    actions = sorted(gov.ACTION_PERMISSIONS)

    p = Page("5 · Governance model", width=1300, height=880)
    p.text("Governance — enforced by the ontology layer, not the model's goodwill",
           40, 24, w=1200, size=16)
    p.text("Roles read only the tiers they are cleared for (right), and may invoke only the "
           "actions granted to them (left).", 40, 50, w=1200, size=12, bold=False)

    p.text("GOVERNED ACTION", 60, 92, w=240, size=11)
    p.text("ROLE", 590, 92, w=200, size=11)
    p.text("SENSITIVITY TIER", 1000, 92, w=240, size=11)

    rstyle = BASE_NODE + "fillColor=#DAE8FC;strokeColor=#6C8EBF;fontStyle=1;"
    tstyle = {"public":     BASE_NODE + "fillColor=#D5E8D4;strokeColor=#82B366;",
              "restricted": BASE_NODE + "fillColor=#FFF2CC;strokeColor=#D6B656;",
              "secret":     BASE_NODE + "fillColor=#F8CECC;strokeColor=#B85450;fontStyle=1;"}
    astyle = BASE_NODE + "fillColor=#E1D5E7;strokeColor=#9673A6;"

    for i, a in enumerate(actions):
        p.node("act_" + a, a, 60, 130 + i * 110, astyle, w=180)
    for i, r in enumerate(roles):
        p.node("role_" + r, r, 590, 130 + i * 110, rstyle, w=150)
    for i, t in enumerate(tiers):
        p.node("tier_" + t, t, 1010, 185 + i * 165, tstyle[t], w=160)

    for r in roles:
        for t in sorted(gov.TIER_ACCESS.get(r, set())):
            p.edge("role_" + r, "tier_" + t,
                   BASE_EDGE + RIGHT + "strokeColor=#6C8EBF;dashed=1;endArrow=open;")
    for a, allowed in gov.ACTION_PERMISSIONS.items():
        for r in sorted(allowed):
            p.edge("role_" + r, "act_" + a,
                   BASE_EDGE + LEFT + "strokeColor=#9673A6;endArrow=open;opacity=70;")

    p.box("Object-type gating: slay_monster requires target type = Monster; bless requires "
          "Hero/Mortal.\nEvery invocation — allowed or denied — is written to the audit log.",
          60, 770, 1160, 70,
          "rounded=1;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;"
          "fontSize=12;align=center;")
    return p


# --- Page 6: full graph (dense reference) ------------------------------------
def page_full(kg: KnowledgeGraph) -> Page:
    ROWS = [("Primordial",), ("Titan",), ("Olympian",), ("God",),
            ("Nymph", "Mortal"), ("Hero",), ("Monster",),
            ("Place", "Artifact"), ("RomanDeity",), ("Group",)]
    per_line = 12
    p = Page("6 · Full graph (dense)", width=per_line * PITCH_X + 200, height=2100)
    p.text("Full graph — all 105 nodes and 142 edges, banded by entity type", 40, 24,
           w=1200, size=16)
    p.text("Ten relation families on one canvas cannot be laid out without crossings — this "
           "page is a reference. For a readable view use pages 1–5, or select all here and "
           "apply Arrange → Layout → Organic.", 40, 50, w=1600, size=11, bold=False)
    y = 120
    for types in ROWS:
        members = sorted(n for n in kg.g.nodes if kg.node_type(n) in types)
        if not members:
            continue
        p.text(" / ".join(types).upper(), 10, y - 30, w=300, h=22, size=10)
        for i, n in enumerate(members):
            line, col = divmod(i, per_line)
            p.node(sid(n), n, 60 + col * PITCH_X, y + line * (NODE_H + 24), nstyle(kg, n))
        y += ((len(members) - 1) // per_line + 1) * (NODE_H + 24) + 110
    for u, v, k in kg.g.edges(keys=True):
        p.edge(sid(u), sid(v), BASE_EDGE + EDGE_COLOR.get(k, "strokeColor=#B3B3B3") + ";")
    return p


def main() -> None:
    kg = KnowledgeGraph()
    os.makedirs(OUT_DIR, exist_ok=True)
    pages = [page_genealogy(kg), page_deeds(kg), page_parallels(kg),
             page_scenario1(kg), page_governance(), page_full(kg)]
    xml = (f'<mxfile host="app.diagrams.net" type="device" pages="{len(pages)}">\n'
           + "\n".join(pg.xml(i + 1) for i, pg in enumerate(pages))
           + "\n</mxfile>\n")
    with open(OUT_FILE, "w", encoding="utf-8") as fh:
        fh.write(xml)
    print(f"Wrote {OUT_FILE}  ({len(xml):,} bytes)")
    for pg in pages:
        print(f"  {pg.name:32} {pg.width}×{pg.height}")


if __name__ == "__main__":
    main()
