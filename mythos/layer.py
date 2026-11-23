"""
OntologyLayer: the single interface the enforced agent is allowed to touch.

It never hands back raw graph internals. Every method returns grounded,
provenance-carrying results, and every access decision is made here, not by the
agent. In a production system this is exactly what you would expose as an MCP
server: a small set of typed, governed tools over the knowledge graph.
"""
from __future__ import annotations

from .graph import KnowledgeGraph
from . import governance as gov
from .data import SOURCES


def cite(source_id: str) -> str:
    s = SOURCES.get(source_id)
    if not s:
        return source_id
    who = f"{s['author']}, {s['title']}"
    return f"{who} (Gutenberg #{s['gutenberg']})" if s.get("gutenberg") else who


class OntologyLayer:
    def __init__(self, kg: KnowledgeGraph | None = None) -> None:
        self.kg = kg or KnowledgeGraph()
        self.audit = gov.AuditLog()

    # -- grounding: relational set query --------------------------------------
    def olympians_children_of(self, parent_a: str, parent_b: str) -> dict:
        a = self.kg.resolve(parent_a); b = self.kg.resolve(parent_b)
        if not a or not b:
            return {"answer": [], "note": "Unknown ancestor(s).", "citations": []}
        both = self.kg.children_of(a) & self.kg.children_of(b)
        olympians = self.kg.members("Twelve Olympians")
        result = sorted(both & olympians)
        excluded = sorted(both - olympians)
        return {
            "answer": result,
            "excluded_because_not_olympian": excluded,
            "note": (f"Intersected children_of({a}) ∩ children_of({b}) ∩ "
                     f"members(Twelve Olympians)."),
            "citations": [cite("theogony"), cite("berens")],
        }

    # -- 2-hop relational join ------------------------------------------------
    def who_killed_children_of(self, parent: str) -> dict:
        p = self.kg.resolve(parent)
        if not p:
            return {"answer": [], "note": "Unknown figure."}
        results = []
        for child in sorted(self.kg.children_of(p)):
            for k in self.kg.killers_of(child):
                results.append({"slayer": k["killer"], "victim": child,
                                "source": cite(k["source"])})
        return {"answer": results,
                "note": f"Joined children_of({p}) → killed_by. {len(results)} hit(s)."}

    # -- aggregation / counting -----------------------------------------------
    def count_olympian_children_of(self, parent: str) -> dict:
        p = self.kg.resolve(parent)
        if not p:
            return {"count": 0, "who": [], "note": "Unknown figure."}
        who = sorted(self.kg.children_of(p) & self.kg.members("Twelve Olympians"))
        return {"count": len(who), "who": who,
                "note": f"|children_of({p}) ∩ Twelve Olympians|",
                "citations": [cite("theogony"), cite("berens")]}

    # -- typed filtering ------------------------------------------------------
    def children_of_type(self, parent: str, node_type: str) -> dict:
        p = self.kg.resolve(parent)
        if not p:
            return {"answer": [], "note": "Unknown figure."}
        who = sorted(c for c in self.kg.children_of(p) if self.kg.node_type(c) == node_type)
        return {"answer": who,
                "note": f"children_of({p}) filtered to type '{node_type}'."}

    # -- grounded fact-check --------------------------------------------------
    def verify_parentage(self, child: str, claimed_parent: str) -> dict:
        c = self.kg.resolve(child); cp = self.kg.resolve(claimed_parent)
        if not c or not cp:
            return {"verdict": "unknown", "note": "Unknown figure(s)."}
        attested = self.kg.parents_of(c)
        match = [a for a in attested if a["parent"] == cp]
        others = [a for a in attested if a["parent"] != cp]
        if match:
            verdict = "supported"
            note = f"Attested by {cite(match[0]['source'])} (trust {match[0]['trust']:.2f})."
            if others:
                alt = ", ".join(f"{o['parent']} — {cite(o['source'])}" for o in others)
                note += f" But other traditions are recorded: {alt}."
        else:
            verdict = "unsupported"
            known = ", ".join(f"{a['parent']} ({cite(a['source'])})" for a in attested) or "none recorded"
            note = f"No source links {cp} to {c}. Recorded parent(s): {known}."
        return {"verdict": verdict, "child": c, "claimed_parent": cp, "note": note}

    # -- provenance: conflicting sources, ranked ------------------------------
    def parents(self, name: str) -> dict:
        n = self.kg.resolve(name)
        if not n:
            return {"subject": name, "claims": [], "note": "Unknown figure."}
        claims = []
        for p in self.kg.parents_of(n):
            claims.append({
                "parent": p["parent"], "relation": p["relation"],
                "source": cite(p["source"]), "trust": p["trust"],
            })
        note = ("Multiple traditions attested; ranked by trust."
                if len({c["source"] for c in claims}) > 1 else "Single tradition.")
        return {"subject": n, "claims": claims, "note": note}

    # -- cross-pantheon parallels ---------------------------------------------
    def counterpart(self, name: str) -> dict:
        n = self.kg.resolve(name)
        if not n:
            return {"subject": name, "counterparts": [], "note": "Unknown figure."}
        cps = [{"name": c["name"], "pantheon": c["pantheon"], "source": cite(c["source"])}
               for c in self.kg.counterparts(n)]
        note = (f"No cross-pantheon counterpart recorded for {n}."
                if not cps else f"{n} ({self.kg.pantheon(n)}) ↔ cross-pantheon equivalent(s).")
        return {"subject": n, "pantheon": self.kg.pantheon(n),
                "counterparts": cps, "note": note}

    def alignment(self) -> dict:
        pairs = self.kg.parallels()
        matched = {r for _, r in pairs} | {g for g, _ in pairs}
        roman_only = sorted(n for n in self.kg.g.nodes
                            if self.kg.pantheon(n) == "roman" and n not in matched)
        return {"pairs": pairs, "roman_only": roman_only,
                "note": "Greek↔Roman equivalences (interpretatio romana)."}

    # -- governed knowledge access --------------------------------------------
    def describe(self, name: str, role: str) -> dict:
        n = self.kg.resolve(name)
        if not n:
            return {"subject": name, "facts": [], "withheld": 0}
        visible, withheld = [], 0
        for f in self.kg.facts(n):
            if gov.may_read(role, f["tier"]):
                visible.append({"predicate": f["predicate"], "value": f["value"],
                                "tier": f["tier"], "source": cite(f["source"])})
            else:
                withheld += 1
        return {"subject": n, "type": self.kg.node_type(n),
                "facts": visible, "withheld": withheld}

    def get_sensitive_fact(self, name: str, predicate: str, role: str) -> gov.Decision:
        """Direct request for one fact — enforced by tier."""
        n = self.kg.resolve(name)
        if not n:
            return gov.Decision(False, f"Unknown figure '{name}'.")
        for f in self.kg.facts(n):
            if f["predicate"] == predicate:
                if gov.may_read(role, f["tier"]):
                    return gov.Decision(True, "Permitted.",
                                        {"value": f["value"], "tier": f["tier"],
                                         "source": cite(f["source"])})
                return gov.Decision(
                    False,
                    f"'{predicate}' of {n} is {f['tier'].upper()} knowledge; "
                    f"role '{role}' is not cleared for it.")
        return gov.Decision(False, f"No such fact '{predicate}' for {n}.")

    # -- governed actions ------------------------------------------------------
    def list_actions(self, role: str) -> list[str]:
        return sorted(a for a, roles in gov.ACTION_PERMISSIONS.items() if role in roles)

    def invoke(self, role: str, action: str, target: str) -> gov.Decision:
        n = self.kg.resolve(target)
        target_type = self.kg.node_type(n) if n else None
        decision = gov.check_action(role, action, target_type)
        if decision.allowed:
            decision.payload = {"effect": self._narrate(action, n or target)}
        self.audit.record(role, action, n or target, decision)
        return decision

    @staticmethod
    def _narrate(action: str, target: str) -> str:
        return {
            "smite": f"A thunderbolt strikes {target}.",
            "bless": f"{target} is blessed with divine favour.",
            "slay_monster": f"{target} is slain; the land is freed of it.",
            "consult_oracle": f"The Oracle murmurs concerning {target}.",
            "reveal_mystery": f"The rite of {target} is disclosed.",
        }.get(action, f"{action} performed on {target}.")
