# Corpus sources

All texts are public domain, downloaded from **Project Gutenberg**. The files in
this folder are substantial excerpts; run `python scripts/fetch_corpus.py` to
pull the complete books. Redistribution is permitted under the Project Gutenberg
License.

| File | Work | Author / Editor | Source |
|------|------|-----------------|--------|
| `hesiod_homerica_gutenberg348.txt` | Hesiod, the Homeric Hymns, and Homerica (incl. **Theogony**) | Hesiod / Homer, tr. H. G. Evelyn-White | https://www.gutenberg.org/ebooks/348 |
| `berens_myths_legends_gutenberg22381.txt` | Myths and Legends of Ancient Greece and Rome | E. M. Berens | https://www.gutenberg.org/ebooks/22381 |
| `bulfinch_age_of_fable_gutenberg3327.txt` | Bulfinch's Mythology: The Age of Fable | Thomas Bulfinch | https://www.gutenberg.org/ebooks/3327 |
| `guerber_myths_greece_rome_gutenberg39250.txt` | Myths of Greece and Rome | H. A. Guerber | https://www.gutenberg.org/ebooks/39250 |
| `ovid_metamorphoses_gutenberg21765.txt` | The Metamorphoses of Ovid, Books I–VII | Ovid, tr. Henry T. Riley | https://www.gutenberg.org/ebooks/21765 |

Direct plain-text URLs follow the pattern
`https://www.gutenberg.org/cache/epub/<ID>/pg<ID>.txt`.

## How these sources are used

- The **naive agent** does flat keyword retrieval over distilled chunks of this
  corpus (`data/kb/flat_notes.md`).
- The **enforced agent** reasons over the curated knowledge graph
  (`mythos/data.py`), where every edge and fact cites one of the works above via
  the `SOURCES` registry and carries a trust score.
