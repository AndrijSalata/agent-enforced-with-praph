"""
EnforcedAgent: every answer and every action goes through the OntologyLayer.

The agent's job is only to (1) parse the question into an intent and (2) call
the right governed method with the caller's role. It is structurally incapable
of reaching around the layer to the raw data, and it never decides access for
itself — the layer does. Swap the mock router for a real LLM and these
guarantees are unchanged.
"""
from __future__ import annotations

from mythos.layer import OntologyLayer
from mythos.data import NODES
from .backends import get_backend


class EnforcedAgent:
    def __init__(self, layer: OntologyLayer | None = None, backend=None) -> None:
        self.layer = layer or OntologyLayer()
        self.backend = backend or get_backend()
        # Individuals only (exclude Group nodes) for name extraction.
        self.known_names = [n for n, t in NODES if t != "Group"]

    def answer(self, question: str, role: str = "mortal") -> dict:
        intent = self.backend.route(question, self.known_names)
        kind = intent.get("intent")

        if kind == "olympian_children":
            r = self.layer.olympians_children_of(intent["a"], intent["b"])
            return {"agent": "enforced", "role": role, "kind": kind,
                    "answer": r["answer"],
                    "excluded": r.get("excluded_because_not_olympian", []),
                    "note": r["note"], "citations": r["citations"]}

        if kind == "parents":
            r = self.layer.parents(intent.get("name") or "")
            return {"agent": "enforced", "role": role, "kind": kind,
                    "answer": r["claims"], "note": r["note"], "subject": r["subject"]}

        if kind == "killed_children_of":
            r = self.layer.who_killed_children_of(intent.get("name") or "")
            return {"agent": "enforced", "role": role, "kind": kind,
                    "answer": r["answer"], "note": r["note"]}

        if kind == "count_olympian_children":
            r = self.layer.count_olympian_children_of(intent.get("name") or "")
            return {"agent": "enforced", "role": role, "kind": kind,
                    "count": r["count"], "answer": r["who"], "note": r["note"],
                    "citations": r.get("citations", [])}

        if kind == "children_of_type":
            r = self.layer.children_of_type(intent.get("name") or "", intent.get("node_type") or "")
            return {"agent": "enforced", "role": role, "kind": kind,
                    "answer": r["answer"], "note": r["note"]}

        if kind == "verify":
            r = self.layer.verify_parentage(intent.get("child") or "", intent.get("claimed") or "")
            return {"agent": "enforced", "role": role, "kind": kind,
                    "verdict": r.get("verdict"), "note": r["note"]}

        if kind == "counterpart":
            r = self.layer.counterpart(intent.get("name") or "")
            return {"agent": "enforced", "role": role, "kind": kind,
                    "subject": r["subject"], "pantheon": r.get("pantheon"),
                    "answer": r["counterparts"], "note": r["note"]}

        if kind == "alignment":
            r = self.layer.alignment()
            return {"agent": "enforced", "role": role, "kind": kind,
                    "answer": r["pairs"], "roman_only": r["roman_only"], "note": r["note"]}

        if kind == "sensitive_fact":
            d = self.layer.get_sensitive_fact(intent.get("name") or "",
                                              intent.get("predicate") or "", role)
            return {"agent": "enforced", "role": role, "kind": kind,
                    "allowed": d.allowed, "answer": (d.payload or {}).get("value"),
                    "reason": d.reason, "citation": (d.payload or {}).get("source")}

        if kind == "action":
            d = self.layer.invoke(role, intent["action"], intent.get("target") or "")
            return {"agent": "enforced", "role": role, "kind": kind,
                    "action": intent["action"], "target": intent.get("target"),
                    "allowed": d.allowed,
                    "answer": (d.payload or {}).get("effect") if d.allowed else None,
                    "reason": d.reason}

        if kind == "describe":
            r = self.layer.describe(intent.get("name") or "", role)
            return {"agent": "enforced", "role": role, "kind": kind,
                    "subject": r["subject"], "type": r.get("type"),
                    "answer": r["facts"], "withheld": r["withheld"]}

        return {"agent": "enforced", "role": role, "kind": "unknown",
                "answer": None, "reason": "Could not map the question to a governed query."}
