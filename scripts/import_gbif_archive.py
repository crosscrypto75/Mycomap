#!/usr/bin/env python3
"""Convert a manually downloaded GBIF DwC-A ZIP into a compact MycoMap lookup.
Usage: python scripts/import_gbif_archive.py download.zip data/mycology/france-gbif.json
No API calls; do not treat absence or counts as ecological probabilities.
"""
import csv
import json
import re
import sys
import zipfile
from collections import Counter
from pathlib import Path

source = Path(sys.argv[1])
target = Path(sys.argv[2])
counts = Counter()
datasets = set()
with zipfile.ZipFile(source) as archive:
    with archive.open("occurrence.txt") as stream:
        rows = csv.DictReader((line.decode("utf-8-sig", errors="replace") for line in stream), delimiter="\t")
        for row in rows:
            if row.get("kingdom") != "Fungi" or row.get("countryCode") != "FR":
                continue
            if row.get("taxonRank") not in ("SPECIES", "SUBSPECIES", "VARIETY", "FORM"):
                continue
            name = (row.get("species") or "").strip()
            if not re.fullmatch(r"[A-Z][a-zA-Z-]+\s+[a-z][a-zA-Z-]+", name):
                continue
            counts[name] += 1
            if row.get("datasetKey"):
                datasets.add(row["datasetKey"])
payload = {
    "schemaVersion": 1,
    "source": "GBIF occurrence download (manually supplied DwC-A)",
    "scope": "France; Fungi; species-level names",
    "caveats": [
        "Counts cover only this downloaded archive, not all GBIF France records.",
        "Absence is not evidence of absence in France.",
        "Counts are not probabilities, confidence scores, or ecological productivity.",
        "Images are not included unless provided separately."
    ],
    "datasetKeys": sorted(datasets),
    "totalRecordsIncluded": sum(counts.values()),
    "taxa": [{"name": name, "frOccurrenceCount": count} for name, count in sorted(counts.items())]
}
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
print(f"Exported {len(counts)} species, {sum(counts.values())} records -> {target}")
