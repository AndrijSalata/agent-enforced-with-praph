"""
Governance: the "enforced" half of the prototype.

Two things are enforced, both driven by the graph — never by the LLM's goodwill:

  1. Knowledge access. Every fact has a sensitivity tier (public / restricted /
     secret). A caller's role determines which tiers it may read. Secret facts
     (a hero's fatal weakness, the hidden entrance to the Underworld) are simply
     never returned to a mortal.

  2. Actions. The agent can *do* things (consult the Oracle, slay a monster,
     smite a foe). Each action is gated by role AND by the type of its target
     object (you can only slay something that is actually a Monster). Every
     invocation is written to an audit log.

This mirrors the Palantir-style principle: agents query typed objects and invoke
*governed actions*, rather than touching raw data or calling arbitrary tools.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

# Which sensitivity tiers each role may read.
TIER_ACCESS = {
    "mortal":   {"public"},
    "initiate": {"public", "restricted"},
    "hero":     {"public"},
    "god":      {"public", "restricted", "secret"},
    "admin":    {"public", "restricted", "secret"},
}

# Which actions each role may invoke.
ACTION_PERMISSIONS = {
    "consult_oracle": {"mortal", "initiate", "hero", "god", "admin"},
    "reveal_mystery": {"initiate", "god", "admin"},
    "slay_monster":   {"hero", "god", "admin"},
    "smite":          {"god", "admin"},
    "bless":          {"god", "admin"},
}

# Some actions require the target to be of a particular object type.
ACTION_TARGET_TYPE = {
    "slay_monster": {"Monster"},
    "smite":        {"Hero", "Mortal", "Monster", "Titan", "God"},
    "bless":        {"Hero", "Mortal"},
}


@dataclass
class Decision:
    allowed: bool
    reason: str
    payload: dict | None = None


@dataclass
class AuditLog:
    entries: list[dict] = field(default_factory=list)

    def record(self, role: str, action: str, target: str, decision: Decision) -> None:
        self.entries.append({
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "role": role, "action": action, "target": target,
            "allowed": decision.allowed, "reason": decision.reason,
        })


def may_read(role: str, tier: str) -> bool:
    return tier in TIER_ACCESS.get(role, set())


def check_action(role: str, action: str, target_type: str | None) -> Decision:
    if action not in ACTION_PERMISSIONS:
        return Decision(False, f"Unknown action '{action}'.")
    if role not in ACTION_PERMISSIONS[action]:
        allowed_roles = ", ".join(sorted(ACTION_PERMISSIONS[action]))
        return Decision(False, f"Role '{role}' may not invoke '{action}' (requires: {allowed_roles}).")
    required = ACTION_TARGET_TYPE.get(action)
    if required is not None and target_type not in required:
        return Decision(False,
                        f"'{action}' requires a target of type {sorted(required)}, "
                        f"but target is of type '{target_type}'.")
    return Decision(True, "Permitted.")
