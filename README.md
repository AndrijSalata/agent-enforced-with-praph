# agent-enforced-with-graph

A tiny, runnable prototype for a conference talk on **giving any AI agent a
Genie-style ontology/context layer** — vendor-neutral, no warehouse required.

The demo puts two agents side by side over the same Greek-mythology knowledge:

- a **naive agent** — flat keyword retrieval over public-domain source texts
  (what a plain RAG index or loose LLM recall gives you), and
- an **enforced agent** — every answer and every action routed through a
  **knowledge graph + governance layer**.

Same myths, same questions. The graph adds the two things a model can't
guarantee on its own: **grounding** (correct, cited answers) and **governance**
(who is allowed to know — and do — what).

```
python demo.py
```

## Why a graph? (the talk's thesis in ten scenarios)

`python demo.py` runs all ten side by side: **RAG** (flat retrieval over the
corpus) vs **RAG + Graph** (retrieval grounded and governed by the knowledge
graph). Each scenario isolates one capability the graph adds.

| # | Capability | Question | RAG-only fails because… |
|---|-----------|----------|--------------------------|
| 1 | Multi-hop set intersection | *Which of the Twelve Olympians are children of Cronus & Rhea?* | can't intersect sets → wrongly includes Hades |
| 2 | 2-hop relational join | *Who killed a child of Typhon?* | can't chain children_of → killed_by |
| 3 | Aggregation / counting | *How many Olympians are children of Zeus?* | can't enumerate/count a set |
| 4 | Typed filtering | *Which heroes are sons of Zeus?* | has no entity types to filter on |
| 5 | Provenance, ranked | *Who are the parents of Aphrodite?* | commits to one tradition, uncited |
| 6 | Grounded fact-check | *Was Aphrodite the daughter of Zeus?* | gives an unsupported yes/no |
| 7 | Cross-source linking | *Roman counterpart of Hephaestus?* (+ full alignment) | the link isn't in the text |
| 8 | Known-unknowns / absence | *Greek counterpart of Janus?* | hallucinates a lookalike (Venus) |
| 9 | Governed knowledge + redaction | *Achilles' fatal weakness* (mortal vs god) | leaks the secret to anyone |
| 10 | Governed action, role + type gated | *Smite / Slay*, by role & target type | has no permission model |

Scenarios **1–4** are *reasoning* (set logic, joins, aggregation, typing);
**5–6** are *trust* (provenance, verification); **7–8** are *cross-source
linking and knowing what it doesn't know*; **9–10** are *governance* (access and
actions enforced by the layer, not the model's goodwill). Every answer carries a
source; every action is audited.

## Diagrams (draw.io)

```bash
python scripts/export_drawio.py     # → diagrams/mythos_graph.drawio
```

Plain uncompressed XML, six pages — open at [app.diagrams.net](https://app.diagrams.net)
(File → Open) or with the VS Code *Draw.io Integration* extension:

| Page | What it shows |
|------|---------------|
| 1 · Genealogy | `parent_of` / `born_from`, layered by topological generation |
| 2 · Deeds & domains | `killed` / `rules` / `wields` / `bears` / `guards` / `loved`, two columns |
| 3 · Greek ↔ Roman | the 21 `equivalent_to` pairs, plus Janus with *no* counterpart |
| 4 · Scenario 1 explained | why the set intersection drops Hades — the teaching slide |
| 5 · Governance model | actions ← roles → sensitivity tiers |
| 6 · Full graph | everything at once; dense by nature, kept for reference |

Nodes are coloured by type (Olympian gold, Titan orange, Monster red, Roman
teal, …) and edges by relation (`equivalent_to` dashed teal, `killed` red,
`member_of` dotted blue).

**Why the arrows stay clear of the blocks.** Pages 1–5 each carry a *single
relation family*, so edges never pile up; every edge gets explicit exit/entry
anchors (bottom→top or right→left) instead of leaving the route to draw.io;
genealogy is laid out by topological generation with parentless nodes pulled
down beside their children, which makes 68 of 81 edges span a single row; and
the 13 edges that must cross an intermediate row are given explicit waypoints
through a lane verified to be free of any block. Crossings that remain are drawn
with `jumpStyle=arc` so they read cleanly. Page 6 is the exception — ten relation
families on one canvas can't be untangled, so select all and apply
*Arrange → Layout → Organic* if you need it.

## The blueprint this maps to

The prototype is a minimal instance of a vendor-neutral context layer:

1. **Entity & relationship graph** — `mythos/data.py`, `mythos/graph.py`
2. **Trusted definitions / typed queries** — `OntologyLayer` methods (`mythos/layer.py`)
3. **Provenance & trust ranking** — every edge/fact cites a source with a trust score
4. **Access control** — sensitivity tiers + role permissions (`mythos/governance.py`)
5. **Governed actions + audit** — `invoke()` with an audit log
6. **A small, governed interface** the agent must go through — in production this
   is exactly what you'd expose as an **MCP server**.

## Layout

```
mythos/
  data.py         # curated graph: nodes, typed edges, facts — each with source + trust + sensitivity
  graph.py        # NetworkX graph + typed traversals (children_of, members, parents_of, …)
  governance.py   # roles, tier access, action permissions, audit log
  layer.py        # OntologyLayer — the only interface the enforced agent may touch
agent/
  backends.py     # offline deterministic router (default) | optional real Anthropic model
  naive_agent.py  # flat keyword retrieval baseline (no graph, no governance)
  enforced_agent.py
data/
  corpus/         # public-domain source texts (Project Gutenberg) — see SOURCES.md
  kb/             # flat_notes.md (naive index) + exported mythos_graph.json
scripts/
  fetch_corpus.py # download the FULL source books locally
demo.py           # side-by-side, four scenarios + audit log
tests/            # asserts enforced = correct & safe where naive = wrong & leaky
```

## Run it

```bash
pip install -r requirements.txt      # just networkx
python demo.py                       # the side-by-side demo
python -m pytest -q                  # or: python tests/test_enforcement.py
python scripts/fetch_corpus.py       # (optional) pull the complete source texts
```

**Optional — use a real model** for intent parsing (guarantees are unchanged,
since enforcement lives in the layer):

```bash
pip install anthropic
export ANTHROPIC_API_KEY=...    # Windows: set ANTHROPIC_API_KEY=...
export AGENT_LLM=anthropic
python demo.py
```

## Data & sources

All knowledge derives from public-domain texts on **Project Gutenberg**
(Hesiod's *Theogony*, Berens, Bulfinch, Guerber, Ovid). Full list, links, and
usage in [`data/corpus/SOURCES.md`](data/corpus/SOURCES.md). Excerpts are
committed; `scripts/fetch_corpus.py` fetches the complete works.

## Honest framing (not a strawman)

The naive baseline retrieves real text perfectly well. What it lacks is
structure and policy: it cannot do relational set operations, reconcile
conflicting sources, or enforce access. Those three capabilities are the entire
value of the graph layer — which is the point worth making on stage.
