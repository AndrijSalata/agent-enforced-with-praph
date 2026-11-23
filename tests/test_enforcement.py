"""
Verification: the graph-enforced agent is correct and safe where the naive one
is wrong and leaky. Run:  python -m pytest -q   (or: python tests/test_enforcement.py)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mythos.layer import OntologyLayer
from agent.naive_agent import NaiveAgent
from agent.enforced_agent import EnforcedAgent


def _setup():
    layer = OntologyLayer()
    return layer, NaiveAgent(), EnforcedAgent(layer=layer)


def test_grounding_multihop():
    _, naive, enforced = _setup()
    q = "Which of the Twelve Olympians are children of Cronus and Rhea?"
    e = enforced.answer(q)
    assert set(e["answer"]) == {"Zeus", "Hera", "Poseidon", "Demeter", "Hestia"}
    assert "Hades" in e["excluded"]              # correctly filtered out
    # The naive baseline over-answers: it surfaces Hades as if he qualified.
    assert "hades" in naive.answer(q)["answer"].lower()


def test_provenance_conflicting_sources():
    _, _, enforced = _setup()
    e = enforced.answer("Who are the parents of Aphrodite?")
    parents = {c["parent"] for c in e["answer"]}
    sources = {c["source"] for c in e["answer"]}
    assert {"Uranus", "Zeus", "Dione"} <= parents   # both traditions present
    assert len(sources) >= 2                          # more than one attesting source
    # ranked by trust (descending)
    trusts = [c["trust"] for c in e["answer"]]
    assert trusts == sorted(trusts, reverse=True)


def test_governance_secret_knowledge():
    layer, naive, enforced = _setup()
    q = "What is Achilles' fatal weakness?"
    assert enforced.answer(q, role="mortal")["allowed"] is False   # denied
    god = enforced.answer(q, role="god")
    assert god["allowed"] is True and "heel" in god["answer"].lower()
    # naive leaks it regardless of role
    assert "heel" in naive.answer(q, role="mortal")["answer"].lower()


def test_governance_actions():
    layer, _, enforced = _setup()
    assert enforced.answer("Smite Heracles.", role="mortal")["allowed"] is False
    assert enforced.answer("Smite Heracles.", role="god")["allowed"] is True
    # object-type gating: you can only slay something that is a Monster
    assert enforced.answer("Slay the Hydra.", role="hero")["allowed"] is True
    assert enforced.answer("Slay Zeus.", role="hero")["allowed"] is False
    # audit captured every attempt
    assert len(layer.audit.entries) >= 4


def test_two_hop_join():
    _, _, enforced = _setup()
    e = enforced.answer("Who killed a child of Typhon?")
    pairs = {(r["slayer"], r["victim"]) for r in e["answer"]}
    assert ("Heracles", "Hydra") in pairs
    assert ("Bellerophon", "Chimera") in pairs


def test_aggregation_count():
    _, _, enforced = _setup()
    e = enforced.answer("How many of the Twelve Olympians are children of Zeus?")
    assert e["count"] == len(e["answer"]) >= 5
    assert "Athena" in e["answer"] and "Hades" not in e["answer"]


def test_typed_filter():
    _, _, enforced = _setup()
    e = enforced.answer("Which heroes are sons of Zeus?")
    assert set(e["answer"]) == {"Heracles", "Perseus"}


def test_factcheck_verdict():
    _, _, enforced = _setup()
    yes = enforced.answer("Was Aphrodite the daughter of Zeus?")
    assert yes["verdict"] == "supported" and "tradition" in yes["note"].lower()
    no = enforced.answer("Was Perseus the son of Poseidon?")
    assert no["verdict"] == "unsupported"


def test_redaction():
    _, _, enforced = _setup()
    mortal = enforced.answer("Tell me everything about Achilles", role="mortal")
    assert mortal["withheld"] >= 1
    assert all(f["tier"] == "public" for f in mortal["answer"])
    god = enforced.answer("Tell me everything about Achilles", role="god")
    assert god["withheld"] == 0


def test_cross_pantheon_counterpart():
    layer, naive, enforced = _setup()
    # Works in both directions and across less-obvious pairs.
    e = enforced.answer("Who is the Roman counterpart of Hephaestus?")
    assert [c["name"] for c in e["answer"]] == ["Vulcan"]
    back = enforced.answer("What is the Greek equivalent of Neptune?")
    assert [c["name"] for c in back["answer"]] == ["Poseidon"]
    # Alignment enumerates all pairs and flags uniquely-Roman gods.
    align = enforced.answer("Show the parallels between Greek and Roman pantheons.")
    assert len(align["answer"]) >= 20
    assert "Janus" in align["roman_only"]


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn(); print(f"PASS  {name}")
    print("All checks passed.")
