"""
Side-by-side demo: Agent with RAG (flat retrieval) vs. Agent with RAG + Graph.

Ten scenarios, each isolating ONE capability the knowledge graph adds on top of
plain retrieval — grounding, joins, aggregation, typed filtering, provenance,
fact-checking, cross-source linking, known-unknowns, governed knowledge, and
governed actions.

    python demo.py
"""
from __future__ import annotations

import os

from mythos.layer import OntologyLayer
from mythos.graph import KnowledgeGraph
from agent.naive_agent import NaiveAgent
from agent.enforced_agent import EnforcedAgent

LINE = "=" * 78


def hdr(n: int, cap: str, q: str) -> None:
    print("\n" + LINE + f"\n{n:>2}) {cap}\n    Q: “{q}”\n" + LINE)


def rag(agent: NaiveAgent, q: str, role: str = "mortal") -> None:
    print(f"  RAG       : {agent.answer(q, role=role)['answer']}")


def graph(a: dict) -> None:
    k = a.get("kind")
    if k == "olympian_children":
        print(f"  RAG+GRAPH : {', '.join(a['answer'])}")
        if a["excluded"]:
            print(f"              (excluded — not among the Twelve: {', '.join(a['excluded'])})")
        print(f"              ↳ {a['note']}")
    elif k == "killed_children_of":
        for r in a["answer"]:
            print(f"  RAG+GRAPH : {r['slayer']} killed {r['victim']}  — {r['source']}")
        print(f"              ↳ {a['note']}")
    elif k == "count_olympian_children":
        print(f"  RAG+GRAPH : {a['count']}  ({', '.join(a['answer'])})")
        print(f"              ↳ {a['note']}")
    elif k == "children_of_type":
        print(f"  RAG+GRAPH : {', '.join(a['answer'])}")
        print(f"              ↳ {a['note']}")
    elif k == "parents":
        for c in a["answer"]:
            rel = "born from" if c["relation"] == "born_from" else "child of"
            print(f"  RAG+GRAPH : {rel} {c['parent']:<8} [trust {c['trust']:.2f}] — {c['source']}")
        print(f"              ↳ {a['note']}")
    elif k == "verify":
        print(f"  RAG+GRAPH : {a['verdict'].upper()} — {a['note']}")
    elif k == "counterpart":
        if a["answer"]:
            for c in a["answer"]:
                print(f"  RAG+GRAPH : {a['subject']} ({a['pantheon']}) ↔ {c['name']} ({c['pantheon']}) — {c['source']}")
        else:
            print(f"  RAG+GRAPH : {a['note']}")
    elif k == "alignment":
        pairs = "  ".join(f"{g}={r}" for g, r in a["answer"][:6])
        print(f"  RAG+GRAPH : {len(a['answer'])} parallels, e.g. {pairs} …")
        if a["roman_only"]:
            print(f"              uniquely Roman (no Greek counterpart): {', '.join(a['roman_only'])}")
    elif k == "sensitive_fact":
        if a["allowed"]:
            print(f"  RAG+GRAPH : {a['answer']}   — {a['citation']}")
        else:
            print(f"  RAG+GRAPH : ⛔ DENIED — {a['reason']}")
    elif k == "describe":
        if a["answer"]:
            for f in a["answer"]:
                print(f"  RAG+GRAPH : [{f['tier']}] {f['predicate']}: {f['value']}  — {f['source']}")
        if a["withheld"]:
            print(f"              🔒 {a['withheld']} fact(s) withheld from role '{a['role']}'.")
        if not a["answer"] and not a["withheld"]:
            print("  RAG+GRAPH : (nothing recorded)")
    elif k == "action":
        print(f"  RAG+GRAPH : {'⚡ ' + a['answer'] if a['allowed'] else '⛔ DENIED — ' + a['reason']}")
    else:
        print(f"  RAG+GRAPH : {a['answer']}")


def main() -> None:
    layer = OntologyLayer()
    rag_agent = NaiveAgent()
    ga = EnforcedAgent(layer=layer)

    os.makedirs(os.path.join("data", "kb"), exist_ok=True)
    KnowledgeGraph().export_json(os.path.join("data", "kb", "mythos_graph.json"))
    print("Backend:", ga.backend.name)
    print("Knowledge graph:", layer.kg.stats())
    print("\nLegend:  RAG = flat retrieval over the corpus  ·  "
          "RAG+GRAPH = retrieval grounded & governed by the knowledge graph")

    # 1 — multi-hop set intersection
    q = "Which of the Twelve Olympians are children of Cronus and Rhea?"
    hdr(1, "GROUNDING · multi-hop set intersection", q)
    rag(rag_agent, q); graph(ga.answer(q))
    print("  DELTA     : RAG returns all six children (incl. Hades, not an Olympian). "
          "The graph intersects sets → correct.")

    # 2 — 2-hop relational join
    q = "Who killed a child of Typhon?"
    hdr(2, "REASONING · 2-hop relational join", q)
    rag(rag_agent, q); graph(ga.answer(q))
    print("  DELTA     : chaining children_of → killed_by is a graph traversal RAG can't do.")

    # 3 — aggregation / counting
    q = "How many of the Twelve Olympians are children of Zeus?"
    hdr(3, "AGGREGATION · counting over a set", q)
    rag(rag_agent, q); graph(ga.answer(q))
    print("  DELTA     : counting requires enumerating a set; retrieval can only quote text.")

    # 4 — typed filtering
    q = "Which heroes are sons of Zeus?"
    hdr(4, "TYPED FILTERING · constrain by entity type", q)
    rag(rag_agent, q); graph(ga.answer(q))
    print("  DELTA     : the graph filters children_of(Zeus) to type=Hero. RAG has no types.")

    # 5 — provenance, ranked
    q = "Who are the parents of Aphrodite?"
    hdr(5, "PROVENANCE · rank conflicting sources", q)
    rag(rag_agent, q); graph(ga.answer(q))
    print("  DELTA     : two traditions attested. RAG commits to one, uncited; graph ranks both.")

    # 6 — grounded fact-check
    q = "Was Aphrodite the daughter of Zeus?"
    hdr(6, "FACT-CHECK · grounded verification", q)
    rag(rag_agent, q); graph(ga.answer(q))
    print("  DELTA     : graph gives a sourced verdict AND flags the competing tradition.")

    # 7 — cross-source linking
    q = "Who is the Roman counterpart of Hephaestus?"
    hdr(7, "CROSS-SOURCE · link two pantheons", q)
    rag(rag_agent, q); graph(ga.answer(q))
    q2 = "Show the parallels between the Greek and Roman pantheons."
    graph(ga.answer(q2))
    print("  DELTA     : the Vulcan↔Hephaestus link isn't in the text; the graph traverses it.")

    # 8 — known-unknowns / absence
    q = "What is the Greek counterpart of Janus?"
    hdr(8, "KNOWN-UNKNOWNS · represent absence", q)
    rag(rag_agent, q); graph(ga.answer(q))
    print("  DELTA     : Janus has no Greek equivalent. RAG grabs a lookalike; the graph says so.")

    # 9 — governed knowledge + redaction
    q = "What is Achilles' fatal weakness?"
    hdr(9, "GOVERNANCE (knowledge) · clearance + redaction", q)
    print("  — asked by a MORTAL —")
    rag(rag_agent, q, role="mortal"); graph(ga.answer(q, role="mortal"))
    print("  — asked by a GOD —")
    graph(ga.answer(q, role="god"))
    print("  — “Tell me everything about Achilles” (MORTAL) —")
    graph(ga.answer("Tell me everything about Achilles", role="mortal"))
    print("  DELTA     : RAG leaks the secret to anyone; the graph gates by clearance and redacts.")

    # 10 — governed action, role + type gated
    q = "Smite Heracles."
    hdr(10, "GOVERNANCE (action) · role + object-type gating", q)
    print("  — attempted by a MORTAL —")
    print("  RAG       : (no permission model) … it would just narrate the act.")
    graph(ga.answer(q, role="mortal"))
    print("  — attempted by a GOD —")
    graph(ga.answer(q, role="god"))
    print("  — “Slay Zeus.” by a HERO (type check) —")
    graph(ga.answer("Slay Zeus.", role="hero"))
    print("  — “Slay the Hydra.” by a HERO —")
    graph(ga.answer("Slay the Hydra.", role="hero"))
    print("  DELTA     : actions are gated by role AND target type, and every attempt is audited.")

    hdr(0, "AUDIT LOG", "every governed action, allowed or denied")
    for e in layer.audit.entries:
        print(f"  {'✓' if e['allowed'] else '✗'} role={e['role']:<7} {e['action']}({e['target']}) — {e['reason']}")

    print("\n" + LINE)
    print("Same corpus, same questions. The graph adds what retrieval alone can't guarantee:")
    print("correct multi-hop reasoning, ranked provenance, cross-source links, and enforced")
    print("access. RAG finds text; RAG + graph reasons, cites, and obeys the rules.")
    print(LINE)


if __name__ == "__main__":
    main()
