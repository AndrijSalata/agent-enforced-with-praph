"""
LLM backends.

The prototype runs OFFLINE by default with a deterministic rule-based router
(MockBackend) so a live demo never depends on a network call or an API key.
Set AGENT_LLM=anthropic (and ANTHROPIC_API_KEY) to route intent parsing through
a real model instead — the enforced agent's *guarantees do not change*, because
grounding and governance are enforced by the ontology layer, not the model.

A "route" turns a natural-language question into a structured intent:
    {"intent": "olympian_children", "a": "Cronus", "b": "Rhea"}
    {"intent": "parents", "name": "Aphrodite"}
    {"intent": "sensitive_fact", "name": "Achilles", "predicate": "fatal_weakness"}
    {"intent": "action", "action": "smite", "target": "Heracles"}
    {"intent": "describe", "name": "Zeus"}
    {"intent": "unknown"}
"""
from __future__ import annotations

import os
import re


def _names_in(question: str, known_names: list[str]) -> list[str]:
    """Return known entity names appearing in the question, in order."""
    found = []
    low = question.lower()
    for name in sorted(known_names, key=len, reverse=True):
        if re.search(rf"\b{re.escape(name.lower())}\b", low):
            found.append((low.index(name.lower()), name))
    # de-dupe preserving first appearance, then order by position
    seen, ordered = set(), []
    for pos, name in sorted(found):
        if name not in seen:
            seen.add(name); ordered.append(name)
    return ordered


class MockBackend:
    name = "mock (offline, deterministic)"

    TYPE_WORDS = {"hero": "Hero", "heroes": "Hero", "monster": "Monster",
                  "monsters": "Monster", "titan": "Titan", "titans": "Titan"}

    def route(self, question: str, known_names: list[str]) -> dict:
        q = question.lower()
        names = _names_in(question, known_names)
        is_question = q.strip().startswith(
            ("who", "which", "what", "how", "is ", "was", "did", "does", "are", "verify"))

        # --- grounded fact-check: "Was X the daughter/son of Y?" -------------
        if (q.startswith(("was", "is ", "did", "verify", "is it true")) and len(names) >= 2
                and any(w in q for w in ("son", "daughter", "child", "born", "parent"))):
            return {"intent": "verify", "child": names[0], "claimed": names[1]}

        # --- aggregation: "How many Olympians are children of X?" ------------
        if q.startswith("how many") and ("olympian" in q) and names:
            return {"intent": "count_olympian_children", "name": names[0]}

        # --- 2-hop join: "Who killed a child of X?" -------------------------
        if is_question and ("child" in q) and any(w in q for w in ("kill", "killed", "slay", "slew")):
            return {"intent": "killed_children_of", "name": names[0] if names else None}

        # --- typed filtering: "Which heroes are sons of X?" -----------------
        type_hit = next((t for w, t in self.TYPE_WORDS.items() if re.search(rf"\b{w}\b", q)), None)
        if is_question and type_hit and names and any(w in q for w in ("son", "sons", "child", "children", "of", "daughter")):
            return {"intent": "children_of_type", "name": names[0], "node_type": type_hit}

        # --- cross-pantheon parallels --------------------------------------
        if any(w in q for w in ("counterpart", "equivalent", "roman", "greek version",
                                "parallel", "same as", "interpretatio")):
            return {"intent": "counterpart", "name": names[0]} if names else {"intent": "alignment"}

        # --- governed actions (imperative only, never a question) ----------
        if not is_question:
            if any(w in q for w in ("smite", "strike down")):
                return {"intent": "action", "action": "smite", "target": names[0] if names else None}
            if any(w in q for w in ("slay", "kill", "defeat")):
                return {"intent": "action", "action": "slay_monster", "target": names[0] if names else None}
            if "bless" in q:
                return {"intent": "action", "action": "bless", "target": names[0] if names else None}

        # --- governed knowledge --------------------------------------------
        if "weakness" in q or "vulnerab" in q or "achilles heel" in q:
            return {"intent": "sensitive_fact", "name": names[0] if names else None,
                    "predicate": "fatal_weakness"}
        if "mystery" in q or "mysteries" in q:
            return {"intent": "sensitive_fact", "name": names[0] if names else "Eleusis",
                    "predicate": "mystery_rite"}

        # --- provenance / genealogy ----------------------------------------
        if ("olympian" in q) and ("child" in q or "children of" in q):
            if len(names) >= 2:
                return {"intent": "olympian_children", "a": names[0], "b": names[1]}
            if names:
                return {"intent": "olympian_children", "a": names[0], "b": names[0]}
        if any(w in q for w in ("parent", "parents", "mother", "father", "born")):
            return {"intent": "parents", "name": names[0] if names else None}

        if names:
            return {"intent": "describe", "name": names[0]}
        return {"intent": "unknown"}


class AnthropicBackend:
    """Optional real-LLM router. Falls back to MockBackend on any problem."""
    name = "anthropic (real model)"

    def __init__(self, model: str = "claude-sonnet-5") -> None:
        self.model = model
        self._fallback = MockBackend()
        try:
            import anthropic  # noqa: F401
            self._client = anthropic.Anthropic()
            self._ready = bool(os.environ.get("ANTHROPIC_API_KEY"))
        except Exception:
            self._ready = False

    def route(self, question: str, known_names: list[str]) -> dict:
        if not self._ready:
            return self._fallback.route(question, known_names)
        import json
        system = (
            "You convert a question about Greek mythology into a JSON intent. "
            "Allowed intents: olympian_children{a,b}, parents{name}, "
            "sensitive_fact{name,predicate}, action{action,target}, "
            "describe{name}, unknown. Use only entity names from this list: "
            + ", ".join(known_names) + ". Reply with JSON only."
        )
        try:
            msg = self._client.messages.create(
                model=self.model, max_tokens=200, system=system,
                messages=[{"role": "user", "content": question}],
            )
            text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
            return json.loads(text[text.index("{"): text.rindex("}") + 1])
        except Exception:
            return self._fallback.route(question, known_names)


def get_backend() -> "MockBackend | AnthropicBackend":
    if os.environ.get("AGENT_LLM", "mock").lower() == "anthropic":
        return AnthropicBackend()
    return MockBackend()
