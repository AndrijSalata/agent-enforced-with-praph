"""
NaiveAgent: the baseline. Flat keyword retrieval over the corpus, no graph.

It models what you get from a plain RAG index (or an LLM answering from loose
recall): it can fetch relevant text, but it cannot perform relational set
operations, reconcile conflicting sources, or enforce who is allowed to know
what. So it will confidently:
  * over-answer a multi-hop question (returns *all* children of Cronus & Rhea,
    unable to filter to "the Twelve Olympians" — wrongly including Hades),
  * commit to a single origin story where two are attested,
  * and happily reveal a secret to anyone who asks.
"""
from __future__ import annotations

import os
import re

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_chunks() -> list[str]:
    chunks: list[str] = []
    notes = os.path.join(_HERE, "data", "kb", "flat_notes.md")
    if os.path.exists(notes):
        for line in open(notes, encoding="utf-8"):
            line = line.strip()
            if line.startswith("- "):
                chunks.append(line[2:])
    return chunks


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z]+", text.lower()))


class NaiveAgent:
    def __init__(self) -> None:
        self.chunks = _load_chunks()

    def _retrieve(self, question: str, k: int = 1) -> list[str]:
        q = _tokens(question) - {"the", "of", "are", "who", "what", "is", "which", "and", "a"}
        scored = [(len(q & _tokens(c)), c) for c in self.chunks]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [c for s, c in scored[:k] if s > 0]

    def answer(self, question: str, role: str = "mortal") -> dict:
        # Note: `role` is accepted but IGNORED — the naive agent has no notion
        # of governance. That is precisely the point.
        hits = self._retrieve(question, k=1)
        text = hits[0] if hits else "I'm not sure."
        return {"agent": "naive", "role_ignored": role,
                "answer": text, "retrieved": hits}
