#!/usr/bin/env python3
"""Build a documented, non-exhaustive French fungal occurrence index from GBIF.

Only species with at least one GBIF occurrence recorded in France are included.
Occurrence counts are NOT abundance, and lack of records is NOT absence.
Run: python scripts/build_fr_fungi_reference.py
"""
import json
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://api.gbif.org/v1"
OUTPUT = Path("data/mycology/france-gbif.json")
FACET_PAGE = 1000
MAX_PAGES = int(os.getenv("MYCOMAP_GBIF_MAX_PAGES", "100"))
DELAY = float(os.getenv("MYCOMAP_GBIF_DELAY", "0.12"))


def get(path, params=None, attempts=4):
    url = BASE + path + ("?" + urllib.parse.urlencode(params, doseq=True) if params else "")
    for attempt in range(attempts):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "MycoMap-reference-builder/1.0 (public biodiversity research)", "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=45) as response:
                return json.load(response)
        except Exception:
            if attempt == attempts - 1:
                raise
            time.sleep(2 ** attempt)


def main():
    species_counts = {}
    pages = 0
    for offset in range(0, MAX_PAGES * FACET_PAGE, FACET_PAGE):
        data = get("/occurrence/search", {
            "country": "FR", "kingdomKey": 5, "taxonRank": "SPECIES",
            "facet": "taxonKey", "facetLimit": FACET_PAGE,
            "facetOffset": offset, "limit": 0,
        })
        facets = data.get("facets", [])
        counts = next((f.get("counts", []) for f in facets if f.get("field") == "TAXON_KEY"), None)
        if counts is None:
            raise RuntimeError("GBIF did not return taxonKey facets; refusing to publish an empty index")
        pages += 1
        for entry in counts:
            key = entry.get("name", "")
            if str(key).isdigit():
                species_counts[int(key)] = int(entry.get("count", 0))
        print("Facet page", pages, "taxa", len(species_counts), flush=True)
        if len(counts) < FACET_PAGE:
            break
        time.sleep(DELAY)
    else:
        raise RuntimeError("Facet pagination hit MYCOMAP_GBIF_MAX_PAGES; increase cap before publishing")

    taxa = []
    for index, (key, count) in enumerate(sorted(species_counts.items())):
        try:
            info = get("/species/" + str(key))
        except Exception as exc:
            print("Skip unresolved taxon", key, exc, flush=True)
            continue
        if info.get("kingdom") != "Fungi" or info.get("rank") != "SPECIES":
            continue
        name = info.get("canonicalName")
        if not name or len(name.split()) < 2:
            continue
        taxa.append({
            "gbifKey": key,
            "name": name,
            "scientificName": info.get("scientificName", name),
            "acceptedKey": info.get("acceptedKey", key),
            "status": info.get("taxonomicStatus", "UNKNOWN"),
            "frOccurrenceCount": count,
        })
        if index % 100 == 0:
            print("Resolved", index + 1, "/", len(species_counts), flush=True)
        time.sleep(DELAY)

    if len(taxa) < 100:
        raise RuntimeError("Suspiciously small reference; refusing to overwrite existing data")
    payload = {
        "schemaVersion": 1,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "source": "GBIF occurrence and species APIs",
        "sourceUrl": "https://www.gbif.org/occurrence/search?country=FR&taxon_key=5",
        "country": "FR",
        "meaning": "Taxa with occurrence records in France; records are unverified individually, not a validated French checklist",
        "caveats": [
            "Presence of a GBIF record is not proof of native or established occurrence.",
            "Absence from this file is not evidence of absence in France.",
            "Counts reflect submitted records and sampling effort, not abundance.",
            "Synonyms and duplicate accepted taxa may occur; acceptedKey is provided.",
            "Departmental occurrence data are not included.",
        ],
        "taxa": sorted(taxa, key=lambda t: (t["name"].lower(), t["gbifKey"])),
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temp = OUTPUT.with_suffix(".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    temp.replace(OUTPUT)
    print("Wrote", OUTPUT, len(taxa), "taxa")


if __name__ == "__main__":
    main()
