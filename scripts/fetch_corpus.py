"""
Download the FULL public-domain source texts into data/corpus/.

The repo ships with substantial excerpts already. Run this to replace them with
the complete books (Project Gutenberg permits free download and redistribution).

    python scripts/fetch_corpus.py

No third-party dependencies — uses only the standard library.
"""
from __future__ import annotations

import os
import urllib.request

# source_id -> (Gutenberg ID, output filename)
BOOKS = {
    "hesiod_homerica":  (348,   "hesiod_homerica_gutenberg348.txt"),
    "berens":           (22381, "berens_myths_legends_gutenberg22381.txt"),
    "bulfinch":         (3327,  "bulfinch_age_of_fable_gutenberg3327.txt"),
    "guerber":          (39250, "guerber_myths_greece_rome_gutenberg39250.txt"),
    "ovid":             (21765, "ovid_metamorphoses_gutenberg21765.txt"),
}

URL = "https://www.gutenberg.org/cache/epub/{id}/pg{id}.txt"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "corpus")


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    for key, (gid, fname) in BOOKS.items():
        url = URL.format(id=gid)
        dest = os.path.join(OUT, fname)
        print(f"↓ {key:18} {url}")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read()
            with open(dest, "wb") as fh:
                fh.write(data)
            print(f"  saved {len(data):,} bytes -> {dest}")
        except Exception as e:  # noqa: BLE001
            print(f"  FAILED: {e}")
    print("Done.")


if __name__ == "__main__":
    main()
