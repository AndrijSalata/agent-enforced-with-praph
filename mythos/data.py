"""
Curated Greek-mythology knowledge graph.

This is the *structured* knowledge the enforced agent reasons over. Every edge
and fact carries provenance (which public-domain source attests it) and a trust
score, plus a sensitivity tier used by the governance layer.

The raw source texts themselves live in ``data/corpus/`` (downloaded from
Project Gutenberg). Those texts are what the *naive* agent does flat keyword
retrieval over — see ``agent/naive_agent.py``. The contrast between the two is
the whole point of the demo.

Design note (so the demo is not a strawman): the naive baseline can retrieve
text just fine. What it cannot do is (1) perform relational set operations,
(2) reconcile and rank conflicting sources, or (3) enforce access policy.
Those three capabilities are exactly what this structured, governed graph adds.
"""

# --- Provenance registry: source_id -> bibliographic record -------------------
SOURCES = {
    "theogony":   {"title": "Theogony",                              "author": "Hesiod",            "gutenberg": 348},
    "iliad":      {"title": "Iliad",                                 "author": "Homer",             "gutenberg": None},
    "odyssey":    {"title": "Odyssey",                               "author": "Homer",             "gutenberg": None},
    "berens":     {"title": "Myths and Legends of Ancient Greece and Rome", "author": "E. M. Berens", "gutenberg": 22381},
    "bulfinch":   {"title": "The Age of Fable",                      "author": "Thomas Bulfinch",   "gutenberg": 3327},
    "guerber":    {"title": "Myths of Greece and Rome",              "author": "H. A. Guerber",     "gutenberg": 39250},
    "ovid":       {"title": "Metamorphoses",                         "author": "Ovid",              "gutenberg": 21765},
    "apollodorus":{"title": "Bibliotheca (The Library)",            "author": "Apollodorus",       "gutenberg": None},
}

# --- Nodes: (id, type) --------------------------------------------------------
# types: Primordial, Titan, Olympian, God, Hero, Mortal, Monster, Place,
#        Artifact, Group, Nymph
NODES = [
    # Primordials
    ("Chaos", "Primordial"), ("Gaia", "Primordial"), ("Uranus", "Primordial"),
    ("Pontus", "Primordial"), ("Tartarus", "Primordial"), ("Nyx", "Primordial"),
    ("Erebus", "Primordial"),
    # Titans
    ("Cronus", "Titan"), ("Rhea", "Titan"), ("Oceanus", "Titan"), ("Tethys", "Titan"),
    ("Hyperion", "Titan"), ("Theia", "Titan"), ("Coeus", "Titan"), ("Phoebe", "Titan"),
    ("Iapetus", "Titan"), ("Themis", "Titan"), ("Mnemosyne", "Titan"), ("Crius", "Titan"),
    ("Prometheus", "Titan"), ("Epimetheus", "Titan"), ("Atlas", "Titan"), ("Leto", "Titan"),
    ("Metis", "Titan"),
    # Twelve Olympians
    ("Zeus", "Olympian"), ("Hera", "Olympian"), ("Poseidon", "Olympian"),
    ("Demeter", "Olympian"), ("Hestia", "Olympian"), ("Athena", "Olympian"),
    ("Apollo", "Olympian"), ("Artemis", "Olympian"), ("Ares", "Olympian"),
    ("Aphrodite", "Olympian"), ("Hephaestus", "Olympian"), ("Hermes", "Olympian"),
    # Other gods (not counted among the Twelve)
    ("Hades", "God"), ("Persephone", "God"), ("Dionysus", "God"), ("Eros", "God"),
    ("Helios", "God"), ("Selene", "God"), ("Eos", "God"), ("Hebe", "God"),
    ("Dione", "God"),
    # Nymphs / consorts / mortals of note
    ("Maia", "Nymph"), ("Semele", "Mortal"), ("Alcmene", "Mortal"), ("Danae", "Mortal"),
    ("Peleus", "Mortal"), ("Thetis", "Nymph"), ("Daphne", "Nymph"),
    # Heroes
    ("Heracles", "Hero"), ("Perseus", "Hero"), ("Achilles", "Hero"),
    ("Theseus", "Hero"), ("Bellerophon", "Hero"), ("Oedipus", "Hero"),
    ("Odysseus", "Hero"), ("Jason", "Hero"),
    # Monsters
    ("Typhon", "Monster"), ("Echidna", "Monster"), ("Medusa", "Monster"),
    ("Hydra", "Monster"), ("Cerberus", "Monster"), ("Minotaur", "Monster"),
    ("Chimera", "Monster"), ("Sphinx", "Monster"), ("Pegasus", "Monster"),
    # Places
    ("Mount Olympus", "Place"), ("Underworld", "Place"), ("Eleusis", "Place"),
    ("Crete", "Place"), ("Troy", "Place"),
    # Artifacts
    ("Thunderbolt", "Artifact"), ("Trident", "Artifact"), ("Aegis", "Artifact"),
    ("Winged Sandals", "Artifact"), ("Caduceus", "Artifact"), ("Golden Fleece", "Artifact"),
    # Groups
    ("Twelve Olympians", "Group"), ("Titans", "Group"), ("Primordials", "Group"),
]

# --- Edges: (src, rel, dst, source_id, trust) ---------------------------------
# rels: parent_of, born_from, member_of, rules, wields, bears, killed, guards,
#       transformed_into, loved
EDGES = [
    # Primordial genealogy (Hesiod, Theogony)
    ("Chaos", "parent_of", "Nyx", "theogony", 0.9),
    ("Chaos", "parent_of", "Erebus", "theogony", 0.9),
    ("Gaia", "parent_of", "Uranus", "theogony", 0.95),
    ("Gaia", "parent_of", "Pontus", "theogony", 0.9),

    # Titans, children of Gaia + Uranus
    *[("Gaia", "parent_of", t, "theogony", 0.9) for t in
      ["Cronus", "Rhea", "Oceanus", "Tethys", "Hyperion", "Theia", "Coeus",
       "Phoebe", "Iapetus", "Themis", "Mnemosyne", "Crius"]],
    *[("Uranus", "parent_of", t, "theogony", 0.9) for t in
      ["Cronus", "Rhea", "Oceanus", "Tethys", "Hyperion", "Theia", "Coeus",
       "Phoebe", "Iapetus", "Themis", "Mnemosyne", "Crius"]],

    # Children of the Titans
    ("Iapetus", "parent_of", "Prometheus", "theogony", 0.9),
    ("Iapetus", "parent_of", "Epimetheus", "theogony", 0.9),
    ("Iapetus", "parent_of", "Atlas", "theogony", 0.9),
    ("Coeus", "parent_of", "Leto", "theogony", 0.9),
    ("Phoebe", "parent_of", "Leto", "theogony", 0.9),
    ("Hyperion", "parent_of", "Helios", "theogony", 0.9),
    ("Hyperion", "parent_of", "Selene", "theogony", 0.9),
    ("Hyperion", "parent_of", "Eos", "theogony", 0.9),
    ("Theia", "parent_of", "Helios", "theogony", 0.9),

    # The six children of Cronus and Rhea (Hesiod, Theogony)
    *[("Cronus", "parent_of", c, "theogony", 0.95) for c in
      ["Zeus", "Hera", "Poseidon", "Demeter", "Hestia", "Hades"]],
    *[("Rhea", "parent_of", c, "theogony", 0.95) for c in
      ["Zeus", "Hera", "Poseidon", "Demeter", "Hestia", "Hades"]],

    # Children of Zeus (various mothers)
    ("Zeus", "parent_of", "Athena", "theogony", 0.9),
    ("Metis", "parent_of", "Athena", "theogony", 0.85),
    ("Zeus", "parent_of", "Apollo", "theogony", 0.9),
    ("Zeus", "parent_of", "Artemis", "theogony", 0.9),
    ("Leto", "parent_of", "Apollo", "theogony", 0.9),
    ("Leto", "parent_of", "Artemis", "theogony", 0.9),
    ("Zeus", "parent_of", "Ares", "theogony", 0.9),
    ("Hera", "parent_of", "Ares", "theogony", 0.9),
    ("Hera", "parent_of", "Hephaestus", "theogony", 0.8),
    ("Zeus", "parent_of", "Hermes", "berens", 0.85),
    ("Maia", "parent_of", "Hermes", "berens", 0.85),
    ("Zeus", "parent_of", "Persephone", "berens", 0.85),
    ("Demeter", "parent_of", "Persephone", "berens", 0.9),
    ("Zeus", "parent_of", "Dionysus", "berens", 0.85),
    ("Semele", "parent_of", "Dionysus", "berens", 0.85),
    ("Zeus", "parent_of", "Hebe", "berens", 0.8),
    ("Hera", "parent_of", "Hebe", "berens", 0.8),

    # --- Aphrodite: the two competing origin traditions (the provenance demo) ---
    ("Aphrodite", "born_from", "Uranus", "theogony", 0.9),   # sea-foam of Uranus (Hesiod)
    ("Zeus", "parent_of", "Aphrodite", "iliad", 0.8),         # daughter of Zeus & Dione (Homer)
    ("Dione", "parent_of", "Aphrodite", "iliad", 0.8),

    # Demigod / hero parentage
    ("Zeus", "parent_of", "Heracles", "berens", 0.9),
    ("Alcmene", "parent_of", "Heracles", "berens", 0.9),
    ("Zeus", "parent_of", "Perseus", "berens", 0.9),
    ("Danae", "parent_of", "Perseus", "berens", 0.9),
    ("Peleus", "parent_of", "Achilles", "berens", 0.9),
    ("Thetis", "parent_of", "Achilles", "berens", 0.9),

    # Monster genealogy
    ("Typhon", "parent_of", "Cerberus", "theogony", 0.85),
    ("Typhon", "parent_of", "Hydra", "theogony", 0.85),
    ("Typhon", "parent_of", "Chimera", "theogony", 0.85),
    ("Echidna", "parent_of", "Cerberus", "theogony", 0.85),
    ("Echidna", "parent_of", "Hydra", "theogony", 0.85),
    ("Echidna", "parent_of", "Sphinx", "theogony", 0.8),

    # Group membership — classic list of the Twelve Olympians (incl. Hestia)
    *[("Twelve Olympians", "member_of", g, "berens", 0.9) for g in
      ["Zeus", "Hera", "Poseidon", "Demeter", "Hestia", "Athena", "Apollo",
       "Artemis", "Ares", "Aphrodite", "Hephaestus", "Hermes"]],
    *[("Titans", "member_of", t, "theogony", 0.9) for t in
      ["Cronus", "Rhea", "Oceanus", "Tethys", "Hyperion", "Theia", "Coeus",
       "Phoebe", "Iapetus", "Themis", "Mnemosyne", "Crius"]],

    # Domains, weapons, deeds
    ("Zeus", "rules", "Mount Olympus", "berens", 0.9),
    ("Poseidon", "rules", "Pontus", "berens", 0.9),
    ("Hades", "rules", "Underworld", "berens", 0.9),
    ("Zeus", "wields", "Thunderbolt", "berens", 0.95),
    ("Poseidon", "wields", "Trident", "berens", 0.95),
    ("Hermes", "wields", "Winged Sandals", "berens", 0.9),
    ("Hermes", "wields", "Caduceus", "berens", 0.9),
    ("Athena", "bears", "Aegis", "berens", 0.9),
    ("Cerberus", "guards", "Underworld", "berens", 0.95),

    ("Perseus", "killed", "Medusa", "berens", 0.95),
    ("Heracles", "killed", "Hydra", "berens", 0.95),
    ("Theseus", "killed", "Minotaur", "berens", 0.95),
    ("Bellerophon", "killed", "Chimera", "berens", 0.9),
    ("Oedipus", "killed", "Sphinx", "berens", 0.85),
    ("Zeus", "killed", "Typhon", "theogony", 0.9),

    # A touch of Ovid
    ("Apollo", "loved", "Daphne", "ovid", 0.9),
]

# --- Attribute facts, some sensitive ------------------------------------------
# tier: "public" | "restricted" | "secret"
# (subject, predicate, value, source_id, trust, tier)
FACTS = [
    ("Zeus", "epithet", "cloud-gatherer", "iliad", 0.9, "public"),
    ("Athena", "domain", "wisdom and strategic war", "berens", 0.9, "public"),
    ("Apollo", "domain", "prophecy, music, the sun", "berens", 0.9, "public"),
    ("Hades", "epithet", "the unseen one", "berens", 0.85, "public"),

    # RESTRICTED — cult / prophecy knowledge (initiates and gods only)
    ("Eleusis", "mystery_rite",
     "The Eleusinian Mysteries reenact Demeter's search for Persephone; "
     "initiates are promised a blessed afterlife.",
     "berens", 0.8, "restricted"),
    ("Cronus", "prophecy",
     "It was foretold that one of Cronus's own children would overthrow him — "
     "which is why he swallowed them.",
     "theogony", 0.9, "restricted"),

    ("Achilles", "role", "The greatest warrior of the Achaeans at Troy.",
     "iliad", 0.9, "public"),

    # SECRET — a hero's fatal weakness / underworld geography (gods only)
    ("Achilles", "fatal_weakness",
     "His heel: dipped in the Styx by Thetis, it alone was left unprotected.",
     "berens", 0.85, "secret"),
    ("Underworld", "hidden_entrance",
     "A cave at Cape Tainaron in Laconia was said to open onto the descent to Hades.",
     "guerber", 0.75, "secret"),
]

# --- Roman parallels (interpretatio romana) -----------------------------------
# The Romans identified their own gods with Greek ones. Modelling this as an
# explicit ``equivalent_to`` edge lets the agent traverse *between* two source
# worlds — a query flat retrieval cannot resolve systematically. Each pairing is
# attested by the mythographers in the corpus (Bulfinch, Berens, Guerber, Ovid).
# (greek, roman, source_id)
PARALLELS = [
    ("Zeus", "Jupiter", "bulfinch"),
    ("Hera", "Juno", "bulfinch"),
    ("Poseidon", "Neptune", "bulfinch"),
    ("Demeter", "Ceres", "berens"),
    ("Hestia", "Vesta", "berens"),
    ("Athena", "Minerva", "bulfinch"),
    ("Artemis", "Diana", "bulfinch"),
    ("Ares", "Mars", "bulfinch"),
    ("Aphrodite", "Venus", "bulfinch"),
    ("Hephaestus", "Vulcan", "berens"),
    ("Hermes", "Mercury", "bulfinch"),
    ("Hades", "Pluto", "berens"),
    ("Dionysus", "Bacchus", "bulfinch"),
    ("Persephone", "Proserpina", "ovid"),
    ("Eros", "Cupid", "bulfinch"),
    ("Cronus", "Saturn", "berens"),
    ("Rhea", "Ops", "berens"),
    ("Gaia", "Terra", "berens"),
    ("Uranus", "Caelus", "berens"),
    ("Heracles", "Hercules", "bulfinch"),
    ("Odysseus", "Ulysses", "bulfinch"),
]

# Register each Roman counterpart as a node and add the equivalence edge.
for _greek, _roman, _src in PARALLELS:
    NODES.append((_roman, "RomanDeity"))
    EDGES.append((_greek, "equivalent_to", _roman, _src, 0.9))

# A uniquely Roman god with no Greek counterpart — the graph can represent the
# *absence* of a parallel, a nuance worth showing on stage.
NODES.append(("Janus", "RomanDeity"))
FACTS.append(
    ("Janus", "domain",
     "Roman god of beginnings, gates and doorways; two-faced, looking to past "
     "and future. He has no Greek equivalent.",
     "berens", 0.85, "public"))
