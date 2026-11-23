"""
KnowledgeGraph: loads the curated data into a NetworkX directed multigraph and
exposes typed traversal queries the ontology layer needs.

The point of the graph (vs. flat text): relational questions become precise set
operations over edges, and every answer carries its provenance.
"""
from __future__ import annotations

import json
from typing import Iterable

import networkx as nx

from . import data


class KnowledgeGraph:
    def __init__(self) -> None:
        self.g = nx.MultiDiGraph()
        self._build()

    def _build(self) -> None:
        for node_id, node_type in data.NODES:
            pantheon = "roman" if node_type == "RomanDeity" else "greek"
            self.g.add_node(node_id, type=node_type, pantheon=pantheon)
        for src, rel, dst, source_id, trust in data.EDGES:
            # Tolerate edges that reference nodes not explicitly listed.
            for n in (src, dst):
                if n not in self.g:
                    self.g.add_node(n, type="Unknown")
            self.g.add_edge(src, dst, key=rel, rel=rel, source=source_id, trust=trust)
        # Attribute facts are stored on the subject node under "facts".
        for subj, pred, val, source_id, trust, tier in data.FACTS:
            if subj not in self.g:
                self.g.add_node(subj, type="Unknown")
            self.g.nodes[subj].setdefault("facts", []).append(
                {"predicate": pred, "value": val, "source": source_id,
                 "trust": trust, "tier": tier}
            )

    # --- basic accessors ------------------------------------------------------
    def has(self, node_id: str) -> bool:
        return node_id in self.g

    def node_type(self, node_id: str) -> str:
        return self.g.nodes[node_id].get("type", "Unknown") if node_id in self.g else "Unknown"

    def resolve(self, name: str) -> str | None:
        """Case-insensitive node lookup by exact name."""
        if name in self.g:
            return name
        low = name.strip().lower()
        for n in self.g.nodes:
            if n.lower() == low:
                return n
        return None

    # --- typed traversals -----------------------------------------------------
    def children_of(self, parent: str) -> set[str]:
        return {v for _, v, k in self.g.out_edges(parent, keys=True) if k == "parent_of"}

    def parents_of(self, child: str) -> list[dict]:
        """All attested origins of `child`, each with source + trust.

        Covers two edge conventions: ``X parent_of child`` (incoming) and
        ``child born_from X`` (outgoing), the latter used for origin myths such
        as Aphrodite rising from the foam of Uranus.
        """
        out = []
        for u, v, k, d in self.g.in_edges(child, keys=True, data=True):
            if k == "parent_of":
                out.append({"parent": u, "relation": k,
                            "source": d["source"], "trust": d["trust"]})
        for u, v, k, d in self.g.out_edges(child, keys=True, data=True):
            if k == "born_from":
                out.append({"parent": v, "relation": k,
                            "source": d["source"], "trust": d["trust"]})
        return sorted(out, key=lambda r: r["trust"], reverse=True)

    def members(self, group: str) -> set[str]:
        return {v for _, v, k in self.g.out_edges(group, keys=True) if k == "member_of"}

    def killers_of(self, victim: str) -> list[dict]:
        return [{"killer": u, "source": d["source"], "trust": d["trust"]}
                for u, v, k, d in self.g.in_edges(victim, keys=True, data=True) if k == "killed"]

    def counterparts(self, name: str) -> list[dict]:
        """Cross-pantheon equivalents via ``equivalent_to`` edges (either direction)."""
        out = []
        for u, v, k, d in self.g.out_edges(name, keys=True, data=True):
            if k == "equivalent_to":
                out.append({"name": v, "pantheon": self.g.nodes[v].get("pantheon"),
                            "source": d["source"], "trust": d["trust"]})
        for u, v, k, d in self.g.in_edges(name, keys=True, data=True):
            if k == "equivalent_to":
                out.append({"name": u, "pantheon": self.g.nodes[u].get("pantheon"),
                            "source": d["source"], "trust": d["trust"]})
        return out

    def parallels(self) -> list[tuple[str, str]]:
        """All Greek↔Roman pairs, as (greek, roman)."""
        pairs = []
        for u, v, k in self.g.edges(keys=True):
            if k == "equivalent_to":
                pairs.append((u, v))
        return sorted(pairs)

    def pantheon(self, node_id: str) -> str:
        return self.g.nodes.get(node_id, {}).get("pantheon", "greek")

    def relation(self, subject: str, rel: str) -> list[dict]:
        return [{"target": v, "source": d["source"], "trust": d["trust"]}
                for _, v, k, d in self.g.out_edges(subject, keys=True, data=True) if k == rel]

    def facts(self, subject: str) -> list[dict]:
        return list(self.g.nodes.get(subject, {}).get("facts", []))

    def neighbors_summary(self, node_id: str) -> list[str]:
        """Human-readable one-hop context for a node (used for grounding)."""
        lines = []
        for _, v, k, d in self.g.out_edges(node_id, keys=True, data=True):
            lines.append(f"{node_id} {k} {v}")
        for u, _, k, d in self.g.in_edges(node_id, keys=True, data=True):
            lines.append(f"{u} {k} {node_id}")
        return lines

    # --- introspection --------------------------------------------------------
    def stats(self) -> dict:
        rels: dict[str, int] = {}
        for _, _, k in self.g.edges(keys=True):
            rels[k] = rels.get(k, 0) + 1
        return {"nodes": self.g.number_of_nodes(),
                "edges": self.g.number_of_edges(),
                "relations": rels}

    def export_json(self, path: str) -> None:
        payload = {
            "sources": data.SOURCES,
            "nodes": [{"id": n, "type": self.g.nodes[n].get("type"),
                       "pantheon": self.g.nodes[n].get("pantheon")} for n in self.g.nodes],
            "edges": [{"src": u, "rel": k, "dst": v, "source": d["source"], "trust": d["trust"]}
                      for u, v, k, d in self.g.edges(keys=True, data=True)],
            "facts": [{"subject": s, **f} for s in self.g.nodes for f in self.facts(s)],
        }
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)
